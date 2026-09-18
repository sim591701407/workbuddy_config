---
name: quiz-ecg-service-restore
description: Restore the psychology-experiment quiz platform (quiz-app, port 8765) and the standalone ECG analysis tool (ecg-analysis-app, port 8766) plus the serveo public tunnel (psyquiz2.serveousercontent.com) after the session-brokered background processes were reclaimed. Use when the user says "恢复公网访问", "启动心电项目", "服务挂了", "public 502", or asks to bring the deployed quiz/ECG services back online on this Windows machine.
agent_created: true
---

# 恢复 quiz-app + ECG 工具 + serveo 公网隧道

## Purpose
All three processes are hosted as session background tasks and are reclaimed when the session ends or the environment recycles them. "恢复公网访问" therefore always means a **full three-service restart**, never just a tunnel reconnect.

## When to use
- User says 「恢复公网访问」/「启动心电项目」/「服务挂了」/「急用」
- Any endpoint returns 502 and no LISTEN socket exists on 8765/8766
- `tunnel_watchdog.log` shows `no URL captured` or no entries for days

## Fixed paths (verify they still exist)
| Item | Path |
|---|---|
| quiz-app (答题系统 + 心电后台) | `C:\Users\Administrator\WorkBuddy\2026-08-22-12-04-24\quiz-app` |
| ecg-analysis-app (独立心电工具) | `C:\Users\Administrator\WorkBuddy\ecg-analysis-app` |
| **venv Python (quiz-app server 必须用这个)** | `C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe` |
| bare Python (仅用于 ecg-analysis-app / watchdog / 脚本) | `C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe` |
| Tunnel key | `C:/Users/Administrator/.wb_tunnel_key/id_ed25519` |
| Watchdog log | `<quiz-app>\data\tunnel_watchdog.log` |
| Public URL | https://psyquiz2.serveousercontent.com |

## Procedure

### Step 1 — Diagnose
```bash
curl -s --noproxy '*' -o /dev/null -w "quiz:%{http_code}\n" --max-time 4 http://localhost:8765/
curl -s --noproxy '*' -o /dev/null -w "ecg:%{http_code}\n"  --max-time 4 http://localhost:8766/api/health
curl -s -o /dev/null -w "pub:%{http_code}\n"  --max-time 15 https://psyquiz2.serveousercontent.com/admin
```
- `302` on 8765 root and `200` on 8766 health = healthy (do NOT mistake 302 for failure).
- `502` + no LISTEN socket + no `python`/`ssh` processes = everything was reclaimed → full restart.

### Step 1.5 — 先分流，别条件反射全量重启
| 本地 8765/8766 | 公网 | 结论 | 动作 |
|---|---|---|---|
| 正常（302/200） | 502 | **只是隧道挂了** | 走「隧道限流恢复」：停看门狗 → `taskkill ssh` → **前台静置 ~6 分钟** → 重启看门狗。**不要动本地服务** |
| 也挂了 / 无 LISTEN | 502 | 服务被回收 | 走 Step 2 全量重启 |

2026-09-18 21:21 实测：本地两个服务一直健康，只有 serveo 隧道自然掉线（当天 20:08 建立，约 72 分钟后失效）。
**隧道自然掉线后立即重连同样会被拒**，必须静置，不能靠看门狗自己重试（它每 60s 试一次，反而加剧限流）。

停看门狗的正确姿势（**按命令行匹配，绝不按 PID 猜**，理由见 pitfall 6；`taskkill` 在本机不生效，用 PowerShell）：
```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -like "*tunnel_watchdog.py*" } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Get-Process ssh -ErrorAction SilentlyContinue | Stop-Process -Force   # 清隧道残留
```
然后**前台**静置 6 分钟（分两步，别写成 `sleep; cmd`，见 pitfall 8），再单独启动看门狗。

**Reliable process check on this box — PowerShell stdout does NOT return.** Write to a file and Read it:
```powershell
$out = @(); $out += "listen8765=" + (Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue).Count
$out += "pythonProcs=" + @(Get-Process python -ErrorAction SilentlyContinue).Count
$out += "sshProcs=" + @(Get-Process ssh -ErrorAction SilentlyContinue).Count
$out | Set-Content -Path "<tmp>\_stat.txt" -Encoding UTF8
```

