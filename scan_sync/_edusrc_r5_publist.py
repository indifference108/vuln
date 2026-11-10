# -*- coding: utf-8 -*-
"""只读检查公示名单页是否提供「明文学号源」（项目成功模式的另一半）
红线：只统计是否存在成串学号形态数字/名单附件，不落地、不存储、不使用任何真实学号或身份证号。
"""
import json, re, time, requests, urllib3
urllib3.disable_warnings()

SRC = r"E:\kimi\scan\fofa_pool\edusrc_nday_slices_20261110.json"
OUT = r"E:\kimi\scan\fofa_pool\edusrc_r5_publist_20261110.json"
s = requests.Session(); s.trust_env = False
s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"})

d = json.load(open(SRC, encoding="utf-8"))
KEYS = ["edu_publist_sid", "edu_publist_title", "edu_publist_lq"]
hosts = []
for k in KEYS:
    for h in d.get(k, {}).get("hosts", []):
        host = h.lower(); base = host.split(":")[0]
        if base.endswith(".edu.cn") and base.count("edu.cn") == 1 and host not in hosts:
            hosts.append(host)

def probe(host):
    url = "https://" + host + "/"
    try:
        r = s.get(url, timeout=8, verify=False, allow_redirects=True)
        b = r.text[:200000]
        m = re.search(r"<title[^>]*>(.*?)</title>", b, re.I | re.S)
        title = re.sub(r"\s+", " ", m.group(1)).strip()[:80] if m else ""
        # 只统计「数量/存在性」，绝不保存具体数字
        text = re.sub(r"<script[^>]*>.*?</script>", " ", b, flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        sid_like = re.findall(r"(?<!\d)([1-9]\d{7,11})(?!\d)", text)
        # 排除明显是日期/年份/电话的形态：只保留 8~12 位且不以 19/20 开头两位年份为主
        sid_like = [x for x in sid_like if not (len(x) == 8 and x[:2] in ("19", "20"))]
        docs = re.findall(r'href\s*=\s*["\']([^"\']+\.(?:xlsx?|docx?|pdf))["\']', b, re.I)
        pub_links = []
        for a in re.finditer(r'<a\s[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>', b, re.I | re.S):
            t = re.sub(r"<[^>]+>", " ", a.group(2)); t = re.sub(r"\s+", " ", t).strip()[:50]
            if t and any(k in t for k in ["公示", "名单", "录取", "学号", "新生", "学位"]):
                pub_links.append(t)
        return {"host": host, "status": r.status_code, "title": title,
                "final_url": r.url[:130], "len": len(r.content),
                "id_like_count": len(sid_like), "has_id_like": len(sid_like) > 0,
                "doc_attachment_count": len(docs), "has_doc_attachment": len(docs) > 0,
                "pub_link_samples": pub_links[:6], "pub_link_count": len(pub_links),
                "note": "仅统计数量，不保存任何真实学号/证件号"}
    except Exception as e:
        return {"host": host, "status": None, "err": type(e).__name__ + ":" + str(e)[:80]}

res = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
       "boundary": "只读 GET 公开公示页；只统计存在性，不落地/不使用任何真实学号或身份证号",
       "items": []}
for h in hosts:
    r = probe(h)
    res["items"].append(r)
    print(h[:40].ljust(40), "->", str(r.get("status")).ljust(5),
          (r.get("title") or "")[:26].ljust(26),
          "id_like", r.get("id_like_count"), "docs", r.get("doc_attachment_count"),
          "publinks", r.get("pub_link_count"), flush=True)
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    time.sleep(1.2)
print("DONE", len(res["items"]), flush=True)
