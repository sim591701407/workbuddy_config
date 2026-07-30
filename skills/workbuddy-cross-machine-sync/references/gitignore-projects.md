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

# 依赖与构建产物（按需增删）
**/node_modules/
**/.venv/
**/venv/
**/__pycache__/
**/dist/
**/build/
**/.next/
**/.output/

# 大体积生成物：如需作为交付物保留，请用 Git LFS，或删掉下面几行
**/*.mp4
**/*.mov
**/*.png
**/*.jpg
**/*.jpeg
**/*.webp
**/*.gif

# 系统/编辑器
.DS_Store
Thumbs.db
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
