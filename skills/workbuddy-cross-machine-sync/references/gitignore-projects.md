# WorkBuddy 项目仓库忽略规则（projects repo, ~/WorkBuddy）

只同步「工作成果 + 项目记忆」，排除运行缓存。

```gitignore
# 项目内 .workbuddy 的运行态缓存（保留 memory/ 项目记忆）
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

**/.workbuddy/*.db
**/.workbuddy/*.db-shm
**/.workbuddy/*.db-wal

# 依赖与构建产物（按需增删）
**/node_modules/
**/.venv/
**/venv/
**/__pycache__/
*.pyc
**/dist/
**/build/
**/.next/
**/.output/

# 大体积生成物：视频/压缩包不进 git（需要则上 Git LFS）
**/*.mp4
**/*.mov
**/*.avi
**/*.zip
**/*.tar.gz

# 注：图片（png/jpg/svg）通常就是交付成果，默认【同步】。
# 只有当某项目产出海量图片撑爆仓库时，才在该项目下单独加 .gitignore 排除。

# 密钥类，永不提交
*.pem
*.key
.env
.env.*
!.env.example

# 系统/编辑器
.DS_Store
Thumbs.db
.idea/
.vscode/
```

# 跨平台换行符（仓库根目录 .gitattributes）

放在 `~/WorkBuddy/.gitattributes`，防止 macOS / Windows 之间 CRLF 反复变动。

```
* text=auto
*.png binary
*.jpg binary
*.jpeg binary
*.webp binary
*.gif binary
*.mp4 binary
*.mov binary
```
