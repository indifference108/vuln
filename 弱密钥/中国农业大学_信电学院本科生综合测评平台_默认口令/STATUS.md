# 报送状态：材料已就绪，待报送

- 状态：**CNVD 报送材料已完成**（2026-10-13），复现视频已录制归档（evidence/05-漏洞复现视频.mp4，26.6MB）
- 定案事实：登录接口 `POST /api/v1/auth/login`，账号=学号、密码=学号后六位；144 个公示学号实测 8 个登录成功
- CVSS v3.1 9.1 Critical，CWE-521
- 受理号：**CNVD-C-2026-674160**（2026-10-13 提交，审核中）
- 归档编号：（归档后补填）
- 计划：同步通知学院（cieetw@cau.edu.cn，邮件已拟好见 submission/vendor-disclosure-email.md）
