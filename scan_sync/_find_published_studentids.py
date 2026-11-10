# -*- coding: utf-8 -*-
"""
从学校「自己公开发布的公示名单」里提取明文学号（edusrc 报送取证用）
范围：只 GET 公开公示页与公开附件；不登录、不爆破、不访问任何业务系统。
输出：来源 URL + 公示标题 + 学号列表（只保留学号，不采集姓名/证件号）。
"""
import io, json, re, time, zipfile, requests, urllib3, os
urllib3.disable_warnings()

OUT = r"E:\kimi\scan\fofa_pool\published_studentids_20261111.json"
s = requests.Session(); s.trust_env = False
s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"})

SITES = [
    "https://mzsg.csmzxy.edu.cn/",
    "https://graduate.cug.edu.cn/",
    "https://bkzs.ouc.edu.cn/",
    "https://www.yjszs.sdnu.edu.cn/",
    "https://jiaowu.sicau.edu.cn/",
    "https://yz.ouc.edu.cn/",
    "https://clxy.kmust.edu.cn/",
    "https://3lists.jzmu.edu.cn/",
    "https://wsps.xidian.edu.cn/",
]
PUB_KW = ["公示", "名单", "录取", "拟录取", "获奖", "奖学金", "推免", "复审", "资格", "学号"]
YEAR_PREFIX = tuple(str(y) for y in range(2018, 2028))

def absurl(base, href):
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        m = re.match(r"(https?://[^/]+)", base)
        return (m.group(1) if m else base.rstrip("/")) + href
    return base.rsplit("/", 1)[0] + "/" + href.lstrip("./")

def text_from(url, data, ctype):
    txt = ""
    if data[:4] == b"%PDF" or "pdf" in ctype:
        try:
            import pypdf
            rd = pypdf.PdfReader(io.BytesIO(data))
            for pg in rd.pages[:20]:
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
        enc = "utf-8"
        for e in ("utf-8", "gb18030", "latin-1"):
            try:
                txt = data.decode(e); break
            except Exception:
                continue
    return txt

def student_ids(txt):
    """学号形态：10-12 位、以 2018-2027 开头，或表格里成组出现的 8-12 位纯数字"""
    cands = re.findall(r"(?<!\d)(\d{8,12})(?!\d)", txt)
    out = []
    for x in cands:
        if len(x) >= 10 and x[:4] in YEAR_PREFIX:
            out.append(x)
    # 同一页面大量等长数字（表格列）也算
    from collections import Counter
    c = Counter(len(x) for x in cands)
    common = [L for L, n in c.items() if n >= 5 and 8 <= L <= 12]
    if common:
        for x in cands:
            if len(x) in common and x not in out:
                out.append(x)
    return list(dict.fromkeys(out))

def links_from(url, html):
    out = []
    for a in re.finditer(r'<a\s[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.I | re.S):
        href, t = a.group(1), re.sub(r"<[^>]+>", " ", a.group(2))
        t = re.sub(r"&nbsp;|\s+", " ", t).strip()[:90]
        if t and any(k in t for k in PUB_KW):
            out.append({"title": t, "url": absurl(url, href)})
    return out[:14]

res = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
       "boundary": "只 GET 公开公示页/附件；不登录、不爆破、不访问业务系统；只保留学号，不采集姓名/证件号",
       "sources": []}

for site in SITES:
    item = {"site": site, "pages": []}
    try:
        r = s.get(site, timeout=10, verify=False, allow_redirects=True)
        html = r.text[:300000]
        links = links_from(r.url, html)
        # 首页本身也查一遍
        pages = [{"title": "(首页)", "url": r.url}] + [{"title": x["title"], "url": x["url"]} for x in links]
        # 首页若有附件链接也加进来
        for d in re.findall(r'href\s*=\s*["\']([^"\']+\.(?:xlsx?|docx?|pdf))["\']', html, re.I)[:8]:
            pages.append({"title": "(附件) " + d.split("/")[-1][:40], "url": absurl(r.url, d)})
    except Exception as e:
        item["error"] = type(e).__name__ + ":" + str(e)[:80]
        res["sources"].append(item)
        print(site, "ERR", item["error"], flush=True)
        continue

    seen = set()
    for p in pages[:12]:
        if p["url"] in seen:
            continue
        seen.add(p["url"])
        try:
            rr = s.get(p["url"], timeout=12, verify=False, allow_redirects=True)
            ct = rr.headers.get("Content-Type", "")
            txt = text_from(p["url"], rr.content, ct)
            ids = student_ids(txt)
            rec = {"title": p["title"], "url": p["url"][:180], "http": rr.status_code,
                   "bytes": len(rr.content), "student_ids": ids[:40], "id_count": len(ids)}
            item["pages"].append(rec)
            print(site.split("//")[-1][:22].ljust(22), p["title"][:34].ljust(34),
                  "->", rr.status_code, "ids", len(ids), flush=True)
            if ids:
                print("      ", ids[:8], flush=True)
        except Exception as e:
            item["pages"].append({"title": p["title"], "url": p["url"][:180],
                                  "error": type(e).__name__})
        time.sleep(1.2)
    res["sources"].append(item)
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("DONE", sum(len(x.get("pages", [])) for x in res["sources"]), "pages", flush=True)
