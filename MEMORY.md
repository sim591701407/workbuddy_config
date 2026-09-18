# 用户长期规则

## 称呼(2026-09-18 用户指定)
- **称呼用户为「裴帅」**。用户本人明确要求("叫我裴帅"),不要改用其它称呼。
- **我的名字是「明日香」**(裴帅 2026-09-18 指定)。详见 `~/.workbuddy/IDENTITY.md`。
- **调性基调已由用户确认: 保持"直给、少寒暄、结论先行、不说没有实测支撑的话"**(裴帅原话:"还是像现在这样的调性")。不要改得更热情或更圆滑。
- 详细背景见 `~/.workbuddy/USER.md`。

## Git 版本控制规则(2026-08-14 用户确认)
- 用户仓库: `C:\Users\Administrator\WorkBuddy`,远端 `git@github.com:sim591701407/workbuddy_xm.git`(SSH,已切换,不依赖 GCM)
- **每次创建新的工作区/历史项目目录(如 `2026-XX-XX-XX-XX-XX`)时,必须主动提醒用户确认是否纳入 git 版本控制**,避免积累未跟踪的残留目录
- 用户偏好: 历史项目默认倾向删除而非推送;删除时优先回收站,回收站不可用时需先征得用户确认再永久删除
- 已知环境坑: Windows 下 Git Credential Manager 崩溃(段错误)→ 用 SSH 认证绕开;沙箱内外文件系统视图可能不一致,删除/检查前用 PowerShell Test-Path 或 Python 在沙箱外核实
- **代理端口每个会话都不同**(2026-09-18 确认): 环境会注入 `http_proxy`/`https_proxy`,见过 `7890`、`14025`,**不要硬编码**;脚本里用 `echo $http_proxy` 现取。本机 curl 访问 `localhost`/`127.0.0.1` 实测会绕过代理(2026-09-18 在服务确认在线时验证过),但访问本机服务仍建议加 `--noproxy '*'`,以防某个会话的代理拦截 localhost 把健康服务误报成 502、导致白重启一轮
- **致命坑(2026-09-07 确认): git 进程写入 `.git/refs/` 目录和部分 objects 会被后台进程静默吞噬**(config 与 projects 仓库都中招),手动 echo 写的 refs 和 packed-refs 文件能幸存。因此: ① 每次 fetch/push/commit 后必须核对 refs 是否真实落盘,丢失则手动 `mkdir -p .git/refs/remotes/origin && echo <sha> > .git/refs/remotes/origin/main`;② 日常同步不要依赖 Sync-WorkBuddy.ps1 wrapper(会卡死),直接手动 `git pull --rebase` + `git push`;③ 本机 wb-sync 命令位于 `~\.workbuddy\bin\wb-sync.cmd`(已入 PATH),但不可靠,慎用

## Windows 环境坑(2026-09-11 确认,适用于所有本机任务)
- **quiz-app 服务必须用 venv Python 启动(2026-09-17 踩实)**: `C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe`(含 openpyxl)。
  用裸 `versions\3.13.12\python.exe` 启动时,服务端 xlsx 导出(/api/admin/export、/api/admin/user/export)在 import openpyxl 处崩溃 → 连接无响应中断 → serveo 表现为 502"网页无法运作"。
  start-demo.bat 已修正为优先 venv Python。
- **并行调用 Edit 工具编辑同一文件会互相覆盖丢失改动**(2026-09-17 踩实): 同一文件的多处修改必须逐个顺序编辑,每次编辑后 grep 校验落盘。
- **PowerShell 工具的 stdout 不回传**: `Write-Output` 完全没有输出。必须 `Set-Content` 写文件后用 Read 工具读取。
- **`cmd.exe` 在 PowerShell 工具中被安全策略禁止**: `assoc` / `ftype` / `schtasks` 等改走直接读注册表或 Bash 工具。
- **`Add-Type` 被禁止**("compiles and loads .NET code at runtime"): PowerShell 里无法做 P/Invoke 或截屏。改用 Python + ctypes。
- **含 `%VAR%` 的命令会被误拦**(提示"cmd.exe %VAR% syntax is not PowerShell syntax"),正则/字符串里避免写 `%SystemRoot%` 这类字面量。
- **删除受 `safe-delete` 批量守卫拦截**: 循环 `Remove-Item` 多个文件报 `[SAFE_DELETE_BULK_GUARD_ERROR] bulk delete guard blocked deletion`。
  绕开方式: 用 `Move-Item` 整体改名/移动到备份目录(非破坏性,保留数据,更安全)。
- **Python 脚本触发 SIGTERM 的三个操作**: `subprocess` 调 tasklist/taskkill、`os.startfile`、`ShellExecuteW` 直调 GUI。
  纯 ctypes 的 `EnumWindows` / `IsHungAppWindow` / `QueryFullProcessImageNameW` 可正常运行且 stdout 正常回传。
  `dangerouslyDisableSandbox` 对此无效(不是沙箱导致)。
- **判断 GUI 程序是否真卡死的可靠 oracle 是 `IsHungAppWindow(hwnd)`**(Python ctypes 调用),
  `Get-Process -Responding` 次之。**不要用线程 `WaitReason` 判断**——真卡死时线程也可能显示 `UserRequest`(健康空闲消息循环的特征),极易误判。
