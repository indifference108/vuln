# -*- coding: utf-8 -*-
"""只读确认 GeoServer 公开首页版本号（不执行任何 PoC/XXE）"""
import json, re, time, requests, urllib3
urllib3.disable_warnings()

OUT = r"E:\kimi\scan\fofa_pool\edusrc_geoserver_version_20261110.json"
s = requests.Session()
s.trust_env = False
s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"})

TARGETS = ["map.xjau.edu.cn", "geolab.ucas.edu.cn", "ifarm.xjau.edu.cn", "sdjn.bnu.edu.cn", "geoshikong.whcp.edu.cn"]
PATHS = ["/geoserver/web/", "/geoserver/"]
res = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "items": [],
       "cve": "CVE-2024-36401 (GeoServer XXE->RCE, CISA KEV, CVSS 9.8)",
       "affected": "<2.23.4, 2.24.0, 2.25.0 ; fixed 2.23.4 / 2.24.1 / 2.25.1",
       "note": "仅读取公开欢迎页文本中的版本号；未请求 WFS/REST 利用面，未发送任何 payload"}

def affected(v):
    try:
        parts = [int(x) for x in v.split(".")]
    except Exception:
        return None
    if len(parts) < 2 or parts[0] != 2:
        return None
    minor, patch = parts[1], (parts[2] if len(parts) > 2 else 0)
    if minor < 23:
        return True
    if minor == 23:
        return patch < 4
    if minor == 24:
        return patch < 1
    if minor == 25:
        return patch < 1
    return False

for h in TARGETS:
    item = {"host": h, "probes": [], "version": None, "affected": None}
    for p in PATHS:
        url = "https://" + h + p
        try:
            r = s.get(url, timeout=8, verify=False, allow_redirects=True)
            txt = r.text[:60000]
            title = ""
            m = re.search(r"<title[^>]*>(.*?)</title>", txt, re.I | re.S)
            if m:
                title = re.sub(r"\s+", " ", m.group(1)).strip()[:80]
            # 只在公开页面文本里找版本号
            vm = re.search(r"GeoServer\s+(2\.\d+\.\d+(?:\.\d+)?)", txt, re.I)
            ver = vm.group(1) if vm else None
            item["probes"].append({"url": url, "status": r.status_code, "title": title,
                                   "ctype": r.headers.get("Content-Type", "")[:60], "version": ver,
                                   "len": len(r.content)})
            if ver:
                item["version"] = ver
                break
        except Exception as e:
            item["probes"].append({"url": url, "status": None, "err": type(e).__name__ + ":" + str(e)[:80]})
        time.sleep(1.5)
    if item["version"]:
        item["affected"] = affected(item["version"])
    res["items"].append(item)
    print(h, "version=", item["version"], "affected=", item["affected"],
          "statuses=", [p.get("status") for p in item["probes"]],
          "titles=", [p.get("title") for p in item["probes"]], flush=True)

json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("saved", flush=True)
