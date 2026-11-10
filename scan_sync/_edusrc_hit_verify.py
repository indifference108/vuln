# -*- coding: utf-8 -*-
"""命中复核：只读确认 Actuator 未授权，绝不请求 env/heapdump 内容"""
import json, time, requests, urllib3, re
urllib3.disable_warnings()

OUT = r"E:\kimi\scan\fofa_pool\edusrc_hit_actuator_20261110.json"
s = requests.Session()
s.trust_env = False
s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"})
BASE = "http://tyzf.aku.edu.cn:8084"

def get(path):
    try:
        r = s.get(BASE + path, timeout=8, verify=False, allow_redirects=False)
        return {"path": path, "status": r.status_code,
                "ctype": r.headers.get("Content-Type", "")[:80],
                "server": r.headers.get("Server", "")[:60],
                "len": len(r.content),
                "body_head": r.text[:300]}
    except Exception as e:
        return {"path": path, "status": None, "err": type(e).__name__ + ":" + str(e)[:100]}

res = {"target": BASE, "ts": time.strftime("%Y-%m-%d %H:%M:%S"), "probes": []}
# 只请求无害端点：根、/actuator、/actuator/health。绝不请求 env/heapdump/mappings 内容。
for p in ["/", "/actuator", "/actuator/health"]:
    r = get(p)
    res["probes"].append(r)
    print(p, r.get("status"), r.get("ctype"), "len", r.get("len"), flush=True)
    time.sleep(1.5)

# 从 /actuator 的 _links 提取「端点名」列表（只看键名，不取值、不请求这些端点）
ac = res["probes"][1]
try:
    obj = json.loads(ac["body_head"])
except Exception:
    obj = {}
links = list((obj.get("_links") or {}).keys()) if isinstance(obj, dict) else []
res["exposed_endpoint_names"] = links
res["actuator_confirmed"] = ac.get("status") == 200 and len(links) > 0
res["sensitive_endpoints_listed"] = [x for x in links if x in ("env", "heapdump", "mappings", "configprops", "beans", "threaddump", "shutdown", "refresh", "restart", "jolokia", "httptrace", "auditevents")]
res["note"] = "仅读取 /actuator 的端点名清单；未请求 env/heapdump 等端点内容，未访问任何真实配置或用户数据"
res["scope"] = "aku.edu.cn = 安康学院（edu.cn 认可单位）；8084 = 疑似统一支付/统一认证业务子系统"

json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("exposed:", links, flush=True)
print("sensitive listed:", res["sensitive_endpoints_listed"], flush=True)
print("confirmed:", res["actuator_confirmed"], flush=True)
