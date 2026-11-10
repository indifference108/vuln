# -*- coding: utf-8 -*-
"""
第三轮（目标重设后）只读判定点验证
红线：只发 GET；不爆破、不执行 RCE/反序列化 payload、不读真实数据、不打内网。
HIT 判定：
  - 海康/设备 /ISAPI/System/deviceInfo 200 且含 deviceInfo -> 未授权设备信息面（弱密钥线）
  - 登录页含明确默认口令提示 -> 弱密钥线索
  - PaperCut / ActiveMQ / vCenter 等版本可读且落 KEV N-day 影响范围 -> RCE 疑似（不执行 PoC）
"""
import json, time, re, os
import requests, urllib3
urllib3.disable_warnings()

SRC = r"E:\kimi\scan\fofa_pool\edusrc_nday_slices_20261110.json"
OUT = r"E:\kimi\scan\fofa_pool\edusrc_r3_fp_20261110.json"
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

# (组名, 来源切片, 判定路径)
GROUPS = [
    ("hik_isapi",   hosts("edu_hik_isapi"),   ["/ISAPI/System/deviceInfo"]),
    ("access_ctrl", hosts("edu_access_ctrl"), ["/"]),
    ("papercut",    hosts("edu_papercut"),    ["/app", "/"]),
    ("activemq",    hosts("edu_activemq"),    ["/admin/", "/"]),
    ("vcenter",     hosts("edu_vcenter"),     ["/"]),
    ("bigip",       hosts("edu_bigip"),       ["/"]),
    ("ofbiz",       hosts("edu_ofbiz"),       ["/"]),
    ("zimbra",      hosts("edu_zimbra"),      ["/"]),
    ("netscaler",   hosts("edu_netscaler"),   ["/"]),
    ("esxi",        hosts("edu_esxi"),        ["/"]),
    ("h3c",         hosts("edu_h3c"),         ["/"]),
    ("ruijie",      hosts("edu_ruijie"),      ["/"]),
]
seen = set()
for g in GROUPS:
    g[1][:] = [h for h in g[1] if not (h in seen or seen.add(h))]

def scheme_for(h):
    if ":" in h:
        p = int(h.rsplit(":", 1)[1])
        return "http" if p in (3000, 8000, 8002, 8080, 8085, 8161, 9191, 9999, 4443, 9443, 5001) else "https"
    return "https"

def probe(host, path):
    url = scheme_for(host) + "://" + host + path
    try:
        r = s.get(url, timeout=7, verify=False, allow_redirects=False)
        b = r.text[:6000]
        m = re.search(r"<title[^>]*>(.*?)</title>", b, re.I | re.S)
        title = re.sub(r"\s+", " ", m.group(1)).strip()[:90] if m else ""
        low = b.lower()
        return {"url": url, "status": r.status_code, "len": len(r.content), "title": title,
                "ctype": r.headers.get("Content-Type", "")[:60],
                "server": r.headers.get("Server", "")[:60],
                "www_auth": r.headers.get("WWW-Authenticate", "")[:60],
                "device_info": ("<deviceinfo" in low or "devicename" in low or "devicemodel" in low),
                "default_pwd_hint": any(x in low for x in ["默认密码", "默认口令", "初始密码", "default password", "admin/12345", "初始口令"]),
                "version_hints": re.findall(r"(?:PaperCut|ActiveMQ|vCenter|BIG-IP|Zimbra|OFBiz|VMware ESXi)[^\n<]{0,40}?(\d+\.\d+(?:\.\d+)?)", b, re.I)[:3],
                "head": b[:220]}
    except Exception as e:
        return {"url": url, "status": None, "err": type(e).__name__ + ":" + str(e)[:80]}

def judge(g, recs):
    for r in recs:
        if g == "hik_isapi" and r.get("status") == 200 and r.get("device_info"):
            return True, "海康 /ISAPI/System/deviceInfo 未授权可读（设备信息面，弱密钥线）"
        if r.get("status") == 200 and r.get("default_pwd_hint"):
            return True, "登录页出现明确默认口令提示（弱密钥线索，需单组只读复核）"
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
        hit, why = judge(g, recs)
        results[tag] = {"group": g, "host": h, "probes": recs, "hit": hit, "why": why}
        last = recs[-1]
        print(("HIT " if hit else "    ") + g + " " + h + " -> " +
              ",".join(str(x.get("status")) for x in recs) + " " +
              (last.get("title") or "")[:38] +
              " dev=" + str(any(x.get("device_info") for x in recs)) +
              " pwdhint=" + str(any(x.get("default_pwd_hint") for x in recs)), flush=True)
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=1)
        if hit:
            stop = tag + " :: " + why
            break
    if stop:
        break
print("DONE", len(results), "STOP:", stop, flush=True)
