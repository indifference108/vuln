# -*- coding: utf-8 -*-
"""
edusrc 轮：FOFA 域名限定新切片（2026-11-10）
用法: python _fofa_edusrc_20261110.py probe|1|2
停止条件: 出现人机验证/登录墙/查询被拦 -> 立即停并落证据
"""
import time, json, requests, sys, os

WB = "http://127.0.0.1:10086/command"
SES = "fofa-carrier"
OUT = r"E:\kimi\scan\fofa_pool\edusrc_nday_slices_20261110.json"

# 与历史不重复：10-19 已在 edu.cn 查过 6 个 AI 产品；10-16/17 在 gov/carrier 查过 Grafana/Nacos/eSight/Agile/VPN/OA；
# 本轮全部是 "host=edu.cn" + 传统 N-day 组件 / 未授权面 / 设备弱口令，此前从未按 edu.cn 限定跑过。
BATCH1 = {
    "edu_geoserver":    '(title="GeoServer" || body="GeoServer") && host="edu.cn"',
    "edu_jenkins":      '(title="Jenkins" || body="Jenkins") && host="edu.cn"',
    "edu_gitlab":       '(title="GitLab" || body="GitLab") && host="edu.cn"',
    "edu_confluence":   '(title="Confluence" || body="Confluence") && host="edu.cn"',
    "edu_weblogic":     '(title="WebLogic" || body="WebLogic") && host="edu.cn"',
    "edu_springboot":   '(title="Whitelabel Error Page" || body="Whitelabel Error Page") && host="edu.cn"',
}
BATCH2 = {
    "edu_grafana":      'title="Grafana" && host="edu.cn"',
    "edu_nacos":        'title="Nacos" && host="edu.cn"',
    "edu_druid":        '(title="Druid" || body="Druid Stat") && host="edu.cn"',
    "edu_tomcat":       'title="Apache Tomcat" && host="edu.cn"',
    "edu_solr":         '(title="Apache Solr" || body="Solr Admin") && host="edu.cn"',
    "edu_hardcode_pwd": 'body="type=password" && host="edu.cn"',
}
BATCH3 = {
    "edu_hikvision":    'body="doc/page/login.asp" && host="edu.cn"',
    "edu_printer":      '(body="HP LaserJet" || body="Brother" || body="Canon") && host="edu.cn"',
    "edu_jboss":        '(title="JBoss" || body="JBoss") && host="edu.cn"',
    "edu_zabbix":       'title="Zabbix" && host="edu.cn"',
    "edu_apollo":       '(title="Apollo" || body="apollo-adminservice") && host="edu.cn"',
    "edu_actuator":     'body="actuator" && host="edu.cn"',
}
# 第二轮：教育行业常见 OA / 中间件 / 弱口令面，历史从未按 edu.cn 限定跑过
BATCH4 = {
    "edu_thinkphp":  'body="ThinkPHP" && host="edu.cn"',
    "edu_exchange":  '(title="Outlook" || body="Exchange") && host="edu.cn"',
    "edu_ruoyi":     '(body="若依" || body="RuoYi") && host="edu.cn"',
    "edu_ecology":   'body="e-cology" && host="edu.cn"',
    "edu_tongda":    '(body="通达OA" || body="tongda") && host="edu.cn"',
    "edu_seeyon":    '(body="seeyon" || body="致远") && host="edu.cn"',
}
BATCH5 = {
    "edu_jumpserver": 'title="JumpServer" && host="edu.cn"',
    "edu_apisix":     '(title="Apache APISIX" || body="apisix") && host="edu.cn"',
    "edu_dvr":        'body="DVRDVS-Webs" && host="edu.cn"',
    "edu_kibana":     'title="Kibana" && host="edu.cn"',
    "edu_phpmyadmin": 'title="phpMyAdmin" && host="edu.cn"',
    "edu_swagger":    '(title="Swagger UI" || body="swagger-ui") && host="edu.cn"',
}
ALL = {"1": BATCH1, "2": BATCH2, "3": BATCH3, "4": BATCH4, "5": BATCH5,
       "probe": {"probe_jenkins": '(title="Jenkins" || body="Jenkins") && host="edu.cn"'}}


