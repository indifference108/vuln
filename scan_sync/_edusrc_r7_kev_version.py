# -*- coding: utf-8 -*-
"""
第七轮：KEV 情报驱动的只读版本串判定
逻辑：本地 KEV 库 2026 新条目覆盖的组件，恰好命中已有 edu.cn 资产池
      -> 不再找新资产，改为对已有池做只读版本串提取，判断有无可核验判定点。
红线：只发 GET；不执行任何 PoC/利用链；不读取真实数据；不爆破。
"""
import json, re, time, requests, urllib3
urllib3.disable_warnings()

SRC = r"E:\kimi\scan\fofa_pool\edusrc_nday_slices_20261110.json"
OUT = r"E:\kimi\scan\fofa_pool\edusrc_r7_kev_version_20261110.json"
s = requests.Session(); s.trust_env = False
s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"})

d = json.load(open(SRC, encoding="utf-8"))
KEV_MAP = {
    "edu_netscaler": ["CVE-2026-88772", "CVE-2026-88779", "CVE-2026-88771", "CVE-2026-19490", "CVE-2026-8452"],
    "edu_zimbra":    ["CVE-2026-73570"],
    "edu_activemq":  ["CVE-2026-34197"],
    "edu_tomcat":    ["CVE-2026-34486"],
    "edu_gitlab":    ["CVE-2026-85706"],
    "edu_vcenter":   ["CVE-2026-59310"],
}

def hosts(k):
    out = []
    for h in d.get(k, {}).get("hosts", []):
        host = h.lower(); base = host.split(":")[0]
        if base.endswith(".edu.cn") and base.count("edu.cn") == 1 and host not in out:
            out.append(host)
    return out

def scheme_for(h):
    if ":" in h:
        p = int(h.rsplit(":", 1)[1])
        return "http" if p in (3000, 8000, 8002, 8080, 8085, 8161, 9191, 9999, 5001, 1312) else "https"
    return "https"

# 只读版本串模式（从登录页 HTML/JS 路径里找，不发任何利用请求）
PATTERNS = [
    r"(?:Citrix Gateway|NetScaler|NS.?Gateway)[\s/_-]{0,4}[vV]?(\d+\.\d+(?:\.\d+)?)",
    r"(?:Zimbra|ZCS)[\s/_-]{0,4}[vV]?(\d+\.\d+(?:\.\d+)?)",
    r"(?:Apache Tomcat|Tomcat/)(\d+\.\d+(?:\.\d+)?)",
    r"(?:GitLab|ActiveMQ|vCenter)[\s/_-]{0,4}[vV]?(\d+\.\d+(?:\.\d+)?)",
    r"[\"'](?:version|build|buildNumber|release)[\"']\s*[:=]\s*[\"'](\d+\.\d+(?:\.\d+)?)",
    r"/(?:vpn|js|static|assets|build)/[^\"']*?(\d+\.\d+\.\d+)[^\"']*?\.(?:js|css)",
]

def probe(key, host):
    url = scheme_for(host) + "://" + host + "/"
    try:
        r = s.get(url, timeout=8, verify=False, allow_redirects=True)
        b = r.text[:200000]
        m = re.search(r"<title[^>]*>(.*?)</title>", b, re.I | re.S)
        title = re.sub(r"\s+", " ", m.group(1)).strip()[:80] if m else ""
        vers = []
        for pat in PATTERNS:
            vers.extend(re.findall(pat, b, re.I))
        vers = list(dict.fromkeys(vers))[:6]
        low = b.lower()
        return {"key": key, "host": host, "status": r.status_code, "title": title,
                "len": len(r.content), "final_url": r.url[:120],
                "ctype": r.headers.get("Content-Type", "")[:55],
                "server": r.headers.get("Server", "")[:55],
                "version_strings": vers, "version_readable": len(vers) > 0,
                "vendor_marker": [x for x in ["citrix", "netscaler", "zimbra", "tomcat", "gitlab", "activemq", "vcenter"]
                                  if x in low][:4],
                "kev_cves": KEV_MAP.get(key, [])}
    except Exception as e:
        return {"key": key, "host": host, "status": None,
                "err": type(e).__name__ + ":" + str(e)[:80],
                "version_readable": False, "kev_cves": KEV_MAP.get(key, [])}

res = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
       "source": "tools/vulndb/vulndb.sqlite (CISA KEV 快照 2026-10-19, 1748 条)",
       "boundary": "只读 GET 登录页；不执行 PoC/利用链、不爆破、不读真实数据",
       "note": "KEV 库无 affected-version 字段，故本轮只判断版本串是否可读，不做 CVE 影响定案",
       "items": []}
for key in KEV_MAP:
    for h in hosts(key)[:8]:
        r = probe(key, h)
        res["items"].append(r)
        print(key.ljust(16), h[:36].ljust(36), "->", str(r.get("status")).ljust(5),
              (r.get("title") or "")[:26].ljust(26),
              "ver", r.get("version_strings"), "marker", r.get("vendor_marker"), flush=True)
        json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        time.sleep(1.2)
readable = [x for x in res["items"] if x.get("version_readable")]
print("DONE", len(res["items"]), "版本串可读:", len(readable), flush=True)
