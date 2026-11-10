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
# === 第三轮：目标重设（判定点驱动） ===
# 弱密钥只挑「设备类」（CNVD 才给证，§7.28）；RCE 只挑 KEV 在册、版本/指纹可读的 N-day。
BATCH6 = {   # KEV 在册 N-day RCE，历史 31 切片从未查过
    "edu_papercut":  '(title="PaperCut" || body="PaperCut") && host="edu.cn"',
    "edu_activemq":  '(title="ActiveMQ" || body="ActiveMQ") && host="edu.cn"',
    "edu_vcenter":   '(title="vCenter" || body="ID_VC_Welcome") && host="edu.cn"',
    "edu_bigip":     '(title="BIG-IP" || body="BIG-IP") && host="edu.cn"',
    "edu_ofbiz":     '(title="OFBiz" || body="OFBiz") && host="edu.cn"',
    "edu_zimbra":    '(title="Zimbra" || body="Zimbra") && host="edu.cn"',
}
BATCH7 = {   # 设备类弱密钥（打印机/门禁/NVR/交换机），CNVD 给证对口
    "edu_access_ctrl":   '(title="门禁" || body="门禁管理系统") && host="edu.cn"',
    "edu_hik_isapi":     '(server="DVRDVS-Webs" || body="/ISAPI/") && host="edu.cn"',
    "edu_printer_panel": '(title="Web Image Monitor" || title="HP LaserJet") && host="edu.cn"',
    "edu_h3c":           '(title="H3C" || body="H3C") && host="edu.cn"',
    "edu_ruijie":        '(title="锐捷" || body="Ruijie") && host="edu.cn"',
    "edu_nvr":           '(title="NVR" || body="网络硬盘录像机") && host="edu.cn"',
}
BATCH8 = {   # 判定点精确切片 + 扩池
    "edu_papercut_p9191": 'title="PaperCut" && port="9191" && host="edu.cn"',
    "edu_activemq_p8161": 'title="ActiveMQ" && port="8161" && host="edu.cn"',
    "edu_springcloudgw":  'body="spring.cloud.gateway" && host="edu.cn"',
    "edu_esxi":           '(title="ESXi" || body="VMware ESXi") && host="edu.cn"',
    "edu_netscaler":      '(title="NetScaler" || body="Citrix Gateway") && host="edu.cn"',
    "edu_moveit":         '(body="MOVEit" || title="MOVEit") && host="edu.cn"',
}
# 第四轮：按项目已成功的弱密钥模式（公示初始密码规则 + 明文学号）反推目标，而非扫产品名
BATCH9 = {
    "edu_initpwd":    'body="初始密码" && host="edu.cn"',
    "edu_defaultpwd": 'body="默认密码" && host="edu.cn"',
    "edu_idcard6":    '(body="身份证后六位" || body="学号后六位") && host="edu.cn"',
    "edu_zhcp":       '(title="综合测评" || body="综合测评") && host="edu.cn"',
    "edu_yjs":        '(title="研究生综合服务" || body="研究生综合服务平台") && host="edu.cn"',
    "edu_xk":         '(title="校际课程互选" || body="校际课程互选") && host="edu.cn"',
}
# RCE 侧去掉泛 body 关键词，只用精确 title（降低门户页误报）
BATCH10 = {
    "edu_papercut_t": 'title="PaperCut" && host="edu.cn"',
    "edu_activemq_t": 'title="Apache ActiveMQ" && host="edu.cn"',
    "edu_zimbra_t":   'title="Zimbra Web Client" && host="edu.cn"',
    "edu_ofbiz_t":    'title="OFBiz" && host="edu.cn"',
    "edu_vcenter_t":  'title="VMware vCenter" && host="edu.cn"',
    "edu_bigip_t":    'title="BIG-IP" && host="edu.cn"',
}
# 第五轮：扩池（此前每 dork 只取免费版第 1 页）+ 补「公示明文学号」这一环
BATCH11 = {   # 公示名单 = 成功模式的另一半（§7.14/§7.16）
    "edu_publist_sid":  'body="学号" && body="公示" && host="edu.cn"',
    "edu_publist_title":'title="公示" && host="edu.cn" && port="80"',
    "edu_publist_lq":   '(body="录取名单" || body="拟录取名单") && host="edu.cn"',
    "edu_initpwd_p80":  'body="初始密码" && host="edu.cn" && port="80"',
    "edu_initpwd_p443": 'body="初始密码" && host="edu.cn" && port="443"',
    "edu_idcard6_after":'(body="身份证后六位" || body="学号后六位") && host="edu.cn" && after="2026-01-01"',
}
BATCH12 = {   # 设备弱密钥 / RCE 判定点扩池 + edu 限定的前端硬编码密码
    "edu_hardcode_val": 'body="type=password" && body="value=" && host="edu.cn"',
    "edu_isapi_p80":    'body="/ISAPI/" && host="edu.cn" && port="80"',
    "edu_access_p8080": '(title="门禁" || body="门禁管理系统") && host="edu.cn" && port="8080"',
    "edu_weblogic_t":   'title="WebLogic" && host="edu.cn"',
    "edu_jenkins_t":    'title="Jenkins" && host="edu.cn"',
    "edu_confluence_t": 'title="Confluence" && host="edu.cn"',
}
# 第六轮：同单位交叉——为已找到「初始密码规则」的单位，找它们自己的公示名单/学号源
BATCH13 = {
    "x_njrts": 'host="njrts.edu.cn" && (body="公示" || body="名单")',
    "x_ncu":   'host="ncu.edu.cn" && (body="公示" || body="名单")',
    "x_xust":  'host="xust.edu.cn" && (body="公示" || body="名单")',
    "x_lvu":   'host="lvu.edu.cn" && (body="公示" || body="名单")',
    "x_whcp":  'host="whcp.edu.cn" && (body="公示" || body="名单")',
    "x_tjnu":  'host="tjnu.edu.cn" && (body="公示" || body="准考证号")',
}
ALL = {"1": BATCH1, "2": BATCH2, "3": BATCH3, "4": BATCH4, "5": BATCH5,
       "6": BATCH6, "7": BATCH7, "8": BATCH8, "9": BATCH9, "10": BATCH10,
       "11": BATCH11, "12": BATCH12, "13": BATCH13,
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
  // 只在真正的 FOFA 验证页停机；结果明细里出现 captcha 字样（如 Citrix CSP 头）不算门禁
  const gate = (location.href.indexOf('/captcha') >= 0 &&
                (lower.indexOf('confirm humanity') >= 0 || b.indexOf('Please click in order') >= 0)) ||
               (lower.indexOf('824001') >= 0 && lower.indexOf('requires registered user') >= 0) ||
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
