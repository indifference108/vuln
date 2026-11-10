# -*- coding: utf-8 -*-
"""
第六轮：闭环检查（只读）
A) 同单位公示源：统计是否存在明文学号形态数字/名单附件，绝不落地真实号码
B) cqou.edu.cn 中间件群：Nacos / Actuator / XXL-JOB 未授权判定点（只读 GET，不爆破、不 POST）
"""
import json, re, time, requests, urllib3
urllib3.disable_warnings()

SRC = r"E:\kimi\scan\fofa_pool\edusrc_nday_slices_20261110.json"
OUT = r"E:\kimi\scan\fofa_pool\edusrc_r6_closure_20261110.json"
s = requests.Session(); s.trust_env = False
s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"})

d = json.load(open(SRC, encoding="utf-8"))
UNITS = {
    "njrts.edu.cn": "初始密码=身份证后六位@njrts",
    "ncu.edu.cn":   "密码=ncu@身份证后六位（继教）",
    "xust.edu.cn":  "初始密码=身份证后六位",
    "lvu.edu.cn":   "账号=学号，初始密码=身份证后六位",
    "whcp.edu.cn":  "用户名=学号，初始密码=身份证后六位",
    "tjnu.edu.cn":  "用户名=准考证号，初始密码=居民身份证号",
}

def hosts(k):
    out = []
    for h in d.get(k, {}).get("hosts", []):
        host = h.lower(); base = host.split(":")[0]
        if base.endswith(".edu.cn") and base.count("edu.cn") == 1 and host not in out:
            out.append(host)
    return out

def probe_pub(host, rule):
    try:
        r = s.get("https://" + host + "/", timeout=7, verify=False, allow_redirects=True)
        b = r.text[:200000]
        m = re.search(r"<title[^>]*>(.*?)</title>", b, re.I | re.S)
        title = re.sub(r"\s+", " ", m.group(1)).strip()[:70] if m else ""
        txt = re.sub(r"<script[^>]*>.*?</script>", " ", b, flags=re.S | re.I)
        txt = re.sub(r"<[^>]+>", " ", txt); txt = re.sub(r"\s+", " ", txt)
        ids = [x for x in re.findall(r"(?<!\d)([1-9]\d{7,11})(?!\d)", txt)
               if not (len(x) == 8 and x[:2] in ("19", "20"))]
        docs = re.findall(r'href\s*=\s*["\']([^"\']+\.(?:xlsx?|docx?|pdf))["\']', b, re.I)
        pubkw = [k for k in ["公示", "名单", "学号", "录取", "新生", "准考证号", "身份证"] if k in txt]
        return {"host": host, "unit_rule": rule, "status": r.status_code, "title": title,
                "id_like_count": len(ids), "doc_attachment_count": len(docs),
                "pub_keywords": pubkw,
                "closure_hint": len(ids) > 0 or len(docs) > 0,
                "note": "仅统计数量，不保存任何真实学号/证件号"}
    except Exception as e:
        return {"host": host, "unit_rule": rule, "status": None,
                "err": type(e).__name__ + ":" + str(e)[:70], "closure_hint": False}

def probe_endpoint(host, path, scheme="http"):
    url = scheme + "://" + host + path
    try:
        r = s.get(url, timeout=7, verify=False, allow_redirects=False)
        b = r.text[:4000]; low = b.lower()
        return {"url": url, "status": r.status_code, "len": len(r.content),
                "ctype": r.headers.get("Content-Type", "")[:60],
                "nacos_users": ('"username"' in low and "pageitems" in low) or "totalcount" in low,
                "actuator_links": '"_links"' in low,
                "actuator_sensitive": any(x in low for x in ["heapdump", '"/env"', "configprops", "mappings"]),
                "xxljob": "xxl-job" in low,
                "head": b[:150]}
    except Exception as e:
        return {"url": url, "status": None, "err": type(e).__name__ + ":" + str(e)[:70]}

res = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
       "boundary": "只读 GET；不登录、不爆破、不 POST、不执行 payload；不落地真实学号/证件号",
       "pub_sources": [], "middleware": []}

# A) 同单位公示源
for unit, rule in UNITS.items():
    key = {"njrts.edu.cn": "x_njrts", "ncu.edu.cn": "x_ncu", "xust.edu.cn": "x_xust",
           "lvu.edu.cn": "x_lvu", "whcp.edu.cn": "x_whcp", "tjnu.edu.cn": "x_tjnu"}[unit]
    for h in hosts(key)[:5]:
        r = probe_pub(h, rule)
        res["pub_sources"].append(r)
        print("PUB", unit.ljust(14), h[:36].ljust(36), "->", str(r.get("status")).ljust(5),
              "ids", r.get("id_like_count"), "docs", r.get("doc_attachment_count"),
              "kw", ",".join(r.get("pub_keywords", []))[:30], flush=True)
        json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        time.sleep(1.2)

# B) cqou.edu.cn 中间件群（精确 title=Jenkins 命中的同批泛域名）
MW = [
    ("nacos.cqou.edu.cn", "/nacos/v1/auth/users?pageNo=1&pageSize=1"),
    ("nacos.cqou.edu.cn", "/nacos/"),
    ("xxljob.cqou.edu.cn", "/xxl-job-admin/"),
    ("elastic.cqou.edu.cn", "/actuator"),
    ("skywalking.cqou.edu.cn", "/actuator"),
    ("jenkins.cqou.edu.cn", "/actuator"),
]
for h, p in MW:
    for sch in ("http", "https"):
        r = probe_endpoint(h, p, sch)
        res["middleware"].append(r)
        print("MW ", h[:30].ljust(30), sch, p[:40].ljust(40), "->", str(r.get("status")).ljust(5),
              "nacos", r.get("nacos_users"), "act", r.get("actuator_links"),
              "sens", r.get("actuator_sensitive"), flush=True)
        time.sleep(1.2)
        if r.get("status") == 200:
            break
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("DONE", flush=True)
