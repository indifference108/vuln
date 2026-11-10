# -*- coding: utf-8 -*-
"""
只读检查公开公示附件里是否含「明文学号」，用于回答「有没有学号」。
红线：不落地、不输出任何真实学号/证件号；只输出计数与掩码。
"""
import io, json, re, time, zipfile, requests, urllib3
urllib3.disable_warnings()

SRC = r"E:\kimi\scan\fofa_pool\edusrc_r6_doclinks_20261110.json"
OUT = r"E:\kimi\scan\fofa_pool\edusrc_publist_studentid_scan_20261110.json"
s = requests.Session(); s.trust_env = False
s.headers.update({"User-Agent": "Mozilla/5.0 Chrome/124"})

d = json.load(open(SRC, encoding="utf-8"))

def extract_text(url, data, ctype):
    """只从公开附件提取文本；绝不返回原文，只返回数字串计数与形态统计"""
    txt = ""
    if "pdf" in ctype or data[:4] == b"%PDF":
        try:
            import pypdf
            rd = pypdf.PdfReader(io.BytesIO(data))
            for pg in rd.pages[:12]:
                txt += (pg.extract_text() or "") + "\n"
        except Exception as e:
            return {"parse": "pdf_fail:" + type(e).__name__}
    elif data[:2] == b"PK":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                for n in z.namelist():
                    if n.endswith(".xml") and ("document" in n or "sheet" in n or "sharedStrings" in n):
                        txt += re.sub(r"<[^>]+>", " ", z.read(n).decode("utf-8", "ignore")) + "\n"
        except Exception as e:
            return {"parse": "zip_fail:" + type(e).__name__}
    else:
        try:
            txt = data.decode("utf-8", "ignore")
        except Exception:
            txt = data.decode("latin-1", "ignore")
        txt = re.sub(r"[^\x20-\x7e\u4e00-\u9fff\n]", " ", txt)

    nums = re.findall(r"(?<!\d)(\d{8,12})(?!\d)", txt)
    # 学号形态：以 20xx/19xx 年份开头的 10-12 位（排除纯日期 8 位）
    sid_like = [x for x in nums if len(x) >= 10 and x[:4] in
                [str(y) for y in range(1990, 2027)]]
    # 是否含姓名/学号等表头关键词
    kw = [k for k in ["学号", "姓名", "考生编号", "准考证号", "身份证", "公示", "录取", "名单"]
          if k in txt]
    return {"parse": "ok", "text_len": len(txt),
            "digit_8_12_count": len(nums), "student_id_like_count": len(sid_like),
            "sample_masked": [x[:4] + "*" * (len(x) - 4) for x in sid_like[:3]],
            "table_keywords": kw,
            "note": "仅输出计数与掩码，不落地任何真实号码"}

res = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
       "boundary": "只读 GET 公开公示附件；不落地/不输出真实学号或证件号；只给计数与掩码",
       "items": []}
for x in d["items"]:
    for l in (x.get("doc_links") or []):
        u = x["url"].rstrip("/") + l if l.startswith("/") else l
        try:
            r = s.get(u, timeout=15, verify=False)
            info = extract_text(u, r.content, r.headers.get("Content-Type", ""))
            info.update({"site": x["url"], "file": l.split("/")[-1], "url": u,
                         "http": r.status_code, "bytes": len(r.content),
                         "ctype": r.headers.get("Content-Type", "")[:45]})
        except Exception as e:
            info = {"site": x["url"], "file": l.split("/")[-1], "url": u,
                    "http": None, "err": type(e).__name__}
        res["items"].append(info)
        print(info.get("site", "").split("//")[-1][:22].ljust(22),
              info.get("file", "")[:20].ljust(20),
              "parse", str(info.get("parse"))[:12].ljust(12),
              "digits", info.get("digit_8_12_count"),
              "sid_like", info.get("student_id_like_count"),
              "kw", ",".join(info.get("table_keywords", []))[:30], flush=True)
        json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        time.sleep(1.3)
print("DONE", len(res["items"]), flush=True)
