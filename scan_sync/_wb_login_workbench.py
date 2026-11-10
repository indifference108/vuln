# -*- coding: utf-8 -*-
"""浏览器半自动验证作业台（本地控制台，127.0.0.1:8795）。

分工：
  - 脚本接管 Chrome：打开登录页、自动填学号、轮询判定登录结果、自动回填 CSV、
    自动进入下一行、保存无敏感信息的结果证据。
  - 用户做人机：在 Chrome 登录页亲手输入【密码 + 验证码】并点击登录。
红线：
  - 绝不读取/保存密码框内容；绝不代填或代提交密码与验证码。
  - 不翻阅登录后的任何真实用户数据；只判 URL 与是否出现成功/失败提示词。
  - 单入口连续尝试上限 5 组；命中 / 账号锁定 / 强制改密 立即停并提示录屏。
  - 含真实学号的 CSV 只存本地，不推公开仓库。
"""
import csv, json, os, re, threading, time, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

WB = "http://127.0.0.1:10086/command"
SES = "edusrc-login"
ENTRY = "https://ehall.csmzxy.edu.cn/"
CSV_PATH = r"E:\kimi\scan\需调试学号清单_20261111.csv"
EVID_DIR = r"E:\kimi\scan\login_evidence"
STATE_JSON = r"E:\kimi\scan\fofa_pool\login_workbench_state_20261111.json"
PORT = 8795
MAX_STREAK = 5

import requests

os.makedirs(EVID_DIR, exist_ok=True)
os.makedirs(os.path.dirname(STATE_JSON), exist_ok=True)

rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8-sig")))
COLS = list(rows[0].keys())

LOCK = threading.Lock()
STATE = {
    "idx": 0,                 # 当前处理 rows 下标
    "attempts_streak": 0,     # 连续尝试计数
    "running": True,
    "auto_next": False,
    "events": [],
    "last": None,
}


def log(msg):
    with LOCK:
        STATE["events"].insert(0, "%s  %s" % (time.strftime("%H:%M:%S"), msg))
        STATE["events"] = STATE["events"][:40]
    print("[workbench]", msg, flush=True)


def save_csv():
    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)


def wb(action, args=None, timeout=45):
    p = {"action": action, "args": args or {}, "session": SES}
    try:
        return requests.post(WB, json=p, timeout=timeout).json()
    except Exception as e:
        return {"ok": False, "err": str(e)[:160]}


def ev(code):
    r = wb("evaluate", {"code": code})
    d = r.get("data") or {}
    v = d.get("value")
    if v is None:
        return None
    try:
        return json.loads(v) if isinstance(v, str) and v.strip().startswith("{") else v
    except Exception:
        return v


PROBE = r"""(() => {
  const b = document.body ? document.body.innerText : '';
  const u = location.href;
  const has = (s) => b.indexOf(s) >= 0;
  const onLogin = /\/authserver\/login/.test(u);
  return JSON.stringify({
    url: u.slice(0, 220),
    title: (document.title || '').slice(0, 90),
    textlen: b.length,
    onLogin: onLogin,
    success: !onLogin && (has('退出') || has('个人中心') || has('办事大厅') || has('欢迎您') || has('我的应用')),
    errPwd: has('用户名或密码错误') || has('密码错误') || has('认证失败') || has('用户名不存在'),
    errCaptcha: has('验证码错误') || has('验证码不正确') || has('验证码已失效'),
    locked: has('账号已被锁定') || has('账号已锁定') || has('已被禁用') || has('账号已被禁用'),
    mustChange: has('首次登录必须修改') || has('密码已过期') || has('强制修改密码') || /changePassword|updatePassword|forceModify/i.test(u),
    hint: b.slice(0, 200).replace(/\s+/g, ' ')
  });
})()"""


def fill_sid(sid):
    code = """(() => {
  const f = document.getElementById('pwdFromId');
  const inp = f ? f.querySelector('#username') : null;
  if (!inp) return 'NO_FORM';
  inp.value = %s;
  inp.dispatchEvent(new Event('input', {bubbles:true}));
  inp.dispatchEvent(new Event('change', {bubbles:true}));
  return 'OK';
})()""" % json.dumps(sid)
    r = wb("evaluate", {"code": code})
    d = r.get("data") or {}
    return d.get("value", "ERR")


