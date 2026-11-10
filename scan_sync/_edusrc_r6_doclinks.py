# -*- coding: utf-8 -*-
"""只读提取同单位公示站的「公示名单」链接标题（不落地任何真实学号/证件号）"""
import json, re, time, requests, urllib3
urllib3.disable_warnings()
OUT = r"E:\kimi\scan\fofa_pool\edusrc_r6_doclinks_20261110.json"
s = requests.Session(); s.trust_env = False
s.headers.update({"User-Agent": "Mozilla/5.0 Chrome/124"})

TARGETS = [
    ("ncu",  "https://rsc.ncu.edu.cn/"),
    ("ncu",  "https://jxmu.ncu.edu.cn/"),
    ("lvu",  "https://xsc.lvu.edu.cn/"),
    ("whcp", "https://rs.whcp.edu.cn/"),
    ("whcp", "https://ky.whcp.edu.cn/"),
    ("njrts","https://jjy.njrts.edu.cn/"),
    ("tjnu", "https://yjszs.tjnu.edu.cn/"),
]
KW = ["公示", "名单", "录取", "学号", "新生", "学位", "准考证", "身份证", "附件"]

def probe(unit, url):
    try:
        r = s.get(url, timeout=8, verify=False, allow_redirects=True)
        b = r.text[:250000]
        out = []
        for a in re.finditer(r'<a\s[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>', b, re.I | re.S):
            t = re.sub(r"<[^>]+>", " ", a.group(2)); t = re.sub(r"\s+", " ", t).strip()[:70]
            if t and any(k in t for k in KW):
                out.append({"text": t, "href": a.group(1)[:120]})
        docs = re.findall(r'href\s*=\s*["\']([^"\']+\.(?:xlsx?|docx?|pdf))["\']', b, re.I)
        return {"unit": unit, "url": url, "status": r.status_code,
                "matched_links": out[:12], "matched_count": len(out),
                "doc_links": docs[:8], "doc_count": len(docs),
                "note": "仅记录链接标题，不落地任何真实学号/证件号"}
    except Exception as e:
        return {"unit": unit, "url": url, "status": None, "err": type(e).__name__ + ":" + str(e)[:80]}

res = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "boundary": "只读 GET；不落地真实学号/证件号", "items": []}
for u, url in TARGETS:
    r = probe(u, url)
    res["items"].append(r)
    print(u.ljust(6), url.split("//")[-1][:34].ljust(34), "->", str(r.get("status")).ljust(5),
          "公示链接", r.get("matched_count"), "附件", r.get("doc_count"), flush=True)
    for l in (r.get("matched_links") or [])[:4]:
        print("     ", l["text"][:60], flush=True)
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    time.sleep(1.3)
print("DONE", flush=True)
