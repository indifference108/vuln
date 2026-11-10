# -*- coding: utf-8 -*-
"""
对「已公示初始密码规则」的 6 个同单位站点深挖公示名单，找同单位明文学号。
只 GET 公开公示页/附件；不登录、不爆破、不访问业务系统。
"""
import io, json, re, time, zipfile, requests, urllib3
from collections import Counter
urllib3.disable_warnings()

SRC = r"E:\kimi\scan\fofa_pool\edusrc_nday_slices_20261110.json"
OUT = r"E:\kimi\scan\fofa_pool\same_unit_studentids_20261111.json"
s = requests.Session(); s.trust_env = False
s.headers.update({"User-Agent": "Mozilla/5.0 Chrome/124"})

d = json.load(open(SRC, encoding="utf-8"))
UNIT_KEYS = ["x_njrts", "x_ncu", "x_xust", "x_lvu", "x_whcp", "x_tjnu"]
PUB_KW = ["公示", "名单", "录取", "拟录取", "获奖", "奖学金", "推免", "学号", "新生", "资格"]

def hosts(k):
    out = []
    for h in d.get(k, {}).get("hosts", []):
        host = h.lower(); base = host.split(":")[0]
        if base.endswith(".edu.cn") and base.count("edu.cn") == 1 and host not in out:
            out.append(host)
    return out

def absurl(base, href):
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        m = re.match(r"(https?://[^/]+)", base)
        return (m.group(1) if m else base.rstrip("/")) + href
    return base.rsplit("/", 1)[0] + "/" + href.lstrip("./")

def text_from(data, ctype):
    txt = ""
    if data[:4] == b"%PDF" or "pdf" in ctype:
        try:
            import pypdf
            for pg in pypdf.PdfReader(io.BytesIO(data)).pages[:15]:
                txt += (pg.extract_text() or "") + "\n"
        except Exception:
            return ""
    elif data[:2] == b"PK":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                for n in z.namelist():
                    if n.endswith(".xml") and any(k in n for k in ["document", "sheet", "sharedStrings"]):
                        txt += re.sub(r"<[^>]+>", " ", z.read(n).decode("utf-8", "ignore")) + "\n"
        except Exception:
            return ""
    else:
        for e in ("utf-8", "gb18030", "latin-1"):
            try:
                txt = data.decode(e); break
            except Exception:
                continue
    return txt

def extract_ids(txt):
    cands = re.findall(r"(?<!\d)(\d{8,12})(?!\d)", txt)
    uniq = list(dict.fromkeys(cands))
    # 排除日期
    uniq = [x for x in uniq if not re.match(r"^(20\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])$", x)]
    bylen = {}
    for x in uniq:
        bylen.setdefault(len(x), []).append(x)
    ids = []
    for L, arr in bylen.items():
        if 10 <= L <= 12 and len(arr) >= 3:
            ids.extend(arr)
        elif 10 <= L <= 12 and len(arr) >= 1 and any(a[:2] in ("23", "24", "25", "26", "12", "22") for a in arr):
            ids.extend(arr)
    return list(dict.fromkeys(ids))[:40]

res = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
       "boundary": "只 GET 公开公示页/附件；不登录、不爆破、不采集姓名/证件号；清单仅存本地不推公开仓库",
       "units": []}
for key in UNIT_KEYS:
    unit = key.replace("x_", "")
    item = {"unit": unit, "sites": []}
    for h in hosts(key)[:6]:
        site = "https://" + h + "/"
        rec = {"site": site, "pages": []}
        try:
            r = s.get(site, timeout=9, verify=False, allow_redirects=True)
            html = r.text[:250000]
            links = []
            for a in re.finditer(r'<a\s[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.I | re.S):
                t = re.sub(r"<[^>]+>", " ", a.group(2)); t = re.sub(r"&nbsp;|\s+", " ", t).strip()[:80]
                if t and any(k in t for k in PUB_KW):
                    links.append({"title": t, "url": absurl(r.url, a.group(1))})
            for x in re.findall(r'href\s*=\s*["\']([^"\']+\.(?:xlsx?|docx?|pdf))["\']', html, re.I)[:5]:
                links.append({"title": "(附件) " + x.split("/")[-1][:36], "url": absurl(r.url, x)})
            pages = [{"title": "(首页)", "url": r.url}] + links[:8]
        except Exception as e:
            rec["error"] = type(e).__name__ + ":" + str(e)[:70]
            item["sites"].append(rec); continue
        seen = set()
        for p in pages[:9]:
            if p["url"] in seen: continue
            seen.add(p["url"])
            try:
                rr = s.get(p["url"], timeout=12, verify=False, allow_redirects=True)
                ids = extract_ids(text_from(rr.content, rr.headers.get("Content-Type", "")))
                if ids:
                    rec["pages"].append({"title": p["title"], "url": p["url"][:170],
                                         "http": rr.status_code, "id_count": len(ids),
                                         "student_id_samples": ids[:12]})
                    print(unit.ljust(7), h[:32].ljust(32), p["title"][:28].ljust(28),
                          "ids", len(ids), ids[:4], flush=True)
            except Exception:
                pass
            time.sleep(1.1)
        item["sites"].append(rec)
    res["units"].append(item)
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("DONE", flush=True)
