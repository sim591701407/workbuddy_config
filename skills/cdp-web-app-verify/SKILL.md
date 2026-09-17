---
name: cdp-web-app-verify
description: Verify a local web app's real UI in a real browser using zero-dependency Chrome DevTools Protocol automation from Node (Node 18+ built-in fetch/WebSocket). Use when a page "doesn't show" something, when you must prove a frontend fix visually rather than by curl-grepping HTML, when the agent-browser/Playwright toolchain is not installed, or for post-packaging acceptance of a local tool before handing it to a user. Drives the app's own JS entry points, asserts computed visibility (offsetHeight), collects page exceptions, and captures screenshots.
agent_created: true
---

# 用 CDP 验收本地 Web 应用（零依赖）

## Purpose
在**真实 Chrome** 里跑完一个本地 Web 工具的真实交互，并对 DOM 状态做出断言。适用于
「接口都 200、但页面上某块就是不显示」这类**纯前端 bug** —— 这类问题用 `curl | grep` 查不出来，
因为 HTML 里标记齐全、样式也齐全，坏的是 JS 运行时没把元素显出来。

## When to use
- 用户说「某功能没显示」「页面错位」「点了没反应」，而接口/HTML 看起来正常。
- 修了前端 bug，需要**证据**证明真的修好了（不是"我看代码觉得没问题"）。
- 打包 exe 之后，要对**产物**而非源码做交付前验收。
- `agent-browser` / Playwright 未安装（装它要下 ~500 MB Chromium），但本机已有 Chrome/Edge。

不适用：只需读取静态 HTML 文本（用 WebFetch / curl）；只需调 JSON 接口（用 curl）。

## 核心思路
本机通常已装 Chrome。用
`chrome --headless=new --remote-debugging-port=<port>` 起一个调试实例，然后用 **Node 原生
`fetch` + `WebSocket`**（Node 18+ 内置，无需 `ws`/`puppeteer`）连上 `/json/list` 拿到的
`webSocketDebuggerUrl`，直接发 CDP 消息：

| 目的 | CDP 方法 |
|---|---|
| 开页 / 导航 | `Page.navigate` |
| 在页面里跑 JS 并取回值 | `Runtime.evaluate`（`returnByValue: true`, `awaitPromise: true`） |
| 收集未捕获异常 | 监听 `Runtime.exceptionThrown` 事件 |
| 截图 | `Page.captureScreenshot`（`captureBeyondViewport: true` 可整页） |

`scripts/cdp_driver.js` 是一个可直接 `require` 的极简封装（`connect / eval / screenshot / onException`）。

## 步骤
1. **找 Chrome**（按此顺序）：
   - `C:\Program Files\Google\Chrome\Application\chrome.exe`
   - `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`
   - `CommandLineTools`… 在 macOS 用 `Google Chrome.app/Contents/MacOS/Google Chrome`
2. **起调试实例**（后台运行）。必须给它**独立的 `--user-data-dir`**，否则会污染用户日常浏览器配置、也可能因"已在运行"而不开调试端口：
   ```
   chrome --headless=new --disable-gpu --no-first-run --no-default-browser-check \
          --remote-debugging-port=9333 --user-data-dir="<临时目录>" \
          --window-size=1400,2600 about:blank
   ```
   等 `/json/version` 能返回即就绪。
3. **驱动并断言**：以 `scripts/verify_example_ecg_app.js` 为例——它把真实文件塞进页面、
   调页面自己的入口函数走完整流程，再断言 DOM。**断言"可见"要同时看**：
   ```js
   const cs = getComputedStyle(el);
   const visible = cs.display !== 'none' && !el.hidden && el.offsetHeight > 0;
   ```
   只看 `hidden` 属性或只看 `display` 都可能被骗（本项目就踩过：容器带 `hidden` 属性，
   而 CSS 另有 `[hidden]{display:none!important}` 兜底 —— 于是"属性为 true"才是可见的判断依据）。
4. **收尾**：`taskkill` / `Stop-Process` 关掉 Chrome，并把 `--user-data-dir` 目录移走。
   （该目录常被 Chromium 残留句柄锁住，删不掉 → 先杀进程再 `mv` 到系统 temp。）

