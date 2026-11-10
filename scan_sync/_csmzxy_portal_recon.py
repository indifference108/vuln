# -*- coding: utf-8 -*-
"""只读：找长沙民政职院自己的登录入口 + 初始密码规则公示（用于让 89 个学号闭环）"""
import re, json, time, requests, urllib3
urllib3.disable_warnings()
OUT = r"E:\kimi\scan\fofa_pool\csmzxy_portal_recon_20261111.json"
s = requests.Session(); s.trust_env = False
s.headers.update({"User-Agent": "Mozilla/5.0 Chrome/124"})

START = ["https://www.csmzxy.edu.cn/", "https://mzsg.csmzxy.edu.cn/", "https://cas.csmzxy.edu.cn/"]
KW_LINK = ["登录", "门户", "教务", "一卡通", "统一", "身份", "系统", "新生", "办事", "邮箱", "VPN", "智慧校园"]
KW_RULE = ["初始密码", "默认密码", "身份证后", "学号后", "初始口令", "默认口令", "密码规则", "首次登录"]
KEY_ALL = KW_LINK + KW_RULE + ["公示", "通知", "须知", "手册", "指南"]

def text(html):
    t = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.S | re.I)
    t = re.sub(r"<style[^>]*>.*?</style>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"&nbsp;|\s+", " ", t).strip()

def links(html, base):
    out = []
    for a in re.finditer(r'<a\s[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.I | re.S):
        href = a.group(1)
        t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", a.group(2))).strip()[:70]
        if not t or not any(k in t for k in KEY_ALL):
            continue
        if href.startswith("http"):
            u = href
        elif href.startswith("/"):
            m = re.match(r"(https?://[^/]+)", base)
            u = (m.group(1) if m else base.rstrip("/")) + href
        else:
            u = base.rsplit("/", 1)[0] + "/" + href.lstrip("./")
        out.append({"text": t, "url": u[:170]})
    return out[:40]

res = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
       "boundary": "只读 GET 公开页面；不登录、不爆破、不采集真实凭据", "pages": []}
seen = set()
queue = [(u, "(入口)") for u in START]
for depth in range(2):
    nxt = []
    for u, tag in queue[:14]:
        if u in seen:
            continue
        seen.add(u)
        try:
            r = s.get(u, timeout=9, verify=False, allow_redirects=True)
            t = text(r.text[:250000])
            rules = [k for k in KW_RULE if k in t]
            rec = {"url": u, "tag": tag, "http": r.status_code, "len": len(r.content),
                   "rules_found": rules, "title": (re.search(r"<title[^>]*>(.*?)</title>", r.text, re.I | re.S).group(1).strip()[:70]
                                                  if re.search(r"<title[^>]*>(.*?)</title>", r.text, re.I | re.S) else "")}
            res["pages"].append(rec)
            print(tag.ljust(8), u[:52].ljust(52), "->", r.status_code, "rules", rules, flush=True)
            if depth == 0:
                for l in links(r.text[:250000], r.url):
                    if l["url"] not in seen:
                        nxt.append((l["url"], l["text"][:26]))
        except Exception as e:
            res["pages"].append({"url": u, "tag": tag, "error": type(e).__name__ + ":" + str(e)[:60]})
        json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        time.sleep(1.1)
    queue = nxt[:14]
print("DONE pages", len(res["pages"]), flush=True)
