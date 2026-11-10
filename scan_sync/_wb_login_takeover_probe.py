# -*- coding: utf-8 -*-
"""接管浏览器：只读打开长沙民政职院统一身份登录页，勘察表单/验证码/结果判据。
不提交任何凭据，不读取密码框内容，不翻阅登录后数据。
"""
import json, time, requests

WB = "http://127.0.0.1:10086/command"
SES = "edusrc-login"


def call(action, args=None, timeout=60):
    p = {"action": action, "args": args or {}, "session": SES}
    try:
        return requests.post(WB, json=p, timeout=timeout).json()
    except Exception as e:
        return {"ok": False, "err": str(e)[:200]}


def ev(code):
    r = call("evaluate", {"code": code})
    d = r.get("data") or {}
    return d.get("value") if d.get("value") is not None else json.dumps(r, ensure_ascii=False)[:600]


r = call("navigate", {"url": "https://ehall.csmzxy.edu.cn/"})
print("navigate:", json.dumps(r, ensure_ascii=False)[:300], flush=True)
time.sleep(7)

CHECK = r"""(() => {
  const b = document.body ? document.body.innerText : '';
  const forms = Array.from(document.forms).map(f => ({
    action: f.getAttribute('action') || '',
    method: f.getAttribute('method') || '',
    id: f.id || '',
    fields: Array.from(f.querySelectorAll('input')).map(i => ({
      name: i.name || '', id: i.id || '', type: i.type || '',
      placeholder: i.placeholder || '', hidden: i.type === 'hidden'
    }))
  }));
  const imgs = Array.from(document.images).map(i => ({
    src: (i.getAttribute('src') || '').slice(0, 120),
    id: i.id || '', cls: (i.className || '').slice(0, 60)
  })).filter(x => /captcha|verify|code|kaptcha|image/i.test(x.src + x.id + x.cls));
  const kw = ['验证码', 'captcha', '身份', '登录', '学号', '密码', '错误', '锁定', '退出', '个人中心', '办事大厅'];
  return JSON.stringify({
    url: location.href.slice(0, 220),
    title: (document.title || '').slice(0, 120),
    textlen: b.length,
    head: b.slice(0, 500),
    kw: kw.filter(k => b.indexOf(k) >= 0),
    forms: forms,
    captchaImgs: imgs,
    hasPasswordInput: !!document.querySelector('input[type=password]')
  });
})()"""
v = ev(CHECK)
try:
    d = json.loads(v)
    print("url:", d["url"])
    print("title:", d["title"], "| textlen:", d["textlen"])
    print("head:", d["head"][:300].replace("\n", " "))
    print("kw:", d["kw"])
    print("hasPasswordInput:", d["hasPasswordInput"])
    print("captchaImgs:", json.dumps(d["captchaImgs"], ensure_ascii=False)[:400])
    for f in d["forms"]:
        print("form:", json.dumps(f, ensure_ascii=False)[:700])
except Exception as e:
    print("raw:", str(v)[:1200])
