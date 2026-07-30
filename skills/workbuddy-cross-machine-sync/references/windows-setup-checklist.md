# Windows 工作机接管清单（现场照做）

> 仓库：
> - 配置 `https://github.com/sim591701407/workbuddy_config.git` → `%USERPROFILE%\.workbuddy`
> - 项目 `https://github.com/sim591701407/workbuddy_xm.git`     → `%USERPROFILE%\WorkBuddy`

---

## 0. 前置检查（3 分钟）

打开 **PowerShell**（不需要管理员），逐条跑：

```powershell
git --version                    # 没有输出 -> 先装 Git for Windows
$env:USERPROFILE                 # 确认家目录，例如 C:\Users\xxx
Test-Path "$env:USERPROFILE\.workbuddy"   # 配置目录在不在
Test-Path "$env:USERPROFILE\WorkBuddy"    # 项目目录在不在
Get-Process WorkBuddy* -ErrorAction SilentlyContinue   # 有输出说明还在跑，必须先退出
```

- 没装 git：https://git-scm.com/download/win ，安装时全默认即可。
- **WorkBuddy 必须完全退出**（含托盘图标），否则它会一边写数据库一边被覆盖。
- 如果 `$env:USERPROFILE\WorkBuddy` 不存在，说明这台机器的项目目录不在默认位置。
  在 WorkBuddy 里看任意项目的路径，或者：
  ```powershell
  Get-ChildItem $env:USERPROFILE -Directory | Where-Object Name -like '*WorkBuddy*'
  ```

---

## 1. 打通认证（先做，否则后面每步都卡）

### 方案 A：SSH（推荐，不用带密钥过来）

```powershell
ssh-keygen -t ed25519 -C "591701407@qq.com"    # 一路回车
Get-Content "$env:USERPROFILE\.ssh\id_ed25519.pub" | Set-Clipboard
```
公钥已进剪贴板 → 浏览器打开 GitHub → Settings → SSH and GPG keys → New SSH key → 粘贴 → 保存。

验证：
```powershell
ssh -T git@github.com     # 出现 "Hi sim591701407! You've successfully authenticated" 即可
```

**公司网络若卡住不动**（22 端口常被封），改走 443：
```powershell
@"
Host github.com
  Hostname ssh.github.com
  Port 443
  User git
"@ | Out-File -Encoding ascii "$env:USERPROFILE\.ssh\config"
ssh -T git@github.com
```

用 SSH 的话，后面所有仓库地址换成：
- `git@github.com:sim591701407/workbuddy_config.git`
- `git@github.com:sim591701407/workbuddy_xm.git`

### 方案 B：PAT（HTTPS）

需要一个**同时覆盖两个仓库**的 fine-grained token（Repository access 勾 `workbuddy_config` + `workbuddy_xm`，Repositories 标签页里 Contents = Read and write）。
提示 Password 时粘贴 token，用户名是 `sim591701407`。

---

## 2. 接管两个目录

### 情况 A：目录不存在 —— 直接 clone

```powershell
cd $env:USERPROFILE
git clone https://github.com/sim591701407/workbuddy_config.git .workbuddy
git clone https://github.com/sim591701407/workbuddy_xm.git WorkBuddy
```

### 情况 B：目录已存在且有数据 —— 原地嫁接（不搬动本地文件）

思路：只把远端的 `.git` 元数据挪进来，再强制检出。强制检出**只覆盖远端存在的文件**，本地的 `binaries/`、`workbuddy.db`、日志一律不动。

```powershell
git config --global core.longpaths true

# ---- 配置仓库 ----
$p = "$env:USERPROFILE\.workbuddy"
Copy-Item $p "$p.backup" -Recurse -Force          # 保险起见先整份备份
$t = "$env:TEMP\wbcfg"
git clone --no-checkout https://github.com/sim591701407/workbuddy_config.git $t
Move-Item "$t\.git" "$p\.git" -Force
Remove-Item $t -Recurse -Force
cd $p
git config core.autocrlf false
git checkout -f main
git branch --set-upstream-to=origin/main main

# ---- 项目仓库 ----
$p = "$env:USERPROFILE\WorkBuddy"
$t = "$env:TEMP\wbxm"
git clone --no-checkout https://github.com/sim591701407/workbuddy_xm.git $t
Move-Item "$t\.git" "$p\.git" -Force
Remove-Item $t -Recurse -Force
cd $p
git config core.autocrlf false
git checkout -f main
git branch --set-upstream-to=origin/main main
```

> clone 完配置仓库后，`Setup-WorkBuddySync.ps1` 就在
> `%USERPROFILE%\.workbuddy\skills\workbuddy-cross-machine-sync\scripts\` 里了，
> 以后换机器可以直接跑它，不用手敲上面这段。

---

## 3. 验证

```powershell
cd "$env:USERPROFILE\.workbuddy"; git log --oneline -1; git ls-files | Measure-Object | % Count
Test-Path "$env:USERPROFILE\.workbuddy\skills\workbuddy-cross-machine-sync\SKILL.md"   # 应为 True
cd "$env:USERPROFILE\WorkBuddy";  git log --oneline -1
```

重新启动 WorkBuddy，随便开个会话问一句"我们之前搭过什么"，能答上来就说明记忆同步成功。

确认无误后删掉备份：
```powershell
Remove-Item "$env:USERPROFILE\.workbuddy.backup" -Recurse -Force
```

---

## 4. 日常同步（Windows）

```powershell
$s = "$env:USERPROFILE\.workbuddy\skills\workbuddy-cross-machine-sync\scripts\Sync-WorkBuddy.ps1"
& $s -Pull      # 开工前
& $s -Push      # 收工后
```

首次执行若报"禁止运行脚本"：
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

嫌路径长就加个函数到 profile：
```powershell
if (-not (Test-Path $PROFILE)) { New-Item -ItemType File -Path $PROFILE -Force }
Add-Content $PROFILE 'function wb-sync { & "$env:USERPROFILE\.workbuddy\skills\workbuddy-cross-machine-sync\scripts\Sync-WorkBuddy.ps1" @args }'
. $PROFILE
# 之后：wb-sync -Pull / wb-sync -Push
```

---

## 5. 铁律

- **切换机器前后各同步一次**：Mac 收工 `wb-sync push` → Windows 开工 `-Pull`；反之亦然。
- **两边不要同时开着 WorkBuddy 干活**，否则 memory 文件必冲突。
- `workbuddy.db` 永远不进仓库，两台机器各自独立（会话历史不通用，这是正常的）。
- 冲突多半发生在 `memory/*.md`：手工把两段内容都保留即可，不要 `--force`。
