# -*- coding: utf-8 -*-
"""只读检查规则公示站点是否同时提供明文学号/名单公示（决定线索能否闭环）"""
import json, re, time, requests, urllib3
urllib3.disable_warnings()

OUT = r"E:\kimi\scan\fofa_pool\edusrc_r4_chain_20261110.json"
s = requests.Session(); s.trust_env = False
s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"})

TARGETS = [
    ("天津师范大学研究生报考服务系统", "https://yjszs.tjnu.edu.cn/", "准考证号 / 初始密码=居民身份证号(18位)"),
    ("南京铁道职业技术学院统一身份认证", "https://webvpn.njrts.edu.cn/", "初始密码=身份证后六位@njrts"),
    ("浙江工商大学研究生教育综合管理", "https://yjszhgl.zjgsu.edu.cn/", "默认密码=ZJGSU#身份证倒数第7-2位；首次登录强制改密"),
    ("湖南现代物流职院图书馆", "https://library.hmlc.edu.cn/", "账号=学号/工号，初始密码=身份证后六位"),
    ("西安科技大学统一身份认证", "https://ids.xust.edu.cn/", "初始密码=身份证后六位（2016级前=学号）"),
    ("南昌大学继续教育学院", "https://scept.ncu.edu.cn/", "账号=身份证号或学号，密码=ncu@身份证后六位"),
    ("兰州职业技术学院统一支付", "https://pay.lvu.edu.cn/", "账号=学号，初始密码=身份证后六位"),
    ("武汉城市职业学院统一支付", "https://jfxt.whcp.edu.cn/", "用户名=学号，初始密码=身份证后六位"),
    ("大连职业技术学院统一身份认证", "https://webvpn.dlvtc.edu.cn/", "账号=10位学号，初始密码=原门户密码"),
    ("某统一身份认证平台", "https://authservernew.caii.edu.cn/", "首次登录强制修改默认密码"),
]
LINK_KW = ["公示", "名单", "学号", "录取", "新生", "学位", "公告", "通知", "查询"]

def probe(name, url, rule):
    try:
        r = s.get(url, timeout=8, verify=False, allow_redirects=True)
        b = r.text[:200000]
        links = []
        for m in re.finditer(r'<a\s[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>', b, re.I | re.S):
            href = m.group(1)
            txt = re.sub(r"<[^>]+>", " ", m.group(2))
            txt = re.sub(r"\s+", " ", txt).strip()[:60]
            if txt and any(k in txt for k in LINK_KW):
                links.append({"text": txt, "href": href[:120]})
        text = re.sub(r"<[^>]+>", " ", b)
        text = re.sub(r"\s+", " ", text)
        # 页面里是否出现成串的公开学号（8~12 位纯数字，且不是日期/电话）
        id_like = re.findall(r"(?<!\d)([1-9]\d{7,11})(?!\d)", text)[:5]
        return {"name": name, "url": url, "status": r.status_code,
                "rule": rule, "final_url": r.url[:130],
                "publist_links": links[:12], "publist_link_count": len(links),
                "plaintext_id_like_samples": id_like,
                "forced_change": ("强制" in rule or "首次登录" in rule or "必须重新设置" in rule)}
    except Exception as e:
        return {"name": name, "url": url, "rule": rule, "status": None,
                "err": type(e).__name__ + ":" + str(e)[:80]}

res = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
       "boundary": "只读 GET 公开页面；不登录、不爆破、不收集真实学号/身份证号（仅统计是否存在成串数字）",
       "items": []}
for name, url, rule in TARGETS:
    r = probe(name, url, rule)
    res["items"].append(r)
    print(name[:22].ljust(22), "->", str(r.get("status")).ljust(5),
          "公示链接", r.get("publist_link_count"), "| 页面数字串", len(r.get("plaintext_id_like_samples", [])),
          "| 强制改密", r.get("forced_change"), flush=True)
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    time.sleep(1.3)
print("DONE", flush=True)
