# -*- coding: utf-8 -*-
"""把公示页检出的数字分类为「学号」/「日期」/「电话」/「编号」，只保留学号。"""
import json, re, time, requests, urllib3
from collections import Counter
urllib3.disable_warnings()

SRC = r"E:\kimi\scan\fofa_pool\published_studentids_20261111.json"
OUT = r"E:\kimi\scan\fofa_pool\published_studentids_verified_20261111.json"
s = requests.Session(); s.trust_env = False
s.headers.update({"User-Agent": "Mozilla/5.0 Chrome/124"})

d = json.load(open(SRC, encoding="utf-8"))

def classify(nums):
    """按前缀族 + 长度 + 数量判断。学号特征：同长度成组出现、前缀为年级(20-26)或学院代码。"""
    by_len = {}
    for x in nums:
        by_len.setdefault(len(x), []).append(x)
    ids, others = [], []
    for L, arr in by_len.items():
        uniq = list(dict.fromkeys(arr))
        if L < 10 or L > 12:
            others.extend(uniq); continue
        # 日期：2026xxxx / 2025xxxx 且形如年月日
        date_like = [x for x in uniq if re.match(r"^(20\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])$", x)]
        rest = [x for x in uniq if x not in date_like]
        others.extend(date_like)
        # 同长度 >=4 个且非日期 → 视为学号列
        if len(rest) >= 4:
            ids.extend(rest)
        else:
            # 少量但前缀为 24/25/23/22/12/22 开头的 10 位，也判学号
            for x in rest:
                if x[:2] in ("19", "20", "21", "22", "23", "24", "25", "26", "12", "22"):
                    ids.append(x)
                else:
                    others.append(x)
    return list(dict.fromkeys(ids)), list(dict.fromkeys(others))

res = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
       "boundary": "只读公开公示页；只保留学号，不采集姓名/证件号；本清单仅存本地，不推公开仓库",
       "sources": []}
for src in d["sources"]:
    item = {"site": src["site"], "pages": []}
    for p in src.get("pages", []):
        nums = p.get("student_ids") or []
        if not nums:
            continue
        ids, others = classify(nums)
        rec = {"title": p["title"], "url": p["url"],
               "student_ids": ids[:60], "id_count": len(ids),
               "non_id_samples": others[:5], "non_id_count": len(others)}
        item["pages"].append(rec)
        print(src["site"].split("//")[-1][:24].ljust(24), p["title"][:38].ljust(38),
              "学号", len(ids), "其他", len(others), flush=True)
        if ids:
            print("      ", ids[:10], flush=True)
    if item["pages"]:
        res["sources"].append(item)
json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("DONE", flush=True)
