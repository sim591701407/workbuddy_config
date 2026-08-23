# User Memory Profile
> Last updated: 2026-08-23T07:06:36+08:00
> Version: 7

## Memory Block

**工作背景**
用户从事心理学研究，负责实验设计与实施，目前主要推进心理学实验配套工具——quiz 答题系统的建设。系统目标用户 200-300 人，采用 PPT 式逐题展示、ID 登录、按题计时（进入即开始计时，提交记录停留时长，ECG 数据需毫秒精度对齐）的交互形态。整体规划包含三大部分：实验前端页面（study1/study2 入口）+ 数据管理 admin 后端 + 与 ECG 心电数据的集成，部署形态倾向公网部署（公网部署）以服务实验数据采集。围绕 2 项主研究展开，每项研究分为对照组与实验组，合计 6 个子研究共用同一套平台。ECG 数据分析流程已落地：250Hz 采样、17.8 min 时长数据，输出 HRV 指标与 HTML 报告。

**个人背景**
用户基于 macOS 终端工作，使用中文（简体）沟通，偏好代码块配合分步骤说明的输出形式。指令简短直接，任务导向；遇到问题时倾向于直接粘贴终端输出，期望助手基于根因给出排查结论。admin 后端的需求描述严格采用编号列表格式，强调具体 UI 行为变更（如取消条件分配、取消数据导出、采用毫秒精度等）。跨多设备协作：Mac 为主机，Windows 工作站（Huawei-MateBook）为副机，quiz 系统最初在 Windows 端启动开发，现需迁移至 Mac 继续推进。沙箱环境使用 PortableGit，通过本地代理 127.0.0.1:7890 访问 GitHub，认证方式已切换为 SSH（GitHub 用户 sim591701407，邮箱 591701407@qq.com，曾使用 fine-grained PAT + osxkeychain 走 HTTPS）。

**当前关注**
将原 Windows 端启动的 quiz 答题系统迁移至当前 Mac 环境中继续建设，重点搭建实验前端 + admin 数据管理后端，支撑 6 个子研究的实验数据采集，并与 ECG 心电数据毫秒级对齐。admin 后端需求以编号列表逐条提出具体 UI 行为改动。同步推进历史项目版本化管理与跨设备同步，正在整理 8 个未纳入版本控制的历史项目目录。

**近期动态**
- 启动 quiz/答题系统搭建：面向 200-300 用户，PPT 式逐题、ID 登录、按题计时（进入开始计时、提交记录停留时长，毫秒精度），将部署 2 项心理学主研究各含对照/实验组的 6 个子研究。
- 规划 quiz 系统架构：实验前端页面（study1/study2） + admin 数据管理后台 + ECG 心电数据集成，整体走公网部署（公网）形态。
- 将 quiz 系统从 Windows（华为 MateBook）端开发环境迁移至 Mac 继续推进。
- 将 GitHub 认证从 HTTPS+PAT（osxkeychain 存储 fine-grained PAT）切换为 SSH（ed25519 密钥），解决 push 失败与 token 过期问题。
- 维护跨 Mac/Windows 的 WorkBuddy 同步方案：workbuddy_config（~/.workbuddy，存放 memory/skills/identity）与 workbuddy_xm（~/WorkBuddy，存放 projects）两个 git 仓库，通过 wb-sync shell 别名一站式完成 pull+commit+push。
- 完成 ECG 心电数据分析（250Hz、17.8 min），输出 HRV 指标与 HTML 报告。
- 整理 8 个尚未纳入版本控制的历史项目目录，准备纳入 Git 管理。

---

<!-- RAW_JSON_START
{
  "uid": "11f4bd18-01cd-4b3a-bb0b-04c7bd68c342",
  "memoryBlock": "**工作背景**\n用户从事心理学研究，负责实验设计与实施，目前主要推进心理学实验配套工具——quiz 答题系统的建设。系统目标用户 200-300 人，采用 PPT 式逐题展示、ID 登录、按题计时（进入即开始计时，提交记录停留时长，ECG 数据需毫秒精度对齐）的交互形态。整体规划包含三大部分：实验前端页面（study1/study2 入口）+ 数据管理 admin 后端 + 与 ECG 心电数据的集成，部署形态倾向公网部署（公网部署）以服务实验数据采集。围绕 2 项主研究展开，每项研究分为对照组与实验组，合计 6 个子研究共用同一套平台。ECG 数据分析流程已落地：250Hz 采样、17.8 min 时长数据，输出 HRV 指标与 HTML 报告。\n\n**个人背景**\n用户基于 macOS 终端工作，使用中文（简体）沟通，偏好代码块配合分步骤说明的输出形式。指令简短直接，任务导向；遇到问题时倾向于直接粘贴终端输出，期望助手基于根因给出排查结论。admin 后端的需求描述严格采用编号列表格式，强调具体 UI 行为变更（如取消条件分配、取消数据导出、采用毫秒精度等）。跨多设备协作：Mac 为主机，Windows 工作站（Huawei-MateBook）为副机，quiz 系统最初在 Windows 端启动开发，现需迁移至 Mac 继续推进。沙箱环境使用 PortableGit，通过本地代理 127.0.0.1:7890 访问 GitHub，认证方式已切换为 SSH（GitHub 用户 sim591701407，邮箱 591701407@qq.com，曾使用 fine-grained PAT + osxkeychain 走 HTTPS）。\n\n**当前关注**\n将原 Windows 端启动的 quiz 答题系统迁移至当前 Mac 环境中继续建设，重点搭建实验前端 + admin 数据管理后端，支撑 6 个子研究的实验数据采集，并与 ECG 心电数据毫秒级对齐。admin 后端需求以编号列表逐条提出具体 UI 行为改动。同步推进历史项目版本化管理与跨设备同步，正在整理 8 个未纳入版本控制的历史项目目录。\n\n**近期动态**\n- 启动 quiz/答题系统搭建：面向 200-300 用户，PPT 式逐题、ID 登录、按题计时（进入开始计时、提交记录停留时长，毫秒精度），将部署 2 项心理学主研究各含对照/实验组的 6 个子研究。\n- 规划 quiz 系统架构：实验前端页面（study1/study2） + admin 数据管理后台 + ECG 心电数据集成，整体走公网部署（公网）形态。\n- 将 quiz 系统从 Windows（华为 MateBook）端开发环境迁移至 Mac 继续推进。\n- 将 GitHub 认证从 HTTPS+PAT（osxkeychain 存储 fine-grained PAT）切换为 SSH（ed25519 密钥），解决 push 失败与 token 过期问题。\n- 维护跨 Mac/Windows 的 WorkBuddy 同步方案：workbuddy_config（~/.workbuddy，存放 memory/skills/identity）与 workbuddy_xm（~/WorkBuddy，存放 projects）两个 git 仓库，通过 wb-sync shell 别名一站式完成 pull+commit+push。\n- 完成 ECG 心电数据分析（250Hz、17.8 min），输出 HRV 指标与 HTML 报告。\n- 整理 8 个尚未纳入版本控制的历史项目目录，准备纳入 Git 管理。",
  "version": 7,
  "updatedAt": "2026-08-23T07:06:36+08:00"
}
RAW_JSON_END -->
