# -*- coding: utf-8 -*-
"""补漏：超时目标双 scheme 重试 + Jenkins 登录页版本串（只读 GET）"""
import json, time, re, requests, urllib3
urllib3.disable_warnings()

OUT = r"E:\kimi\scan\fofa_pool\edusrc_r5_retry_20261110.json"
s = requests.Session(); s.trust_env = False
s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"})

TARGETS = [
    ("confluence", "confluence.cts.shanghaitech.edu.cn", ["/", "/login.action", "/rest/api/space"]),
    ("weblogic",   "crm.gsm.pku.edu.cn",                 ["/", "/console/login/LoginForm.jsp"]),
    ("jenkins",    "jenkins.cqou.edu.cn",               ["/login", "/about/"]),
    ("jenkins",    "lodetech.ustc.edu.cn:8080",          ["/login", "/about/"]),
    ("jenkins",    "build-tux.scc.edu.cn",               ["/login"]),
]

def probe(host, scheme, path):
    url = scheme + "://" + host + path
    try:
        r = s.get(url, timeout=9, verify=False, allow_redirects=False)
        b = r.text[:30000]
        m = re.search(r"<title[^>]*>(.*?)</title>", b, re.I | re.S)
        title = re.sub(r"\s+", " ", m.group(1)).strip()[:80] if m else ""
        vers = re.findall(r"(?:Jenkins ver\.?|Jenkins|Confluence|WebLogic Server|Version)[^\n<]{0,50}?(\d+\.\d+(?:\.\d+)?)", b, re.I)[:4]
        return {"url": url, "status": r.status_code, "len": len(r.content), "title": title,
                "ctype": r.headers.get("Content-Type", "")[:60],
                "server": r.headers.get("Server", "")[:60],
                "version_hints": vers,
                "has_login_form": 'type="password"' in b or "type='password'" in b,
                "head": b[:180]}
    except Exception as e:
        return {"url": url, "status": None, "err": type(e).__name__ + ":" + str(e)[:80]}

res = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "boundary": "只读 GET；不登录、不爆破、不执行 payload", "items": []}
for g, h, paths in TARGETS:
    item = {"group": g, "host": h, "probes": []}
    for sch in ("https", "http"):
        for p in paths:
            r = probe(h, sch, p)
            item["probes"].append(r)
            print(g, h[:32].ljust(32), sch, p.ljust(30), "->", str(r.get("status")).ljust(5),
                  (r.get("title") or "")[:26].ljust(26), "ver", r.get("version_hints"), flush=True)
            time.sleep(1.3)
            if r.get("status") == 200:
                break
        if any(x.get("status") == 200 for x in item["probes"]):
            break
    res["items"].append(item)
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("DONE", flush=True)
