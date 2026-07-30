# WorkBuddy 用户配置仓库忽略规则（config repo, ~/.workbuddy）

同步：记忆、技能、身份、配置。屏蔽：运行态 / 二进制 / 缓存（绝对不要同步 SQLite！）。

```gitignore
# ===== 同步 =====
memory/
skills/
SOUL.md
IDENTITY.md
USER.md
settings.json
mcp.json

# ===== 屏蔽（运行态 / 二进制 / 缓存，切勿同步 SQLite）=====
workbuddy.db
workbuddy.db-shm
workbuddy.db-wal
app/
logs/
sessions/
traces/
audit-log/
shell-snapshots/
file-history/
blobs/
local_storage/
artifact-index/
plans/
workspace/
binaries/
plugins/
connectors/
connectors-marketplace/
.workbuddy-sqlite-migrations/
*.port
.DS_Store
Thumbs.db
```

> 注意：`settings.json` / `mcp.json` 可能含机器专属绝对路径（MCP 服务命令路径、插件路径）。
> 若两台电脑环境差异大，将上面两行从「同步」移到「屏蔽」，避免把 A 机路径原样带到 B 机导致配置失效。
