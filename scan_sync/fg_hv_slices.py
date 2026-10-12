# -*- coding: utf-8 -*-
"""FastGPT 40351 高价值切片收割（gov/edu/医院），增量合并"""
import json, subprocess, time, base64, os

DAEMON = 'http://127.0.0.1:10086/command'
SESSION = 'fofa-mining'
os.chdir(r'E:\kimi\scan')

def wb(action, args):
    body = json.dumps({'action': action, 'args': args, 'session': SESSION})
    fn = f'_wb_{int(time.time()*1000)%1000000}.json'
    open(fn, 'w', encoding='utf-8').write(body)
    try:
        out = subprocess.run(['curl.exe', '-s', '-X', 'POST', DAEMON, '--data-binary', f'@{fn}'],
                             capture_output=True, text=True, timeout=60,
                             encoding='utf-8', errors='replace').stdout
    finally:
        os.remove(fn)
    return json.loads(out)

def grab(query, tag):
    b64 = base64.b64encode(query.encode()).decode()
    wb('navigate', {'url': f'https://en.fofa.info/result?qbase64={b64}', 'newTab': False})
    key, hosts = None, []
    for _ in range(4):
        time.sleep(5)
        r = wb('evaluate', {'code': (
            "var hs=[].slice.call(document.querySelectorAll('a[href]')).map(function(a){return a.href})"
            ".filter(function(h){return h.indexOf('fofa.info')<0 && h.indexOf('http')===0});"
            "var u=[]; hs.forEach(function(h){if(u.indexOf(h)<0)u.push(h)});"
            "JSON.stringify({hosts:u})")})
        if not r.get('ok'):
            continue
        v = json.loads(r['data']['value'])
        if v['hosts'] and v['hosts'] != key:
            key, hosts = v['hosts'], v['hosts']
            break
    print(f'[{tag}] {len(hosts)} hosts', flush=True)
    return hosts

BASE = 'body="tryfastgpt.ai"'
QUERIES = [
    (BASE + ' && (domain="gov.cn")', 'gov'),
    (BASE + ' && (domain="edu.cn")', 'edu'),
    (BASE + ' && (body="医院" || body="人民医院" || body="卫生院")', 'hospital'),
    (BASE + ' && (body="大学" || body="学院")', 'univ_body'),
    (BASE + ' && port="9001"', 'p9001'),
    (BASE + ' && port="3002"', 'p3002'),
]

pool_file = r'fofa_pool\fg_slices_hv_20261012.json'
pool = json.load(open(pool_file, encoding='utf-8')) if os.path.exists(pool_file) else {}
for q, tag in QUERIES:
    if tag in pool:
        print(f'[{tag}] skip (done)', flush=True)
        continue
    try:
        pool[tag] = grab(q, tag)
        json.dump(pool, open(pool_file, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    except Exception as e:
        print(f'[{tag}] ERROR {e}', flush=True)
        break

all_hosts = []
for v in pool.values():
    for h in v:
        if h not in all_hosts:
            all_hosts.append(h)
print('TOTAL unique:', len(all_hosts))
json.dump(all_hosts, open(r'fofa_pool\fg_hv_hosts_20261012.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