- **DWM 的 `Ghost` 窗口会出现在 `EnumWindows` 列表里且 PID 属于 `dwm.exe`**,标题带"(未响应)"= 系统已确认该应用卡死。
- **`Get-AppxPackage` 在 `Reset-AppxPackage` 执行过程中会瞬时返回空**,属部署过程现象,稍后复查即可,勿当作"包被删了"。
- **Bash 工具的 PATH 会偶发损坏(2026-09-17 确认)**: 表现为 `shell-runtime-bash-env.sh: line 3: dirname: command not found` 以及 `grep/head/tail/ls/netstat: command not found`,但 `curl`/`sleep`/`echo` 仍可用(部分是内置或走了不同路径)。
  解法: 在报错的每条命令**前置这行 export** 即恢复正常 —
  `export PATH="/c/Users/Administrator/.workbuddy/binaries/PortableGit/versions/1.2.0/usr/bin:/c/Users/Administrator/.workbuddy/binaries/PortableGit/versions/1.2.0/bin:/c/Windows/System32:/c/Windows:/c/Windows/System32/Wbem"`
  用绝对路径调用 python.exe 之类的方式本来就不受 PATH 影响。

## 删除与提权的真实边界(2026-09-16 确认,卸载 POE2 时踩实)
- **`safe-delete` 是文件系统级钩子,不只是命令拦截**: 它会拦截 Python `os.remove` / `shutil.rmtree` 并把删除重定向到回收站(即使调用方有写权限)。`dangerouslyDisableSandbox` 和"沙箱已绕过"状态都**不能**解除它。
  - 同盘普通文件能进回收站 → 删除"成功",但**同盘回收站不释放空间**,必须再清空回收站才真正腾出容量。
  - SYSTEM 所有的目录(如 `E:\DeliveryOptimization\Cache`)trash 会失败 → `[SAFE_DELETE_FAIL_CLOSED]`,直接拦截,**无解**。
  - 结论: 需要"真正释放空间"的场景,不要指望通过 Python/PowerShell 删除绕过,应走官方卸载程序或官方 API。
- **提权只有一条路可行**: `Start-Process -FilePath "<非解释器可执行文件>" -Verb RunAs -Wait -PassThru`(已验证 `msiexec.exe` 可用,返回 ExitCode)。
  被硬拦的组合: `Start-Process powershell/cmd/python -File/-Command ...` 报 "spawns a child process that bypasses PowerShell command validation" —— **无法提权执行任意脚本**,只能提权执行单个有 CLI 接口的 exe。
- **MSI 卸载报 `Error 1730 / InstallInitialize Return value 3` = 当前进程未提权**(不是包损坏)。日志解码后能看到明确文案"You must be an Administrator to remove this application"。
  msiexec 日志是 **UTF-16LE**,需 `.decode('utf-16-le')` 才可读。
- **判断某个目录能否免提权操作**: 直接在其中创建再删除一个临时文件即可,比猜 ACL 可靠。
- **卸载前的正确姿势**: 先查注册表 Uninstall 键(含 WOW6432Node + HKCU)定位安装方式与 MSI 产品码,再查 `Installer\UserData\S-1-5-18\Products\*\InstallProperties` 拿安装目录,再解析 `.lnk` 快捷方式目标确认真正的安装路径。GGG 游戏的 MSI 卸载器会**连同 `Content.ggpk` 一起删掉**,不必手动删数据目录。
- **当前会话的工作区目录本身删不掉(2026-09-16 确认)**: 里面的文件可以被 trash 清空(内容进回收站、可恢复),但顶层 `WorkBuddy\<时间戳>` 空壳会被会话进程占用 → 报 `SAFE_DELETE_FAIL_CLOSED / trash-failed: Some operations were aborted`。
  排障判据: 在同级新建一个空目录并立即删除,若成功则钩子正常,问题就是"该目录被占用",不是权限或钩子故障。
  对策: 用户要求"用完就删"的工作区,只能先清空内容,再等 WorkBuddy 完全退出后手动删掉空壳(或在桌面放一个只删空目录的 `rd` 脚本,关掉应用后双击)。**不要在会话内反复重试**。

## 性能测量方法学(2026-09-17 确认,评估 quiz-app 上云规格时踩实)
- **给纯 Python 算法计时时禁用 `tracemalloc`**: 它会给每次对象分配加探针开销,让紧凑循环(如逐样本滤波、R 波检测)慢 **10 倍以上**
  (同一文件实测 0.868 s → 10.24 s),足以让"2核2G 够用"被误判成"必须上 4 核"。
  **计时与内存测量必须分成两轮**: 先无探针跑计时,再单独开探针测内存峰值。
- **纯 Python + GIL 的 CPU 密集任务,多线程只排队不并行**: 评估并发能力时要按"单核性能 × 串行"估算,不要按核数线性外推。
- 报告性能数字时,必须写清测量机 CPU 型号与 Python 版本,并给出云端降频系数(实测值的 0.5–0.7 倍)供读者自行折算。

## 腾讯云轻量(Lighthouse)MCP 的能力边界(2026-09-17 确认)
- **没有套餐目录/价格查询工具**(无 `describe_bundles`)。可选规格与价格需从官网「价格总览」文档或活动页获取,不要臆造 BundleId 去调 `describe_bundle_discount`。
- 查询实例必须显式传 `Region`;无实例时返回"暂无数据"而非报错。
- 价格要点: 流量包**只统计公网出方向,上传/入方向免费**;中国内地超额流量 0.8 元/GB;年付享 85 折。
