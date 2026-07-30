# Syncthing 忽略规则（.stignore，放在 WorkBuddy 同步文件夹根）

必须排除运行态与 SQLite，避免损坏与冲突风暴。

```
# SQLite 数据库（绝对不要同步）
workbuddy.db
workbuddy.db-shm
workbuddy.db-wal

# 运行态缓存（项目内 .workbuddy）
**/.workbuddy/app/
**/.workbuddy/logs/
**/.workbuddy/sessions/
**/.workbuddy/traces/
**/.workbuddy/audit-log/
**/.workbuddy/shell-snapshots/
**/.workbuddy/file-history/
**/.workbuddy/blobs/
**/.workbuddy/local_storage/
**/.workbuddy/artifact-index/
**/.workbuddy/plans/

# 依赖与构建产物
**/node_modules/
**/.venv/
**/dist/
**/build/

# 系统/编辑器
.DS_Store
Thumbs.db
```