def wb(action, args, timeout=90):
    try:
        return requests.post(WB, json={"action": action, "args": args, "session": SES}, timeout=timeout).json()
    except Exception as e:
        return {"ok": False, "err": str(e)[:200]}


def ev(code):
    r = wb("evaluate", {"code": code})
    d = r.get("data") or {}
    if d.get("value") is not None:
        return d["value"]
    return json.dumps(r, ensure_ascii=False)[:400]


SET_QUERY = """(q) => {
  const ta = document.querySelector('textarea.el-textarea__inner');
  if (!ta) return 'no-ta';
  const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
  setter.call(ta, q);
  ta.dispatchEvent(new Event('input', {bubbles: true}));
  ta.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true}));
  ta.dispatchEvent(new KeyboardEvent('keypress', {key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true}));
  ta.dispatchEvent(new KeyboardEvent('keyup', {key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true}));
  return 'sent';
}"""

# 不用正则字面量（历史踩坑：daemon 会炸），一律 indexOf / split
EXTRACT = """(() => {
  const b = document.body ? document.body.innerText : '';
  const out = new Set();
  const lower = b.toLowerCase();
  const bad = (h) => h.indexOf('fofa.info') >= 0 || h.indexOf('fofa.so') >= 0 || h.indexOf('example.com') >= 0;
  const links = document.querySelectorAll('a[href]');
  for (let i = 0; i < links.length; i++) {
    let h = links[i].getAttribute('href') || '';
    if (h.indexOf('http://') !== 0 && h.indexOf('https://') !== 0) continue;
    if (bad(h)) continue;
    try { out.add(new URL(h).host); } catch (e) {}
  }
  const lines = b.split(String.fromCharCode(10)).map(s => s.trim());
  for (let i = 0; i < lines.length; i++) {
    const s = lines[i];
    if (s.length > 100 || s.length < 5) continue;
    if (s.indexOf('http://') !== 0 && s.indexOf('https://') !== 0) continue;
    if (bad(s)) continue;
    try { out.add(new URL(s).host); } catch (e) {}
  }
  const hosts = [];
  out.forEach(x => { if (x.indexOf('edu.cn') >= 0 || x.indexOf(':') >= 0) hosts.push(x); });
  const gate = lower.indexOf('captcha') >= 0 || lower.indexOf('人机') >= 0 ||
               lower.indexOf('verify you') >= 0 || lower.indexOf('just a moment') >= 0 ||
               lower.indexOf('请登录') >= 0 || lower.indexOf('log in to') >= 0 ||
               lower.indexOf('access denied') >= 0 || lower.indexOf('请求过于频繁') >= 0;
  const m = b.match(/([0-9][0-9,]*)\\s*(results|条)/i);
  return JSON.stringify({
    hosts: hosts.slice(0, 60), n: hosts.length,
    cnt: m ? m[1] : null,
    url: location.href.slice(0, 200),
    gate: gate,
    login_required: lower.indexOf('log in') >= 0,
    head: b.slice(0, 500)
  });
})()"""

mode = sys.argv[1] if len(sys.argv) > 1 else "probe"
DORKS = ALL[mode]
results = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}

print("navigate home", flush=True)
wb("navigate", {"url": "https://en.fofa.info/"})
time.sleep(9)

stop = None
for name, q in DORKS.items():
    if mode != "probe" and name in results and results[name].get("cnt") not in (None, "0"):
        print("skip(done)", name, flush=True)
        continue
    wb("navigate", {"url": "https://en.fofa.info/"})
    time.sleep(6)
    r = ev("(" + SET_QUERY + ")(" + json.dumps(q) + ")")
    print("set:", name, r, flush=True)
    time.sleep(10)
    v = ev(EXTRACT)
    print("==", name, (v or "")[:900], flush=True)
    try:
        item = json.loads(v)
    except Exception:
        item = {"raw": str(v)[:400], "gate": True}
    item["dork"] = q
    results[name] = item
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    if item.get("gate"):
        stop = name
        print("!!! GATE HIT, STOP:", name, flush=True)
        break
    time.sleep(5)

print("saved", len(results), "stop:", stop, flush=True)
