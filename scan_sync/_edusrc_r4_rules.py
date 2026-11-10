# -*- coding: utf-8 -*-
"""
第四轮：公示初始密码规则线（只读 GET 公开公示页）
只读提取公开页面里「初始密码/默认密码/学号后六位」附近的规则文本；
不登录、不爆破、不取真实学号/身份证数据、不访问真实用户数据。
已报送案例单位（fafu / 川大 / 河南农大 / 福建农林）标为重复，不重挖。
"""
import json, time, re, os
import requests, urllib3
urllib3.disable_warnings()

SRC = r"E:\kimi\scan\fofa_pool\edusrc_nday_slices_20261110.json"
OUT = r"E:\kimi\scan\fofa_pool\edusrc_r4_rules_20261110.json"
s = requests.Session(); s.trust_env = False
s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"})

d = json.load(open(SRC, encoding="utf-8"))
KEYS = ["edu_initpwd", "edu_defaultpwd", "edu_idcard6", "edu_zhcp", "edu_yjs"]
EXCLUDE = ["fafu.edu.cn", "scu.edu.cn", "ncwu.edu.cn", "henau.edu.cn"]  # 已报送/已定案单位

hosts = []
for k in KEYS:
    for h in d.get(k, {}).get("hosts", []):
        host = h.lower(); base = host.split(":")[0]
        if base.endswith(".edu.cn") and base.count("edu.cn") == 1 and host not in hosts:
            hosts.append(host)

KW = ["初始密码", "默认密码", "默认口令", "初始口令", "学号后六位", "身份证后六位",
      "身份证后", "密码为", "password is", "账号为", "用户名为"]
RULE_RE = re.compile(r"(.{0,90}(?:初始密码|默认密码|默认口令|初始口令|学号后六位|身份证后六位|密码为|账号为).{0,90})", re.S)

def probe(host):
    url = "https://" + host + "/"
    try:
        r = s.get(url, timeout=7, verify=False, allow_redirects=True)
        b = r.text[:120000]
        txt = re.sub(r"<script[^>]*>.*?</script>", " ", b, flags=re.S | re.I)
        txt = re.sub(r"<style[^>]*>.*?</style>", " ", txt, flags=re.S | re.I)
        txt = re.sub(r"<[^>]+>", " ", txt)
        txt = re.sub(r"\s+", " ", txt)
        m = re.search(r"<title[^>]*>(.*?)</title>", b, re.I | re.S)
        title = re.sub(r"\s+", " ", m.group(1)).strip()[:90] if m else ""
        hits = [k for k in KW if k in txt]
        snippets = RULE_RE.findall(txt)[:4]
        return {"host": host, "status": r.status_code, "title": title, "len": len(r.content),
                "final_url": r.url[:130], "keywords": hits, "rule_snippets": snippets,
                "excluded_duplicate": any(x in host for x in EXCLUDE)}
    except Exception as e:
        return {"host": host, "status": None, "err": type(e).__name__ + ":" + str(e)[:80],
                "excluded_duplicate": any(x in host for x in EXCLUDE)}

res = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
       "boundary": "只读 GET 公开公示页；不登录、不爆破、不取真实学号/身份证、不访问真实用户数据",
       "excluded_duplicates": EXCLUDE, "items": []}
for h in hosts[:32]:
    r = probe(h)
    res["items"].append(r)
    print(("DUP " if r.get("excluded_duplicate") else "    ") + h[:38].ljust(38),
          "->", str(r.get("status")).ljust(5), (r.get("title") or "")[:30].ljust(30),
          "kw:", ",".join(r.get("keywords", []))[:60], flush=True)
    if r.get("rule_snippets"):
        for sn in r["rule_snippets"][:2]:
            print("      RULE:", re.sub(r"\s+", " ", sn)[:150], flush=True)
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    time.sleep(1.2)
print("DONE", len(res["items"]), flush=True)
