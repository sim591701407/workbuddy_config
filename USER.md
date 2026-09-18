---
summary: "User profile record"
read_when:
  - Bootstrapping a workspace manually
---

# USER.md - About Your Human

- **Name:** 裴帅
- **What to call them:** 裴帅（用户本人指定，2026-09-18）
- **Pronouns:** _(未提供)_
- **City:** 待确认（设备与网络环境：Windows 工作站 + macOS 主机，两台机器双线作业）
- **Notes:**
  - 心理学研究者，负责实验设计与实施；同时参与实验配套系统的开发与部署
  - 母语中文（简体）；技术沟通习惯：**结论先行 + 代码块 + 分步说明**，需求常用编号列表逐条提出
  - 遇到问题倾向直接粘贴终端输出，期望拿到**基于根因**的结论，而不是泛泛的排查建议
  - 强调**结论必须严格基于实测数据**，不接受主观调整或"看起来应该没问题"
  - 偏好文档与代码成体系地维护（README、接口一览、更新记录）

## Context

**主线项目：心理学实验平台（quiz-app）+ 心电分析（ECG）**

- 实验平台：面向 200–300 人，PPT 式逐题展示、ID 登录、按题计时（进入即计时，提交记录停留时长，
  需毫秒精度）；覆盖 2 项主研究 × 对照/实验组 = 6 个子研究，共用同一套平台
- 组成：实验前端（study1 / study2）+ 数据管理后端（admin）+ ECG 数据集成
- 部署形态：公网采集数据。quiz-app 走 serveo 隧道固定在
  `https://psyquiz2.serveousercontent.com`（本地 8765）；独立心电工具本地 8766
- **ECG 分析链路**（SensEcho 5A，24bit @ 250Hz）：
  中值滤波去基线 → 20ms 平滑 → Pan-Tompkins R 波检测 → RR 伪差编辑 → 时域/频域 HRV
  → 输出 HRV 指标与 HTML 报告
- **当前研究焦点**：以设备厂商返回的 HRV 结果为基准验证自有算法可靠性，量化偏差后再分阶段决策。
  已知厂商/自研频域差异主要来自 RR 重采样插值方式（线性 → 自然三次样条后 HF 低估从 −23.5% 收敛到 −1.0%）

**两个 ECG 相关项目的关系（2026-09-09 用户明确）**

- `ecg-analysis-app`（独立免安装工具，将单独交给另一个博士生研究组）与 `quiz-app` 的心电模块
  是**两个完全独立的项目**，仅共用同一套 ECG 分析算法
- 独立工具必须**完全离线自用**；`sync_engine.py` 以独立工具为基准保持两边引擎逐字节一致

**版本控制约定**

- 仓库：`C:\Users\Administrator\WorkBuddy` → `git@github.com:sim591701407/workbuddy_xm.git`（SSH）
- 用户配置 / 记忆 / 技能：`~/.workbuddy` → `workbuddy_config` 仓库
- **每次新建工作区目录（`2026-XX-XX-XX-XX-XX`）都要主动问是否纳入版本控制**
- 只提交代码与文档，**不提交数据**（原始心电文件、数据库、令牌等）
- 历史项目默认倾向删除而非推送；删除优先走回收站，需永久删除时先征得确认

**协作风格偏好**

- 长任务、多步骤时希望有清晰的进度与可复用的沉淀（脚本参数化、skill、README）
- 对"服务被环境回收"这类反复出现的问题，期望给出长期稳定方案而非每次手工重启

---

The more you know, the better you can help. But remember - you're learning about a person, not building a dossier. Respect the difference.
