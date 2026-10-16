# 审计结论

- 弱口令 admin/Huawei@123 命中，登录成功，admin 主界面可达。
- 登录接口 /OPMUI/business/tsmLogin!login.action，hashcode 为一次性页面令牌。
- 失败计数基于会话（新会话即重置 data=1），验证码仅在连续失败后启用。
- 归属：四川省成都市（CHINANET 宽带动态拨号池，PTR broad.cd.sc.dynamic.163data.com.cn）
