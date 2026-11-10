# -*- coding: utf-8 -*-
"""
弱密钥「公示初始密码规则」验证模板 —— 脱敏 / 只判成功 / 不落地真实凭据
=========================================================================
用法（默认跑本地自建靶场，绝不碰生产）：
    C:\\Python312\\python.exe _weakpwd_login_template.py --selftest

用户自备公示材料后，由用户本人执行（或授权后执行）：
    ... _weakpwd_login_template.py --target https://{{TARGET}} \\
        --path {{LOGIN_PATH}} --ufield {{USER_FIELD}} --pfield {{PASS_FIELD}} \\
        --credentials <自备CSV> --i-have-authorization

硬约束（对齐 README 工作规范 / notes §9 / §7.14 川大模式）：
  * 单入口最多 5 组凭据，间隔 >=1.5s，不爆破、不遍历；
  * 只判定「登录是否成功 + 是否落到身份页」，**不翻阅、不保存任何业务数据/个人信息**；
  * 输出只记录序号与 vulnerable 布尔值，**不落地真实学号或证件号**；
  * 遇到验证码立即停止并提示用户人工破（notes §9：验证码用户来破）；
  * 真实目标一律以 {{TARGET}} 占位符表示；默认目标 127.0.0.1 自建靶场；
  * 生产目标必须显式传 --i-have-authorization，且脚本会再次打印红线提示。
"""
import argparse, csv, json, os, sys, time, re
import requests, urllib3
urllib3.disable_warnings()

OUT = r"E:\kimi\scan\fofa_pool\weakpwd_login_selftest_20261110.json"
CAPTCHA_MARKERS = ["validatecode", "captcha", "authcode", "imagecode", "验证码", "kaptcha", "randSesion"]
FAIL_MARKERS = ["账号或密码错误", "用户名或密码错误", "密码错误", "login failed", "invalid credentials", "账号不存在"]
SUCCESS_MARKERS = ["身份页", "个人中心", "welcome", "logout", "退出登录", "dashboard"]

def probe(target, path, ufield, pfield, rows, max_attempts=5, delay=1.5):
    s = requests.Session(); s.trust_env = False  # 国内目标直连，不走代理（notes §7.34）
    s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"})
    out = []
    for i, (sid, cred) in enumerate(rows[:max_attempts], 1):
        payload = {ufield: sid, pfield: cred}
        try:
            r = s.post(target.rstrip("/") + path, data=payload, timeout=8,
                       verify=False, allow_redirects=False)
            body = (r.text or "")[:4000]
            low = body.lower()
            loc = r.headers.get("Location", "") or ""
            # 遇验证码立即停，交用户人工破
            if any(k in low for k in CAPTCHA_MARKERS) or k_in(loc, CAPTCHA_MARKERS):
                out.append({"seq": i, "status": "CAPTCHA_GATE",
                            "note": "检测到验证码，已停止；按 notes §9 由用户人工破"})
                break
            ok = (r.status_code in (302, 303) and ("identity" in loc.lower() or "index" in loc.lower())) \
                 or (r.status_code == 200 and any(k in low for k in SUCCESS_MARKERS)
                     and not any(k in low for k in FAIL_MARKERS))
            out.append({"seq": i, "status": r.status_code, "http": r.status_code,
                        "vulnerable": bool(ok),
                        "note": "仅记录成功/失败判定，未保存响应正文与真实凭据"})
        except Exception as e:
            out.append({"seq": i, "status": None, "vulnerable": False,
                        "err": type(e).__name__ + ":" + str(e)[:80]})
        time.sleep(delay)
    return out

def k_in(s, markers):
    s = (s or "").lower()
    return any(k in s for k in markers)

def load_csv(p):
    rows = []
    with open(p, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append((r.get("sid", ""), r.get("credential", "")))
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true", help="跑本地 127.0.0.1:8792 自建靶场")
    ap.add_argument("--target", default="http://127.0.0.1:8792")
    ap.add_argument("--path", default="/login")
    ap.add_argument("--ufield", default="username")
    ap.add_argument("--pfield", default="password")
    ap.add_argument("--credentials", default=r"E:\kimi\scan\_weakpwd_demo_credentials.csv")
    ap.add_argument("--i-have-authorization", action="store_true")
    a = ap.parse_args()

    if not a.selftest and "127.0.0.1" not in a.target and not a.i_have_authorization:
        print("拒绝执行：生产目标必须显式传 --i-have-authorization，并确认已获书面授权。", file=sys.stderr)
        return 2
    if "127.0.0.1" not in a.target:
        print("== 红线提醒 ==\n1) 单入口 <=5 组、限速 1.5s、不爆破；\n"
              "2) 只判登录成功，不翻阅/不保存真实数据；\n"
              "3) 验证码交用户人工破；\n4) 全程录屏用于 CNVD 报送。\n")

    rows = load_csv(a.credentials)
    res = probe(a.target, a.path, a.ufield, a.pfield, rows)
    report = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "target": a.target,
              "selftest": a.selftest, "attempts": len(res), "results": res,
              "confirmed": sum(1 for x in res if x.get("vulnerable")),
              "note": "输出不含真实学号/证件号；生产登录未执行" if a.selftest else "由用户授权执行"}
    json.dump(report, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"attempts": len(res), "confirmed": report["confirmed"],
                      "results": res}, ensure_ascii=False, indent=1))
    return 0

if __name__ == "__main__":
    sys.exit(main())
