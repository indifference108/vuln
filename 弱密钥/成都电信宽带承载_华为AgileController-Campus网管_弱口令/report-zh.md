# 华为 Agile Controller-Campus 网管平台弱口令漏洞（admin / Huawei@123）

## 概述
- 目标：https://221.237.179.20:8443
- 系统：华为 Agile Controller-Campus（SecoSpace / OPMUI），网络准入控制（NAC）统一网管
- 漏洞类型：弱口令（出厂默认口令未修改）
- 口令：admin / Huawei@123
- IP 归属：四川省成都市（CHINANET 宽带动态拨号池，PTR broad.cd.sc.dynamic.163data.com.cn）
- 验证时间：2026-10-16
- 状态：登记不报送（归属不明）

## 复现步骤
1. GET /OPMUI/login.html 获取登录页及隐藏字段 hashcode（每次页面加载随机生成，随表单提交）。
2. POST /OPMUI/business/tsmLogin!login.action，表单字段 userName=admin、password=Huawei@123、hashcode=<页面值>、validCode 留空（验证码区域默认隐藏，连续失败 3 次才触发）。
3. 服务端返回 {"data":"<32位会话令牌>","message":null,"success":true} 即登录成功；
   口令错误时返回 {"data":1,"message":"用户名或密码错误，或者用户被锁定"}。
4. 携带 XSRF-TOKEN cookie 访问 /OPMUI/jsp/secospace/index.jsp，返回完整网管主界面
   （含 系统管理 / 用户管理 / 角色管理 / 认证授权 / 接入设备 / 告警管理 等菜单），确认 admin 身份。

## 危害说明（目标视角）
该平台为网络准入控制核心网元，攻击者以 admin 登录后可：
- 查看/管理全网接入设备、用户账号与角色、认证授权策略（read 已证实菜单可达）；
- 修改准入策略、下发网络接入策略、管理账号黑名单，可导致全网终端被断网或非法放行；
- 在线用户管理、终端登录日志等模块暴露在内网拓扑与用户信息。
公网可达 + 默认口令 = 网络边界设备完全失守，等价于该单位内网准入体系被绕过的起点。

## 证据
- evidence/login_page.html：登录页（title=Agile Controller Login，含 hashcode 字段）
- evidence/index_page.html：登录后主界面（admin 身份，系统管理菜单）
- evidence/login_response.json：登录成功响应原文
- poc/verify_agile_weakpwd.py：只读复现脚本

## 归属说明
PTR 明确为电信成都宽带动态池，属客户自建设备而非中国电信系统资产，同 7.24 山西联通先例：只登记不报送。

## 纪律声明
全程只读验证：仅执行登录与主页面 GET，未查询、导出、修改任何业务数据，未做任何配置变更。
