# -*- coding: utf-8 -*-
"""本地自建金丝雀靶场：模拟「公示初始密码规则」登录，仅用于自检验证模板逻辑。
不监听外网，只绑 127.0.0.1:8792；不接触任何真实系统/真实数据。"""
import http.server, socketserver, urllib.parse, json, sys

PORT = 8792
DEMO_USERS = {
    "2026001001": "654321@mock",   # 命中：学号 + 证件后六位@mock
    "2026001002": "111111@mock",   # 不命中
}

FORM = """<!doctype html><html><head><title>演示登录</title></head><body>
<form method="post" action="/login">
<input name="username" placeholder="学号"><input name="password" type="password">
</form></body></html>"""

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/identity"):
            self.send_response(200); self.end_headers()
            self.wfile.write("<html><title>身份页 - 个人中心</title><body>welcome</body></html>".encode("utf-8"))
        else:
            self.send_response(200); self.end_headers(); self.wfile.write(FORM.encode())

    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0"))
        d = urllib.parse.parse_qs(self.rfile.read(n).decode())
        u = d.get("username", [""])[0]; p = d.get("password", [""])[0]
        if "captcha" in self.path:
            self.send_response(200); self.end_headers()
            self.wfile.write("<input name='validateCode' placeholder='验证码'>".encode())
            return
        if DEMO_USERS.get(u) == p:
            self.send_response(302); self.send_header("Location", "/identity"); self.end_headers()
        else:
            self.send_response(200); self.end_headers()
            self.wfile.write("账号或密码错误".encode())

if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), H) as srv:
        print("mock target on 127.0.0.1:%d" % PORT, flush=True)
        srv.serve_forever()
