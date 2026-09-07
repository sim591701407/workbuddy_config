# WorkBuddy 用户配置仓库忽略规则（config repo, ~/.workbuddy）

同步：记忆、技能、身份。屏蔽：运行态 / 二进制 / 缓存 / 含密钥文件（绝对不要同步 SQLite！）。

> 配置仓库采用**白名单式** `.gitignore`：默认忽略一切（`/*`），仅显式放行需要同步的文件。
> 直接复制下面整段到 `~/.workbuddy/.gitignore`（macOS）或 `%USERPROFILE%\.workbuddy\.gitignore`（Windows）即可。
> 注意：这份 `.gitignore` 自身也放行了（`!/.gitignore`），提交后其它机器 clone 会自动带上，不会再缺失。

```gitignore
# WorkBuddy 配置仓库白名单（whitelist）
# 默认忽略一切，仅放行以下需要跨设备同步的文件
# 注意：settings.json / mcp.json 含机器专属路径与可能的密钥，两台机器环境不同则不同步

/*
!/.gitignore
!/memory/
!/skills/
!/SOUL.md
!/IDENTITY.md
!/USER.md

# 白名单目录内的常规垃圾文件
*.bak
.DS_Store
Thumbs.db
```

## 常见问题

- **为什么不能直接列黑名单？** 因为 `~/.workbuddy` 里运行态文件太多（app/、binaries/、blobs/、local_storage/ 等），黑名单永远列不全；白名单保证新出现的目录也默认被忽略，`git add -A` 永远不会误提交敏感项。
- **settings.json / mcp.json 要不要放行？** 默认不放行。若两台电脑环境完全一致且你确认文件里无密钥，可自行把 `!/.mcp.json`、`!/settings.json` 追加到白名单，但务必先 `git diff` 审查。
- **workbuddy.db（及 -shm/-wal）绝对不同步**：SQLite 走 git 会损坏，且会话历史本来就该每台机器独立。
