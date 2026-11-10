# -*- coding: utf-8 -*-
"""
edusrc 轮：只读、非武器化指纹验证（2026-11-10）
红线：只发 GET；不执行 RCE/XXE payload；不下载 heapdump/env 内容；不爆破弱口令；不访问真实数据。
命中未授权管理面/未授权端点即停（用户设定：出现洞即停）。
"""
import json, time, re, os, sys
import requests
import urllib3
urllib3.disable_warnings()

OUT = r"E:\kimi\scan\fofa_pool\edusrc_readonly_fp_20261110.json"
SRC = r"E:\kimi\scan\fofa_pool\edusrc_nday_slices_20261110.json"

s = requests.Session()
s.trust_env = False          # 关键：国内目标直连，别走 7897 代理（notes 7.34 教训）
s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
                  "Accept": "text/html,application/json,*/*"})

d = json.load(open(SRC, encoding="utf-8"))

def hosts(keys):
    out = []
    for k in keys:
        for h in d.get(k, {}).get("hosts", []):
            host = h.lower()
            base = host.split(":")[0]
            if base.endswith(".edu.cn") and base.count("edu.cn") == 1 and host not in out:
                out.append(host)
    return out

# 优先级：KEV 在册 N-day RCE > 未授权端点 > 未授权管理面
GROUPS = [
    ("geoserver", hosts(["edu_geoserver"]), "/geoserver/rest/about/version.json"),
    ("actuator",  hosts(["edu_springboot", "edu_actuator"]), "/actuator"),
    ("jboss",     hosts(["edu_jboss"]), "/"),
    ("grafana",   hosts(["edu_grafana"]), "/api/health"),
    ("jenkins",   hosts(["edu_jenkins", "probe_jenkins"]), "/api/json?tree=version"),
    ("weblogic",  hosts(["edu_weblogic"]), "/"),
    ("gitlab",    hosts(["edu_gitlab"]), "/"),
]
# 去掉组间重复
seen = set()
for g in GROUPS:
    g[1][:] = [h for h in g[1] if not (h in seen or seen.add(h))]

def scheme_for(h):
    if ":" in h:
        p = int(h.rsplit(":", 1)[1])
        return "http" if p in (3000, 8080, 8081, 8082, 8084, 8089, 8980, 1312, 8000, 8001, 8887, 8090, 8095) else "https"
    return "https"

def probe(host, path):
    sch = scheme_for(host)
    url = sch + "://" + host + path
    try:
        r = s.get(url, timeout=6, verify=False, allow_redirects=True)
        body = r.text[:3000]
        title = ""
        m = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
        if m:
            title = re.sub(r"\s+", " ", m.group(1)).strip()[:100]
        return {"url": url, "status": r.status_code, "len": len(r.content),
                "title": title, "ctype": r.headers.get("Content-Type", "")[:60],
                "server": r.headers.get("Server", "")[:60],
                "keys": [k for k in ("_links", "version", "GeoServer", "Jenkins", "JBoss", "commit", "database", "healthy")
                         if k.lower() in body.lower()],
                "hit": False, "why": ""}
    except Exception as e:
        return {"url": url, "status": None, "err": type(e).__name__ + ": " + str(e)[:90], "hit": False, "why": ""}

def judge(group, rec):
    """保守判定：只有明确的未授权管理面/端点才算洞"""
    if rec.get("status") != 200:
        return False, ""
    keys = rec.get("keys", [])
    if group == "actuator" and "_links" in keys:
        return True, "Spring Boot Actuator 未授权暴露（/actuator 200 且返回 _links）"
    if group == "jboss" and ("JBoss" in (rec.get("title") or "") or "JBoss" in keys) and "jmx-console" in rec.get("url", ""):
        return True, "JBoss jmx-console 未授权"
    if group == "geoserver" and "version" in keys and "geoserver" in (rec.get("ctype", "") + rec.get("title", "")).lower():
        return True, "GeoServer 版本接口未授权可读（需人工复核 CVE-2024-36401 影响版本）"
    return False, ""

results = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
stop = None
for group, hs, path in GROUPS:
    # geoserver 先打版本接口，失败再打 web 首页（只读）
    paths = [path, "/geoserver/web/"] if group == "geoserver" else [path]
    for h in hs:
        tag = group + "|" + h
        if tag in results:
            continue
        recs = []
        for p in paths:
            r = probe(h, p)
            recs.append(r)
            time.sleep(1.2)
            if r.get("status") == 200:
                break
        rec = dict(recs[-1])
        rec["attempts"] = recs[:-1]
        hit, why = judge(group, rec)
        rec["hit"], rec["why"] = hit, why
        results[tag] = rec
        print(("HIT " if hit else "    ") + group + " " + h + " -> " +
              str(rec.get("status")) + " " + (rec.get("title") or "")[:45] +
              " keys=" + ",".join(rec.get("keys", []))[:60], flush=True)
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=1)
        if hit:
            stop = tag + " :: " + why
            break
    if stop:
        break

print("DONE", len(results), "STOP:", stop, flush=True)
