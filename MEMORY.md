# 用户长期规则

## Git 版本控制规则(2026-08-14 用户确认)
- 用户仓库: `C:\Users\Administrator\WorkBuddy`,远端 `git@github.com:sim591701407/workbuddy_xm.git`(SSH,已切换,不依赖 GCM)
- **每次创建新的工作区/历史项目目录(如 `2026-XX-XX-XX-XX-XX`)时,必须主动提醒用户确认是否纳入 git 版本控制**,避免积累未跟踪的残留目录
- 用户偏好: 历史项目默认倾向删除而非推送;删除时优先回收站,回收站不可用时需先征得用户确认再永久删除
- 已知环境坑: Windows 下 Git Credential Manager 崩溃(段错误)→ 用 SSH 认证绕开;本机代理 127.0.0.1:7890;沙箱内外文件系统视图可能不一致,删除/检查前用 PowerShell Test-Path 或 Python 在沙箱外核实
- **致命坑(2026-09-07 确认): git 进程写入 `.git/refs/` 目录和部分 objects 会被后台进程静默吞噬**(config 与 projects 仓库都中招),手动 echo 写的 refs 和 packed-refs 文件能幸存。因此: ① 每次 fetch/push/commit 后必须核对 refs 是否真实落盘,丢失则手动 `mkdir -p .git/refs/remotes/origin && echo <sha> > .git/refs/remotes/origin/main`;② 日常同步不要依赖 Sync-WorkBuddy.ps1 wrapper(会卡死),直接手动 `git pull --rebase` + `git push`;③ 本机 wb-sync 命令位于 `~\.workbuddy\bin\wb-sync.cmd`(已入 PATH),但不可靠,慎用