### Step 2 — Clear leftovers, then start all three (order matters)
清残留（`taskkill //IM` 在本机 Git Bash 不生效，见 pitfall 7）：
```powershell
Get-Process ssh -ErrorAction SilentlyContinue | Stop-Process -Force
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -like "*tunnel_watchdog.py*" } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```
> 若两个 server 也要重起：**连同其父进程（venv 转发器）一起停**，否则残留的转发器会留下一个空壳（见 pitfall 6）。
Then launch each in the background (`run_in_background: true`), **one command each**:
1. `cd <quiz-app> && <venv-python> server.py`        → 8765  **必须用 venv Python（envs\default\Scripts），裸 Python 没有 openpyxl，所有服务端 xlsx 导出（/api/admin/export、/api/admin/user/export）会崩掉连接 → 公网表现为 502"网页无法运作"（2026-09-17 踩实，这正是"点下载提示网页无法连接"的根因）**
2. `cd <ecg-analysis-app> && <python> server.py`     → 8766
3. `cd <quiz-app> && <python> tunnel_watchdog.py`    → tunnel

### Step 3 — Verify
```bash
sleep 4
curl -s --noproxy '*' -o /dev/null -w "quiz:%{http_code}\n" --max-time 6 http://localhost:8765/
curl -s --noproxy '*' -o /dev/null -w "ecg:%{http_code}\n"  --max-time 6 http://localhost:8766/api/health
sleep 14
tail -4 "<quiz-app>\data\tunnel_watchdog.log"
for p in study1 study2 admin; do
  echo "$p -> $(curl -s -o /dev/null -w '%{http_code}' --max-time 15 https://psyquiz2.serveousercontent.com/$p)"
done
```
Success = watchdog logs `public URL: https://psyquiz2.serveousercontent.com` and all three entries return 200.
**Excel 导出验证**（openpyxl 崩溃不复现才算恢复完整）：
```bash
curl -s -o /tmp/e.xlsx -w "export:%{http_code} %{size_download}\n" --max-time 30 \
  "http://localhost:8765/api/admin/export?key=<adminKey见config.json>&study=1"
# 期望 200 + size>1000；403=key 错；500/连接中断=openpyxl 缺失（用错了解释器）
```

## Pitfalls

**1. Broken bash PATH — check first.** In some sessions coreutils vanish and you get
`shell-runtime-bash-env.sh: line 3: dirname: command not found` plus `grep/head/tail: command not found`.
**Fix: prepend this export to EVERY bash call that needs a tool:**
```bash
export PATH="/c/Users/Administrator/.workbuddy/binaries/PortableGit/versions/1.2.0/usr/bin:/c/Users/Administrator/.workbuddy/binaries/PortableGit/versions/1.2.0/bin:/c/Windows/System32:/c/Windows:/c/Windows/System32/Wbem"
```
`curl`, `sleep`, `tail`, `for` loops all work once PATH is restored. Launching python via its absolute path also works without PATH.

**2. serveo binding freeze (502 after a restart / 隧道自然掉线).** Restarting the quiz server makes the watchdog reconnect instantly; repeated reclaims of the same subdomain get throttled and **even random subdomains are refused**. Recovery: stop the watchdog, 清掉 ssh 残留（PowerShell `Stop-Process`，**不要**用 `taskkill //IM`，见 pitfall 7）, wait ~6 minutes, then restart the watchdog — it recaptures `psyquiz2` on the first try.
**However:** if the services have been down for hours or days, the binding has already lapsed — skip the wait and start the watchdog directly (observed 2026-09-10, 09-16, 09-17: connects within ~5s every time). **反之，隧道是"刚刚掉线"的（之前一直在服务中），6 分钟静置是必须的 —— 2026-09-18 21:21 掉线后立即重连连续 6 次全部 `no URL captured`，静置到 21:31:57 重启后一次成功。**

**3. The tunnel only fronts quiz-app (8765).** ecg-analysis-app (8766) is local-only by design; `start.sh`/`start.bat` are provided if the user wants it standalone.

**4. 本机 curl 一律加 `--noproxy '*'`（防御性）。** 本环境注入了 `http_proxy` / `https_proxy`
（端口**每个会话都可能不同**，见过 `7890`、`14025`，**不要硬编码**）。2026-09-18 实测当前 curl
对 `localhost` / `127.0.0.1` 会绕过代理，所以不加也不会误报；但一旦某个会话的代理拦截了 localhost，
**健康的服务会显示 502**，会被误判成"服务挂了"而白重启一轮。加 `--noproxy '*'` 零成本。