def open_row(i):
    """打开登录页并自动填学号，等待用户做人机。"""
    if i >= len(rows):
        log("清单已跑完")
        return
    sid = rows[i]["账号"]
    tag = rows[i]["调试序号"]
    wb("navigate", {"url": ENTRY})
    time.sleep(5)
    res = fill_sid(sid)
    if res == "NO_FORM":
        time.sleep(3)
        res = fill_sid(sid)
    log("%s 学号 %s 已自动填入（填表结果 %s）→ 请你输密码+验证码并点登录" % (tag, sid, res))
    with LOCK:
        STATE["last"] = None


def record(verdict, probe):
    """回填 CSV + 保存不含密码的证据。"""
    with LOCK:
        i = STATE["idx"]
        r = rows[i]
    tag, sid = r["调试序号"], r["账号"]
    r["调试状态(你填)"] = verdict
    r["调试结果/录屏(你填)"] = "%s 自动判定：%s（录屏请自行补充）" % (
        time.strftime("%Y-%m-%d %H:%M:%S"), verdict)
    save_csv()
    ev_path = os.path.join(EVID_DIR, "%s_%s.json" % (tag, sid))
    json.dump({
        "tag": tag, "student_id": sid, "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "verdict": verdict, "url": probe.get("url"), "title": probe.get("title"),
        "hint": (probe.get("hint") or "")[:200],
        "note": "只记录 URL 与结果提示词；不含密码、验证码、真实用户数据",
    }, open(ev_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump({"idx": STATE["idx"], "streak": STATE["attempts_streak"],
               "verdict": verdict, "ts": time.strftime("%Y-%m-%d %H:%M:%S")},
              open(STATE_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log("%s %s → %s" % (tag, sid, verdict))
    return verdict


def poll_loop():
    """每 2 秒判定一次登录结果；命中/锁定/强制改密立即停。"""
    while True:
        time.sleep(2)
        with LOCK:
            if not STATE["running"]:
                continue
            i = STATE["idx"]
            if i >= len(rows):
                continue
            if rows[i]["调试状态(你填)"].strip():
                continue
        p = ev(PROBE)
        if not isinstance(p, dict):
            continue
        verdict = None
        if p.get("success"):
            verdict = "命中"
        elif p.get("locked"):
            verdict = "账号锁定(停)"
        elif p.get("mustChange"):
            verdict = "强制改密(死线)"
        elif p.get("errPwd"):
            verdict = "失败"
        elif p.get("errCaptcha"):
            verdict = "验证码挡住"
        if not verdict:
            continue
        record(verdict, p)
        with LOCK:
            STATE["attempts_streak"] += 1
            stop = verdict in ("命中", "账号锁定(停)") or STATE["attempts_streak"] >= MAX_STREAK
            auto = STATE["auto_next"] and not stop
            STATE["last"] = {"verdict": verdict, "tag": rows[i]["调试序号"], "hint": p.get("hint", "")[:120]}
        if stop:
            log("停止：%s（连续尝试 %d 组）→ 请录屏留证" % (verdict, STATE["attempts_streak"]))
            with LOCK:
                STATE["running"] = False
        elif auto:
            time.sleep(3)
            with LOCK:
                STATE["idx"] += 1
            open_row(STATE["idx"])


HTML = r"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>edusrc 弱密钥 · 浏览器验证作业台</title>
<style>
body{font:14px/1.6 -apple-system,"Microsoft YaHei",sans-serif;background:#f5f7fa;color:#1f2937;margin:0;padding:24px}
.wrap{max-width:1000px;margin:0 auto}
h1{font-size:20px;margin:0 0 6px}.sub{color:#6b7280;margin-bottom:18px}
.card{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:18px;margin-bottom:14px;box-shadow:0 1px 2px rgba(0,0,0,.03)}
.current{font-size:17px;font-weight:600;margin-bottom:8px}
.sid{font:700 26px/1.3 Consolas,monospace;color:#0f766e;letter-spacing:1px}
.kv{display:grid;grid-template-columns:120px 1fr;gap:6px 12px;margin-top:12px;color:#374151}
.kv b{color:#6b7280;font-weight:500}
button{border:0;border-radius:7px;padding:9px 16px;font-size:14px;cursor:pointer;margin:4px 6px 4px 0}
.p{background:#0f766e;color:#fff}.s{background:#e5e7eb;color:#111827}.w{background:#fef3c7;color:#92400e}.d{background:#fee2e2;color:#991b1b}
.bar{height:8px;background:#e5e7eb;border-radius:4px;overflow:hidden;margin:10px 0}.bar i{display:block;height:100%;background:#0f766e}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:6px 8px;border-bottom:1px solid #eef2f7;text-align:left}
.ok{color:#0f766e;font-weight:600}.bad{color:#b91c1c}.warn{color:#b45309}
#log{background:#111827;color:#d1fae5;border-radius:8px;padding:12px;height:170px;overflow:auto;font:12px/1.6 Consolas,monospace;white-space:pre-wrap}
.tip{background:#ecfdf5;border:1px solid #a7f3d0;color:#065f46;border-radius:8px;padding:12px;margin-bottom:14px}
label{display:inline-flex;align-items:center;gap:6px;margin-right:16px}
</style></head><body><div class="wrap">
<h1>edusrc 弱密钥 · 浏览器验证作业台</h1>
<div class="sub">脚本接管 Chrome 自动填学号 / 判结果 / 回填表格；你只做人机：在登录页输<b>密码 + 验证码</b>并点登录。</div>
<div class="tip"><b>操作顺序</b>：① 看下面的当前学号 → ② 切到 Chrome 的「统一身份认证平台」标签页（账号已自动填好）→ ③ 你填密码、点登录（验证码当前不显示，失败几次后若弹出由你破）→ ④ 这里自动显示判定并回填 CSV → ⑤ 点「下一行」继续。命中会立即停机，请录屏留证。<br>
<b>密码从哪来</b>：学校公开 PDF 只写「默认身份证后六位」；已复核 4 个公示名单页 <b>均无证件号</b>（只有学号+姓名），所以这列必须你自备、亲手填。同类 CAS 偶见「学号」兜底口令（见长江师范学院等公开说明），是否试由你决定，脚本不代填、不猜测。</div>
<div class="card">
  <div class="current">当前行：<span id="tag">—</span> <span id="status" class="warn">等待</span></div>
  <div class="sid" id="sid">—</div>
  <div class="kv">
    <b>登录 URL</b><span>https://ehall.csmzxy.edu.cn/ → authserver.csmzxy.edu.cn/authserver/login</span>
    <b>密码</b><span>你本人填（默认身份证后六位，大写）；脚本不读取、不保存</span>
    <b>验证码</b><span>你本人破；脚本不识别、不代填</span>
    <b>来源</b><span id="src">—</span>
    <b>进度</b><span id="prog">—</span>
  </div>
  <div class="bar"><i id="bar" style="width:0%"></i></div>
  <button class="p" onclick="act('next')">下一行（自动填学号）</button>
  <button class="s" onclick="act('restart')">重新打开当前行</button>
  <button class="w" onclick="act('mark&v=验证码挡住')">标记：验证码挡住</button>
  <button class="w" onclick="act('mark&v=强制改密(死线)')">标记：强制改密</button>
  <button class="d" onclick="act('stop')">停止</button>
  <div style="margin-top:8px"><label><input type="checkbox" id="auto" onchange="autoNext(this.checked)"> 失败后自动换行</label>
  <span style="color:#6b7280">连续尝试上限 <b>5</b> 组；命中 / 锁定 / 强制改密自动停</span></div>
</div>
<div class="card"><h3 style="margin:0 0 8px;font-size:15px">最近判定</h3><table id="tbl"><thead><tr><th>调试序号</th><th>学号</th><th>状态</th><th>来源</th></tr></thead><tbody></tbody></table></div>
<div class="card"><h3 style="margin:0 0 8px;font-size:15px">运行日志</h3><div id="log"></div></div>
</div><script>
function act(x){fetch('/api/'+x).then(r=>r.json()).then(refresh)}
function autoNext(v){fetch('/api/auto?v='+(v?1:0)).then(r=>r.json()).then(refresh)}
function refresh(){fetch('/api/state').then(r=>r.json()).then(d=>{
  const c=d.current||{};
  document.getElementById('tag').textContent=c.tag||'—';
  document.getElementById('sid').textContent=c.sid||'—';
  document.getElementById('src').textContent=c.src||'—';
  document.getElementById('prog').textContent=d.done+' / '+d.total+' 已判定，连续尝试 '+d.streak+' 组';
  document.getElementById('bar').style.width=(d.done/d.total*100).toFixed(1)+'%';
  const st=document.getElementById('status');
  st.textContent=d.running?(d.last?('已判定：'+d.last.verdict):'等待你做人机'):'已停机';
  st.className=d.last&&d.last.verdict==='命中'?'ok':(d.running?'warn':'bad');
  document.getElementById('auto').checked=!!d.auto_next;
  let h='';(d.recent||[]).forEach(r=>{h+='<tr><td>'+r.tag+'</td><td><code>'+r.sid+'</code></td><td class="'+(r.status==='命中'?'ok':(r.status.includes('停')||r.status.includes('死线')?'bad':''))+'">'+r.status+'</td><td>'+(r.src||'').slice(0,42)+'</td></tr>'});
  document.querySelector('#tbl tbody').innerHTML=h;
  document.getElementById('log').textContent=(d.events||[]).join('\n');
})}
setInterval(refresh,1500);refresh();
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body, ctype="application/json; charset=utf-8"):
        b = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/":
            return self._send(HTML, "text/html; charset=utf-8")
        if u.path == "/api/state":
            with LOCK:
                i = STATE["idx"]
                c = rows[i] if i < len(rows) else {}
                recent = [{"tag": r["调试序号"], "sid": r["账号"],
                           "status": r["调试状态(你填)"], "src": r["来源公示页"]}
                          for r in rows if r["调试状态(你填)"].strip()][-12:][::-1]
                return self._send(json.dumps({
                    "current": {"tag": c.get("调试序号"), "sid": c.get("账号"),
                                "src": c.get("来源公示页")},
                    "done": sum(1 for r in rows if r["调试状态(你填)"].strip()),
                    "total": len(rows), "streak": STATE["attempts_streak"],
                    "running": STATE["running"], "auto_next": STATE["auto_next"],
                    "last": STATE["last"], "recent": recent, "events": STATE["events"],
                }, ensure_ascii=False))
        if u.path == "/api/next":
            with LOCK:
                # 跳过已判定的行
                while STATE["idx"] < len(rows) and rows[STATE["idx"]]["调试状态(你填)"].strip():
                    STATE["idx"] += 1
                STATE["running"] = True
                i = STATE["idx"]
            if i < len(rows):
                threading.Thread(target=open_row, args=(i,), daemon=True).start()
            return self._send('{"ok":true}')
        if u.path == "/api/restart":
            with LOCK:
                STATE["running"] = True
                i = STATE["idx"]
            threading.Thread(target=open_row, args=(i,), daemon=True).start()
            return self._send('{"ok":true}')
        if u.path == "/api/mark":
            v = (q.get("v") or [""])[0]
            if v:
                record(v, {"url": "", "title": "", "hint": "用户手动标记"})
                with LOCK:
                    STATE["last"] = {"verdict": v, "tag": rows[STATE["idx"]]["调试序号"], "hint": ""}
            return self._send('{"ok":true}')
        if u.path == "/api/stop":
            with LOCK:
                STATE["running"] = False
            log("用户手动停机")
            return self._send('{"ok":true}')
        if u.path == "/api/auto":
            with LOCK:
                STATE["auto_next"] = (q.get("v") or ["0"])[0] == "1"
            log("失败后自动换行：" + ("开" if STATE["auto_next"] else "关"))
            return self._send('{"ok":true}')
        return self._send('{"ok":false,"err":"unknown"}')


if __name__ == "__main__":
    # 预先打开第一行（只读导航 + 自动填学号，不提交任何凭据）
    with LOCK:
        while STATE["idx"] < len(rows) and rows[STATE["idx"]]["调试状态(你填)"].strip():
            STATE["idx"] += 1
    if STATE["idx"] < len(rows):
        threading.Thread(target=open_row, args=(STATE["idx"],), daemon=True).start()
    threading.Thread(target=poll_loop, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    print("workbench: http://127.0.0.1:%d  | rows=%d" % (PORT, len(rows)), flush=True)
    srv.serve_forever()
