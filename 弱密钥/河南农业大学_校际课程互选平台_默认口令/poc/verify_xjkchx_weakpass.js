// 强智 kingo CAS 登录复刻（只读验证用）：node _kingo_login.js <username> <password> <schoolcode>
const fs = require('fs');
eval(fs.readFileSync('E:/kimi/scan/_kingo_base64.js', 'utf8'));
eval(fs.readFileSync('E:/kimi/scan/_kingo_md5.js', 'utf8'));
eval(fs.readFileSync('E:/kimi/scan/_kingo_jkingo.des.js', 'utf8'));

const BASE = 'https://xjkchx.ncwu.edu.cn';

async function main() {
  const [username, password, schoolcode] = process.argv.slice(2);
  // 1) 取会话 Cookie
  let cookie = '';
  const grab = (res) => {
    const sc = res.headers.getSetCookie ? res.headers.getSetCookie() : [];
    for (const c of sc) { const kv = c.split(';')[0]; if (!cookie.includes(kv.split('=')[0])) cookie += (cookie ? '; ' : '') + kv; }
  };
  const r0 = await fetch(BASE + '/cas/login.action', { headers: { 'User-Agent': 'Mozilla/5.0' } });
  grab(r0); await r0.text();

  // 2) 取 deskey/nowtime/ssessionid
  const r1 = await fetch(BASE + '/custom/js/SetKingoEncypt.jsp', { headers: { 'User-Agent': 'Mozilla/5.0', Cookie: cookie } });
  const encjs = await r1.text(); grab(r1);
  const _deskey = encjs.match(/_deskey = '([^']+)'/)[1];
  const _nowtime = encjs.match(/_nowtime = '([^']+)'/)[1];
  const _ssessionid = encjs.match(/_ssessionid = '([^']+)'/)[1];

  // 3) 构造参数（captcha 空 = 免验证码首次）
  const randnumber = '';
  const pwdHash = hex_md5(hex_md5(password) + hex_md5(randnumber.toLowerCase()));
  const userEnc = base64encode(utf16to8(username + ';;' + _ssessionid));
  const p_u = '_u' + randnumber, p_p = '_p' + randnumber;
  let params = `${p_u}=${userEnc}&${p_p}=${pwdHash}&randnumber=${randnumber}&isPasswordPolicy=false` +
    `&txt_mm_expression=&txt_mm_length=&txt_mm_userzh=&hid_flag=1&hidlag=1&hid_dxyzm=&sel_schname=${schoolcode}`;
  const token = hex_md5(hex_md5(params) + hex_md5(_nowtime));
  const encParams = base64encode(utf16to8(strEnc(params, _deskey, null, null)));
  const body = `params=${encodeURIComponent(encParams)}&token=${token}&timestamp=${encodeURIComponent(_nowtime)}&deskey=${_deskey}&ssessionid=${_ssessionid}`;

  const r2 = await fetch(BASE + '/cas/logon.action', {
    method: 'POST',
    headers: { 'User-Agent': 'Mozilla/5.0', Cookie: cookie, 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
    redirect: 'manual',
  });
  const resp = await r2.text();
  console.log('HTTP', r2.status);
  console.log(resp.slice(0, 500));
}
main().catch(e => { console.error('ERR', e.message); process.exit(1); });