**5. Do not rely on these lasting.** All three live in session background tasks. Tell the user once more that
`quiz-app\start-demo.bat` (quiz + watchdog) and `ecg-analysis-app\start.bat` launch them in independent
windows, which survive session teardown.

**6. ⚠️ Windows venv 的 `Scripts\python.exe` 是转发器，会起两层同名进程 —— 千万别把父进程当"空转冗余"杀掉。**
实测：`envs\default\Scripts\python.exe server.py` 会出现**两个完全同名**的进程，父进程是 venv 转发器、
真正的解释器是它的**子进程**（子进程才是持有 LISTEN socket 的那个）。
转发器几乎不吃 CPU（实测 80 分钟仅 0.1s、单线程），极易被误判成"挂死的冗余进程"。
**2026-09-18 21:25 就是踩了这个坑**：把 8765 的父进程当冗余杀掉 → 子进程（真服务）随之退出 → 服务中断，
只能重连看门狗前重新拉起 server。**裸 `versions\3.13.12\python.exe`（8766 用）没有转发器，只有一个进程。**
> 判断"是不是服务本身"不要看进程名和 CPU，要看 **`Get-NetTCPConnection -LocalPort 8765 -State Listen` 的 OwningProcess**，
> 且**先看父子关系**（`ParentProcessId`）再决定动不动手。

**7. `taskkill //PID` / `//IM` 在本机 Git Bash 里不生效。** 报 `错误: 无效参数/选项 - '//PID'`。
（历史上 `taskkill //IM ssh.exe //F 2>/dev/null` 看起来"成功"其实是被 `2>/dev/null` 掩盖的失败。）
**换 PowerShell**：`Stop-Process -Id <pid> -Force` / `Get-Process ssh | Stop-Process -Force`。
且 PowerShell 的 stdout 不回传 —— 把结果 `Set-Content` 到文件再用 Read 读。

**8. 后台任务里写 `sleep N; cd ... && python ...` 会被跳过 sleep。** 实测 `sleep 370; ...` 只隔了约 10 秒就执行了后面的命令。
要"延时启动"，**分两步**：先在前台跑 `sleep 300`（记得带显式 `timeout`，如 330000，且 `sleep` 不会被自动转后台），
再单独把目标命令作为后台任务启动。另：PATH 退化时 `sleep`/`date` 也会 `command not found`，照样要前置 export。

## After restoring
Append a line to the workspace daily log `C:\Users\Administrator\WorkBuddy\2026-08-14-11-06-52\.workbuddy\memory\YYYY-MM-DD.md` recording: services restarted, task ids, tunnel capture timestamp, and verification result. Always offer the `start-*.bat` alternative.

## 反向操作：关闭公网访问
用户会说「关闭公网访问」（实验结束/下班/不想再对外暴露）。**默认只关隧道，保留本地两个服务**——
保留后本机 `http://127.0.0.1:8765` 仍可用，且随时能再开；如果用户其实想全停，他会说「停掉服务/关掉系统」。

```powershell
# 1) 只停看门狗：按命令行匹配，绝不要按 PID 猜（见 pitfall 6）
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -like "*tunnel_watchdog.py*" } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
# 2) 停隧道进程
Get-Process ssh -ErrorAction SilentlyContinue | Stop-Process -Force
```

验证（缺一不可）：
```bash
# 公网应当不可达（502 或连接失败）
curl -s -o /dev/null -w "pub:%{http_code}\n" --max-time 15 https://psyquiz2.serveousercontent.com/study1
# 本地应当仍然正常
curl -s --noproxy '*' -o /dev/null -w "quiz:%{http_code}\n" --max-time 6 http://127.0.0.1:8765/
curl -s --noproxy '*' -o /dev/null -w "ecg:%{http_code}\n"  --max-time 6 http://127.0.0.1:8766/api/health
# 日志应当停在关闭前的最后时间，没有新的重连
tail -3 "<quiz-app>\data\tunnel_watchdog.log"
```

- **不要**清 `data/tunnel_url.txt`：它只被看门狗写入、没有任何读取方（已实测 grep 确认），
  不会造成"死链接"展示，留着反而便于确认上次的公网地址。
- 重新对外开放 = 只需再起看门狗（<裸 python> tunnel_watchdog.py）。若刚被限流，先静置约 6 分钟。
- 关闭后**主动告知**：本地服务仍在跑；如需彻底停止请再说一句。

