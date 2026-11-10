# -*- coding: utf-8 -*-
"""
第五轮：扩池命中的「精确 title」组件与硬编码密码页，只读判定点验证
红线：只发 GET；不爆破、不执行 RCE/Groovy payload、不读真实数据。
HIT 判定（保守）：
  - Jenkins /script 200 且含 Jenkins 特征 -> 未授权 Groovy 控制台（RCE 面）
  - 页面 <input type=password value="..."> 有明文值 -> 前端硬编码口令（弱密钥）
  - /ISAPI/System/deviceInfo 200 且含 deviceInfo -> 未授权设备信息面
  - Confluence/WebLogic 版本可读且落 KEV N-day 范围 -> 疑似（仅版本比对）
"""
import json, time, re, os
import requests, urllib3
urllib3.disable_warnings()

SRC = r"E:\kimi\scan\fofa_pool\edusrc_nday_slices_20261110.json"
OUT = r"E:\kimi\scan\fofa_pool\edusrc_r5_fp_20261110.json"
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
    ("jenkins_t",   hosts("edu_jenkins_t"),    ["/api/json?tree=version", "/script", "/login"]),
    ("confluence_t",hosts("edu_confluence_t"), ["/", "/rest/api/space"]),
    ("weblogic_t",  hosts("edu_weblogic_t"),   ["/", "/console/login/LoginForm.jsp"]),
    ("hardcode_val",hosts("edu_hardcode_val"), ["/"]),
    ("isapi_p80",   hosts("edu_isapi_p80")[:10], ["/ISAPI/System/deviceInfo"]),
]
seen = set()
for g in GROUPS:
    g[1][:] = [h for h in g[1] if not (h in seen or seen.add(h))]

def scheme_for(h):
    if ":" in h:
        p = int(h.rsplit(":", 1)[1])
        return "http" if p in (3000, 8000, 8002, 8080, 8085, 8161, 9191, 9999, 9443, 5001) else "https"
    return "https"

def probe(host, path):
    url = scheme_for(host) + "://" + host + path
    try:
        r = s.get(url, timeout=7, verify=False, allow_redirects=False)
        b = r.text[:8000]
        low = b.lower()
        m = re.search(r"<title[^>]*>(.*?)</title>", b, re.I | re.S)
        title = re.sub(r"\s+", " ", m.group(1)).strip()[:90] if m else ""
        pw_vals = []
        for im in re.finditer(r"<input[^>]*>", b, re.I):
            tag = im.group(0)
            tp = re.search(r'type\s*=\s*["\']password["\']', tag, re.I)
            vl = re.search(r'value\s*=\s*["\']([^"\']+)["\']', tag, re.I)
            if tp and vl and vl.group(1).strip():
                pw_vals.append(vl.group(1)[:24])
        jenkins_ver = re.search(r'"version"\s*:\s*"([\d.]+)"', b)
        return {"url": url, "status": r.status_code, "len": len(r.content), "title": title,
                "ctype": r.headers.get("Content-Type", "")[:60],
                "server": r.headers.get("Server", "")[:60],
                "www_auth": r.headers.get("WWW-Authenticate", "")[:50],
                "jenkins": ("jenkins" in low or "hudson" in low),
                "jenkins_version": jenkins_ver.group(1) if jenkins_ver else None,
                "groovy_console": ("groovy" in low and "script" in low),
                "hardcoded_pwd_values": pw_vals,
                "device_info": ("<deviceinfo" in low or "devicename" in low),
                "confluence_ver": (re.search(r'(?:Confluence|version)[^\n<]{0,40}?(\d+\.\d+\.\d+)', b, re.I).group(1)
                                   if re.search(r'(?:Confluence|version)[^\n<]{0,40}?(\d+\.\d+\.\d+)', b, re.I) else None),
                "head": b[:200]}
    except Exception as e:
        return {"url": url, "status": None, "err": type(e).__name__ + ":" + str(e)[:80]}

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
        hit, why = False, ""
        for r in recs:
            if r.get("status") == 200 and r.get("jenkins") and "/script" in r.get("url", "") and r.get("groovy_console"):
                hit, why = True, "Jenkins /script 未授权 Groovy 控制台（RCE 面）"; break
            if r.get("hardcoded_pwd_values"):
                hit, why = True, "登录页 <input type=password> 存在明文硬编码口令（弱密钥）"; break
            if r.get("status") == 200 and r.get("device_info"):
                hit, why = True, "/ISAPI/System/deviceInfo 未授权可读（设备信息面）"; break
        results[tag] = {"group": g, "host": h, "probes": recs, "hit": hit, "why": why}
        jv = [r.get("jenkins_version") for r in recs if r.get("jenkins_version")]
        hp = [x for r in recs for x in r.get("hardcoded_pwd_values", [])]
        print(("HIT " if hit else "    ") + g + " " + h[:40].ljust(40),
              "->", ",".join(str(r.get("status")) for r in recs),
              "| jenkins_ver", jv[:1], "| hardpwd", hp[:3],
              "| title", (recs[0].get("title") or "")[:28], flush=True)
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=1)
        if hit:
            stop = tag + " :: " + why
            break
    if stop:
        break
print("DONE", len(results), "STOP:", stop, flush=True)
