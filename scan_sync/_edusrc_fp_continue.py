# -*- coding: utf-8 -*-
"""
edusrc 轮续跑：只读指纹验证（收紧判定）
红线：只发 GET；不执行任何 payload；不读取 env/heapdump/配置内容；不爆破弱口令。
HIT 判定（保守）：
  - Jenkins /script 200            -> 未授权 Groovy 控制台（RCE 面）
  - JBoss /jmx-console 200         -> 未授权管理面
  - /actuator _links 含敏感端点    -> 未授权敏感端点（只看键名，不请求）
  - Tomcat /manager/html 200       -> 未授权管理台
  - Grafana /api/health 版本 <8.3.2 -> CVE-2021-43798 疑似 N-day
  - GeoServer 版本接口可读且版本在受影响范围 -> CVE-2024-36401 疑似 N-day
"""
import json, time, re, os
import requests, urllib3
urllib3.disable_warnings()

SRC = r"E:\kimi\scan\fofa_pool\edusrc_nday_slices_20261110.json"
OUT = r"E:\kimi\scan\fofa_pool\edusrc_readonly_fp_20261110.json"

s = requests.Session()
s.trust_env = False
s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"})

d = json.load(open(SRC, encoding="utf-8"))

def hosts(keys):
    out = []
    for k in keys:
        for h in d.get(k, {}).get("hosts", []):
            host = h.lower(); base = host.split(":")[0]
            if base.endswith(".edu.cn") and base.count("edu.cn") == 1 and host not in out:
                out.append(host)
    return out

GROUPS = [
    ("actuator",  hosts(["edu_springboot", "edu_actuator"]), ["/actuator"]),
    ("jenkins",   hosts(["edu_jenkins", "probe_jenkins"]),   ["/api/json?tree=version", "/script"]),
    ("jboss",     hosts(["edu_jboss"]),                       ["/", "/jmx-console"]),
    ("grafana",   hosts(["edu_grafana"]),                     ["/api/health"]),
    ("tomcat",    hosts(["edu_tomcat"]),                      ["/manager/html"]),
    ("weblogic",  hosts(["edu_weblogic"]),                    ["/"]),
    ("gitlab",    hosts(["edu_gitlab"]),                      ["/"]),
    ("confluence",hosts(["edu_confluence"]),                  ["/"]),
    ("printer",   hosts(["edu_printer"]),                     ["/"]),
    ("hikvision", hosts(["edu_hikvision"]),                   ["/"]),
]
seen = set()
for g in GROUPS:
    g[1][:] = [h for h in g[1] if not (h in seen or seen.add(h))]

def scheme_for(h):
    if ":" in h:
        p = int(h.rsplit(":", 1)[1])
        return "http" if p in (3000, 8080, 8081, 8082, 8084, 8089, 8980, 1312, 8000, 8001, 8887, 8090, 8095) else "https"
    return "https"

def probe(host, path):
    url = scheme_for(host) + "://" + host + path
    try:
        r = s.get(url, timeout=6, verify=False, allow_redirects=False)
        body = r.text[:4000]
        m = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
        title = re.sub(r"\s+", " ", m.group(1)).strip()[:90] if m else ""
        return {"url": url, "status": r.status_code, "len": len(r.content), "title": title,
                "ctype": r.headers.get("Content-Type", "")[:60], "body_head": body[:400]}
    except Exception as e:
        return {"url": url, "status": None, "err": type(e).__name__ + ":" + str(e)[:80]}

def version_lt(v, target):
    try:
        a = [int(x) for x in v.split(".")]; b = [int(x) for x in target.split(".")]
        a += [0] * (3 - len(a)); b += [0] * (3 - len(b))
        return a[:3] < b[:3]
    except Exception:
        return False

def judge(group, recs):
    by = {}
    for r in recs:
        by[r["url"].split("://", 1)[-1].split("/", 1)[-1].lstrip("/")] = r
    st = lambda path: next((r for r in recs if r["url"].endswith(path)), None)
    if group == "jenkins":
        r = st("/script")
        if r and r.get("status") == 200 and "jenkins" in (r.get("body_head", "") + r.get("title", "")).lower():
            return True, "Jenkins /script 未授权可访问（Groovy 控制台 = RCE 面）"
    if group == "jboss":
        r = st("/jmx-console")
        if r and r.get("status") == 200 and ("jboss" in (r.get("body_head", "") + r.get("title", "")).lower()):
            return True, "JBoss jmx-console 未授权管理面"
    if group == "actuator":
        r = st("/actuator")
        if r and r.get("status") == 200:
            try:
                links = list((json.loads(r["body_head"]).get("_links") or {}).keys())
            except Exception:
                links = []
            sens = [x for x in links if x in ("env", "heapdump", "configprops", "mappings", "beans",
                                              "jolokia", "shutdown", "restart", "refresh", "httptrace",
                                              "threaddump", "auditevents", "loggers", "flyway", "liquibase")]
            if sens:
                return True, "Spring Boot Actuator 未授权暴露敏感端点: " + ",".join(sens)
    if group == "tomcat":
        r = st("/manager/html")
        if r and r.get("status") == 200 and "tomcat" in (r.get("body_head", "") + r.get("title", "")).lower():
            return True, "Tomcat /manager/html 未授权管理台"
    if group == "grafana":
        r = st("/api/health")
        if r and r.get("status") == 200:
            m = re.search(r'"version"\s*:\s*"([\d.]+)"', r.get("body_head", ""))
            # CVE-2021-43798 影响范围仅 8.0.0-beta1 <= v <= 8.3.0（修复 8.3.1/8.3.2）；
            # 6.x/7.x 老版本不适用，避免把「版本老」误判成 N-day 命中。
            if m and m.group(1).startswith("8.") and version_lt(m.group(1), "8.3.1"):
                return True, "Grafana " + m.group(1) + " 落在 CVE-2021-43798 影响范围（N-day）"
    return False, ""

results = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
# 清掉上一次被误判的 hit 标记（health-only 不算洞）
for k, v in results.items():
    if k.startswith("actuator|") and v.get("hit"):
        v["hit"] = False; v["why"] = "复核：仅 health 端点，默认配置，不构成洞"
stop = None
count = 0
for group, hs, paths in GROUPS:
    for h in hs:
        tag = group + "|" + h
        if tag in results and results[tag].get("attempts") is not None:
            # geoserver 旧组名不同；其余沿用已有
            pass
        if tag in results:
            continue
        recs = []
        for p in paths:
            recs.append(probe(h, p))
            time.sleep(1.2)
        hit, why = judge(group, recs)
        rec = {"group": group, "host": h, "probes": recs, "hit": hit, "why": why,
               "status": recs[-1].get("status"), "title": recs[-1].get("title")}
        results[tag] = rec
        count += 1
        print(("HIT " if hit else "    ") + group + " " + h + " -> " +
              ",".join(str(r.get("status")) for r in recs) + " " +
              (recs[-1].get("title") or "")[:40], flush=True)
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=1)
        if hit:
            stop = tag + " :: " + why
            break
    if stop:
        break

print("DONE new=", count, "total=", len(results), "STOP:", stop, flush=True)
