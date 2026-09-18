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

**Reliable process check on this box — PowerShell stdout does NOT return.** Write to a file and Read it:
```powershell
$out = @(); $out += "listen8765=" + (Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue).Count
$out += "pythonProcs=" + @(Get-Process python -ErrorAction SilentlyContinue).Count
$out += "sshProcs=" + @(Get-Process ssh -ErrorAction SilentlyContinue).Count
$out | Set-Content -Path "<tmp>\_stat.txt" -Encoding UTF8
```

### Step 2 — Clear leftovers, then start all three (order matters)
```bash
taskkill //IM ssh.exe //F 2>/dev/null; echo "ssh cleaned"
```
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

**2. serveo binding freeze (502 after a restart).** Restarting the quiz server makes the watchdog reconnect instantly; repeated reclaims of the same subdomain get throttled and **even random subdomains are refused**. Recovery: stop the watchdog, `taskkill //IM ssh.exe //F`, wait ~6 minutes, then restart the watchdog — it recaptures `psyquiz2` on the first try.
**However:** if the services have been down for hours or days, the binding has already lapsed — skip the wait and start the watchdog directly (observed 2026-09-10, 09-16, 09-17: connects within ~5s every time).

**3. The tunnel only fronts quiz-app (8765).** ecg-analysis-app (8766) is local-only by design; `start.sh`/`start.bat` are provided if the user wants it standalone.

**4. 本机 curl 一律加 `--noproxy '*'`（防御性）。** 本环境注入了 `http_proxy` / `https_proxy`
（端口**每个会话都可能不同**，见过 `7890`、`14025`，**不要硬编码**）。2026-09-18 实测当前 curl
对 `localhost` / `127.0.0.1` 会绕过代理，所以不加也不会误报；但一旦某个会话的代理拦截了 localhost，
**健康的服务会显示 502**，会被误判成"服务挂了"而白重启一轮。加 `--noproxy '*'` 零成本。

**5. Do not rely on these lasting.** All three live in session background tasks. Tell the user once more that
`quiz-app\start-demo.bat` (quiz + watchdog) and `ecg-analysis-app\start.bat` launch them in independent
windows, which survive session teardown.

## After restoring
Append a line to the workspace daily log `C:\Users\Administrator\WorkBuddy\2026-08-14-11-06-52\.workbuddy\memory\YYYY-MM-DD.md` recording: services restarted, task ids, tunnel capture timestamp, and verification result. Always offer the `start-*.bat` alternative.