## 关键坑
- **顶层 `let`/`const` 不挂到 `window`。** 页面若是普通 `<script>`，`let foo = ...` 只在
  "全局词法环境"里，`window.foo` 是 `undefined`。在 `Runtime.evaluate` 里**要用裸标识符**：
  `typeof foo !== 'undefined' && foo` —— 写成 `window.foo` 会静默拿到 `undefined`，
  然后被 `JSON.stringify` 丢掉，表现为"字段莫名缺失"，极难排查。
- **`returnByValue` 会丢掉 `undefined` 字段。** 想要的字段读不到时，先怀疑它是 `undefined`，
  再怀疑求值作用域（上一坑）。
- **路径给 Node 时用 Windows 风格。** 在 Git Bash 里把 `/c/Users/...` 传给 `node.exe` 会被
  解析成 `c:\c\Users\...`（`Cannot find module`）。传 `C:\Users\...`。
- **不要用 `wait --load networkidle` 式的死等。** 用**轮询断言**代替（如每 300 ms 查一次，
  最多 N 次），既快又不会卡死。
- **文件上传走页面自己的处理函数**，别去模拟 `<input type=file>` 的原生选择框：
  先把内容 base64 注入页面，再在页面里构造 `File` 并调用应用入口（如 `handleFile(f)`）。
- 断言要覆盖**每条交互分支**：快捷项、自定义输入、重置/取消、以及边界（过短片段应报错）。
- **页面级会话收不到 `Browser.*` 事件。** `Browser.setDownloadBehavior` /
  `Browser.downloadWillBegin` 等属于浏览器域，必须连 `/json/version` 返回的
  **browser 级 `webSocketDebuggerUrl`**，而不是 `/json/list` 里那个页级 target。

## 验收「下载 / 导出」功能
导出类功能**不能只看接口返回 200** —— 必须证明文件真的落盘、内容真的对。headless Chrome 的
原生下载管线经常不落地（`--headless=new` 下尤为常见），所以要**双保险**：

1. **主证据：页面内埋点持有 Blob 本体。** 在页面里劫持 `URL.createObjectURL`，把最后一次
   导出产生的 Blob 存到全局：
   ```js
   window.__lastBlob = null;
   const _orig = URL.createObjectURL;
   URL.createObjectURL = function (b) { window.__lastBlob = b; return _orig.call(URL, b); };
   ```
   再用 `Runtime.evaluate` 在页面里 `await window.__lastBlob.arrayBuffer()` →
   转 base64 **只回传字节**（Blob 对象本身不可序列化，回传对象一定拿不到东西），
   由 Node 写盘、再用**独立解析器**（openpyxl / Python `csv`）校验内容是否合法。
2. **旁证：确认原生下载事件也触发。** 先用 `Browser.setDownloadBehavior`
   （`behavior: "allow"` + `downloadPath`）开下载，再监听 `Browser.downloadWillBegin`；
   两者都通，才算"用户点按钮能拿到文件"。只信其中一条都可能误判。
3. **逐文件核断言**：文件名（尤其中文名需 RFC 5987 编码后仍正确）、工作表数量、行数、
   编码（CSV 要有 UTF-8 BOM，否则 Excel 中文乱码）、关键数值是否与页面显示一致。

## 最小可复用骨架
```js
const cdp = await CdpDriver.connect(9333);          // 见 scripts/cdp_driver.js
const errs = []; cdp.onException(e => errs.push(e));
await cdp.navigate("http://localhost:8766/");
await cdp.eval(`(async () => { /* 走完交互 */ return true; })()`);
const ok = await cdp.eval(`(() => {
  const el = document.querySelector('#target');
  const cs = getComputedStyle(el);
  return { hidden: el.hidden, display: cs.display, visible: cs.display !== 'none' && el.offsetHeight > 0 };
})()`);
await cdp.screenshot("<out.png>");
await cdp.close();
if (!ok.visible) throw new Error("目标区域仍不可见");
```
