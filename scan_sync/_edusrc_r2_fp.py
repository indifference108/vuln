# -*- coding: utf-8 -*-
"""第二轮候选只读验证：只发 GET，不爆破、不执行 payload、不读真实数据"""
import json, time, re, os
import requests, urllib3
urllib3.disable_warnings()

SRC = r"E:\kimi\scan\fofa_pool\edusrc_nday_slices_20261110.json"
OUT = r"E:\kimi\scan\fofa_pool\edusrc_r2_fp_20261110.json"
s = requests.Session(); s.trust_env = False
s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"})

d = json.load(open(SRC, encoding="utf-8"))

def hosts(k):
    out = []
    for h in d.get(k, {}).get("hosts", []):
        host = h.lower(); base = host.split(":")[0]
        if base.endswith(".edu.cn") and base.count("edu.cn") == 1 and host not in out:
            out.append(host)
    return out

GROUPS = [
    ("jumpserver", hosts("edu_jumpserver"), ["/"]),
    ("phpmyadmin", hosts("edu_phpmyadmin"), ["/"]),
    ("tongda",     hosts("edu_tongda"),     ["/"]),
    ("ruoyi",      hosts("edu_ruoyi"),      ["/"]),
    ("swagger",    hosts("edu_swagger"),    ["/swagger-ui/index.html"]),
    ("thinkphp",   hosts("edu_thinkphp"),   ["/"]),
]
seen = set()
for g in GROUPS:
    g[1][:] = [h for h in g[1] if not (h in seen or seen.add(h))]

def scheme_for(h):
    if ":" in h:
        p = int(h.rsplit(":", 1)[1])
        return "http" if p in (3000, 58080, 8090, 8099, 9000, 9990, 6066, 10188, 10388, 19999) else "https"
    return "https"

def probe(host, path):
    url = scheme_for(host) + "://" + host + path
    try:
        r = s.get(url, timeout=6, verify=False, allow_redirects=True)
        body = r.text[:4000]
        m = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
        title = re.sub(r"\s+", " ", m.group(1)).strip()[:90] if m else ""
        low = body.lower()
        return {"url": url, "status": r.status_code, "len": len(r.content), "title": title,
                "ctype": r.headers.get("Content-Type", "")[:60],
                "login_form": ("type=password" in low or "name=\"password\"" in low),
                "has_swagger": "swagger" in low,
                "has_jumpserver": "jumpserver" in low or "jumpserver" in title.lower(),
                "has_phpmyadmin": "phpmyadmin" in low,
                "final_url": r.url[:120]}
    except Exception as e:
        return {"url": url, "status": None, "err": type(e).__name__ + ":" + str(e)[:80]}

def judge(g, r):
    if r.get("status") != 200:
        return False, ""
    if g == "phpmyadmin" and r.get("has_phpmyadmin") and not r.get("login_form"):
        return True, "phpMyAdmin 无需登录直接进入管理界面（未授权管理台）"
    if g == "jumpserver" and r.get("has_jumpserver") and "login" not in (r.get("title") or "").lower():
        return False, ""   # 首页公开不等于未授权，保守不定案
    if g == "swagger" and r.get("has_swagger"):
        return True, "Swagger UI 接口文档未授权可访问（信息泄露面）"
    return False, ""

results = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
stop = None
for g, hs, paths in GROUPS:
    for h in hs:
        tag = g + "|" + h
        if tag in results:
            continue
        recs = [probe(h, p) for p in paths]
        for _ in paths:
            time.sleep(1.2)
        r = recs[-1]
        hit, why = judge(g, r)
        results[tag] = {"group": g, "host": h, "probes": recs, "hit": hit, "why": why,
                        "status": r.get("status"), "title": r.get("title")}
        print(("HIT " if hit else "    ") + g + " " + h + " -> " + str(r.get("status")) +
              " " + (r.get("title") or "")[:45] + " loginform=" + str(r.get("login_form")), flush=True)
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=1)
        if hit:
            stop = tag + " :: " + why
            break
    if stop:
        break
print("DONE", len(results), "STOP:", stop, flush=True)
