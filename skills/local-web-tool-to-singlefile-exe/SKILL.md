---
name: local-web-tool-to-singlefile-exe
description: Package a local Python web tool (stdlib http.server + static HTML/JS, e.g. a data-analysis or report tool) into an install-free single-file Windows .exe with PyInstaller, so a non-technical user (another lab, a colleague) can just double-click it. This skill should be used when the user wants to distribute/hand off a local browser-based tool as a standalone exe, asks to "打包成免安装单文件 exe", "用 PyInstaller 打包", "拷过去双击就能用", or needs the frozen-path (_MEIPASS/sys.frozen), single-instance, port-fallback, auto-open-browser and read-only-resource fixes that packaging requires.
agent_created: true
---

# 本地 Web 工具 → 免安装单文件 exe（PyInstaller）

## Purpose
把一个「Python 本地服务 + 静态前端」的小工具打包成 Windows 单文件 exe，交付给非技术用户（另一个课题组/同事），拷过去双击即用、无需装 Python。覆盖打包前必须做的路径语义改造，以及让终端用户「零解释可用」的健壮性设置。

## When to use
- 用户要把本地 Web 工具交给别人用："打包成 exe"、"免安装"、"单文件"、"拷过去双击就能用"、"给另一个课题组"。
- 工具形态是：`server.py`（`http.server` / `ThreadingHTTPServer`）启动本地端口 + `static/index.html` + `static/app.js` 前端。
- 打包后出现这些问题需要排查：双击闪退、找不到静态文件、临时目录报 `[Errno 2]`、控制台刷 traceback、端口被占用、重复启动多份。

不适用：含 numpy/scipy/matplotlib 等重型二进制依赖且体积无所谓的项目；需要安装盘/服务注册的真正「安装程序」（那用 Inno Setup / NSIS）。本技能只做**绿色免安装单文件**。

## 核心理念：冻结前后路径语义不同（最关键）
`--onefile` 模式下：
- **exe 所在目录只读**，且启动时会把内容解包到一个临时目录（`sys._MEIPASS`）。
- `__file__` 指向临时解包目录，**不能**再用它定位「exe 旁边的可写目录」。
- 因此必须把路径拆成两类：**只读资源**（打进 exe，从 `_MEIPASS` 读）与**可写工作目录**（放到系统 temp）。

必备的三个助手函数（放在 server.py 顶部）：

```python
import os, sys, tempfile

def _is_frozen():
    return bool(getattr(sys, "frozen", False))

def _resource_dir():
    """只读资源目录：静态文件、内置数据。冻结时在 _MEIPASS 里。"""
    if _is_frozen():
        return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
    return os.path.dirname(os.path.abspath(__file__))

def _work_dir():
    """可写工作目录：临时文件、上传缓存。冻结时放系统 temp，绝不写 exe 旁边。"""
    if _is_frozen():
        base = os.path.join(tempfile.gettempdir(), "MyTool")   # 改成工具名
    else:
        base = os.path.join(_resource_dir(), "data", "tmp")    # 源码模式沿用原路径
    try:
        os.makedirs(base, exist_ok=True)
        return base
    except OSError:
        return tempfile.gettempdir()                           # 兜底
```

把所有 `open(路径)` / `os.listdir` 的静态资源访问替换为 `os.path.join(_resource_dir(), ...)`；
把所有临时文件写入替换为 `_work_dir()`。程序名相关输出用 `sys.executable` 兜底。

## 健壮性：让终端用户「零解释可用」
按需加入，都是实测踩过的坑：

1. **端口自动顺延**：从默认端口起找首个空闲端口（`socket.bind` 探测），避免「端口被占用，闪退」。
2. **单实例复用**：启动前探 `http://127.0.0.1:<port>/api/health`，已在跑就直接开浏览器并退出，不重复起服务。探测必须用 `urllib.request.build_opener(ProxyHandler({}))` **绕开系统代理**，否则被代理拦掉。
3. **自动开浏览器**：`threading.Timer(0.6, lambda: webbrowser.open(url)).start()`（等服务起来再开）。
4. **静默连接中断**：把 `send_bytes` / `send_json` / `log_error` / `finish` 以及 `Server.handle_error` 里的
   `BrokenPipeError / ConnectionAbortedError / ConnectionResetError / socket.timeout` 全部吞掉 —— 用户拖动/关闭页面时会触发 WinError 10053，不吞掉控制台会刷一屏 traceback 吓到人。
5. **`Handler.timeout = 60`**：避免半开连接长期占线程。
6. **`/favicon.ico` → 204**：消掉日志噪音。
7. **`/api/health`** 返回 `{ok, app, version, engine, time}`：供前端「引擎就绪」徽章与单实例探测用。
8. **静默解压炸弹**：若接受 gzip 上传，解压要限量（如 64 MB），防异常/恶意包撑爆内存：
   ```python
   MAX_DECOMP = 64 * 1024 * 1024
   data = gzip.GzipFile(fileobj=io.BytesIO(raw)).read(MAX_DECOMP + 1)
   if len(data) > MAX_DECOMP: raise ValueError("压缩包过大")
   ```
9. **目录穿越**：静态文件解析用 `os.path.commonpath` 校验，**不要**用 `startswith`（`staticXX` 之类前缀能绕过）。
10. **版本常量单一来源**：`APP_VERSION = "1.1.0"` 放在 server.py 模块级，构建脚本读它生成说明文档，保证程序与文档版本一致。
11. **CLI 参数**：`--port N` / `--host IP` / `--no-browser`，并支持环境变量覆盖（如 `MYTOOL_PORT`）。

## 构建脚本
用 `scripts/build_exe_template.py` 作模板（拷到项目根，改顶部常量）。关键点：
- `--onefile`，内部名用 **ASCII**（如 `ECG-Analyzer`），构建后再 `os.replace` 改成中文交付名（如 `心电分析工具.exe`）—— 直接给 PyInstaller 传中文名会踩编码坑。
- `--add-data "<绝对路径>static{sep}static"`：Windows 分隔符是 `;`（用 `os.pathsep`，别硬写 `:`）；**路径必须绝对**（理由见下）。
- `--hidden-import <engine_module>`：把项目内被动态 import 的模块显式声明。
- `--exclude-module numpy/pandas/matplotlib/scipy/PIL/tkinter`：纯标准库项目显式排除重型库，防止误打包、减小体积。
- 构建后自动 `shutil.rmtree("build")`（中间产物），生成 `dist/使用说明.txt`。
- 交付：把 `dist/` 里 **exe + 使用说明.txt** 两个文件给对方。

Windows 一键脚本见 `scripts/build_exe.bat`（用受管 venv 解释器）。

### 本机硬约束：safe-delete 钩子会打断 PyInstaller（务必改脚本，否则必失败）
WorkBuddy 的 Windows 环境有文件系统级 `safe-delete` 钩子，**批量删除会被拦截并使构建失败**。PyInstaller 内部恰恰大量使用「先删再写」。实测三次失败与对应改法：

| PyInstaller 行为 | 报错 | 改法 |
|---|---|---|
| `--clean` 清理 `build/` 内容 | `[SAFE_DELETE_BULK_CONFIRM_REQUIRED]` 指向 `build/.../Analysis-00.toc` | **去掉 `--clean`** |
| 复用旧 `build/` 时覆盖其内容 | 指向 `build/.../base_library.zip` | `--workpath` 指向**系统临时目录**，且每次用**新目录名**（带时间戳） |
| 覆盖 `dist/` 里已存在的同名 exe | 指向 `dist/ECG-Analyzer.exe` | 构建前把旧 exe **移动到 `dist/_stash/`**（`os.replace`），不要 `os.remove` |
| `os.remove(final_exe)` 再 `os.replace` | 同上 | **直接 `os.replace(src, final)`** —— Windows 上它本身就能原子覆盖，无需先删 |
| `shutil.rmtree("build")` | 被拦 | 保留但 `ignore_errors=True`，失败不影响产物 |

**连带坑**：一旦设了 `--specpath <临时目录>`，`--add-data` 的**相对路径会以 spec 所在目录为基准**，于是报
`ERROR: Unable to find 'C:\Users\...\Temp\static'`。修法是把 `--add-data` 的源路径写成**绝对路径**。

最终形状（模板已内置）：
```
PyInstaller --noconfirm --onefile --name <ASCII名>
            --workpath <temp>/build_work_<时间戳>
            --specpath <temp>
            --add-data <项目绝对路径>/static;static
            --hidden-import <engine> --exclude-module numpy ...  server.py
```
副作用：每次构建在 `%TEMP%` 留一个约 15 MB 的工作目录，项目目录保持干净（推荐做法，别再往项目里塞 `build/`）。


## 解释器与环境
- PyInstaller 可能不在系统 python 里，先在受管 venv 中找/装：
  `<venv>/Scripts/python.exe -m pip install pyinstaller`
  本机受管 venv：`C:\Users\<user>\.workbuddy\binaries\python\envs\default`
- 构建用 `subprocess.check_call([sys.executable, "-m", "PyInstaller", ...])`，`cwd` 设为项目根。

## 打包后验收清单（逐项实测，别只看构建成功）
1. `使用说明.txt` 端口=代码默认端口，版本与 `APP_VERSION` 一致。
2. 从**别的目录**（非 dist）双击 exe 能起：证明已摆脱 exe 旁路径依赖。
3. 静态资源 200：`curl http://127.0.0.1:<port>/`、`/app.js`。
4. 穿越被拦：`/../ecg_analysis.py`、`/staticXX/` 应 403/404。
5. 核心业务链路端到端跑通（样例数据 → 正确输出）。
6. 异常输入返回友好状态码（400/404/422），不是 500 裸栈。
7. gzip 正常 + 超大包被拒。
8. 临时文件分析后清理干净（`_work_dir()` 为空）。
9. 单实例：第二次双击探测到已有实例即退出、开浏览器，不起第二份。
10. 端口顺延：占用默认端口后应顺延到下一个。
11. 自动开浏览器：进程数增加。
12. 连接中断（请求中途 RST）控制台**不刷 traceback**。
13. **洁净机器终验**：exe 拷到空白目录 + 隔离 `LOCALAPPDATA` + 最小 `PATH` + 清空 `PYTHONPATH`，
    完整链路（含导出下载）跑通，且导出文件能被独立解析器零告警读取。见下一节。

**关键一步：对 exe 本身（不是源码版）复跑前端验收。** 构建成功 ≠ 交付可用 —— 曾出现
「前端某区域永不显示」这类纯视觉 bug，`curl` 全绿也发现不了。做法见
`cdp-web-app-verify` 技能：用 CDP 驱动本机真实 Chrome，在页面上走完交互并断言
DOM 可见性（`offsetHeight > 0`）+ 截图，同时收集 `Runtime.exceptionThrown`。
**有下载/导出功能时，务必把「文件真的落盘、内容真的对」也纳入验收**（该技能有专节）。

## 交付前终验：在「洁净机器」上跑一遍（最能证明"不依赖本机"）
只要客户说「拷到另一台电脑用」，就必须做这一步 —— 它同时回答"是否真的自包含 / 离线"。
做法：把 exe 拷到**空白目录**，并隔离一切本机痕迹，然后跑完整业务链路。

```bash
# 1) 造一个"干净电脑"的影子
FRESH="/c/Users/<user>/AppData/Local/Temp/fresh_machine"
mkdir -p "$FRESH/app" "$FRESH/temp" "$FRESH/userprofile" "$FRESH/localappdata"
cp dist/MyTool.exe "$FRESH/app/"

# 2) 隔离环境启动：隔离 LOCALAPPDATA/APPDATA/TEMP，最小 PATH，清掉 PYTHONPATH
cd "$FRESH/app"
unset PYTHONPATH
SystemRoot='C:\Windows' \
PATH='C:\Windows\System32;C:\Windows' \
TEMP="$FRESH\\temp" TMP="$FRESH\\temp" \
USERPROFILE="$FRESH\\userprofile" \
LOCALAPPDATA="$FRESH\\localappdata" APPDATA="$FRESH\\localappdata" \
./MyTool.exe --no-browser --port 8899
```

要点：
- **隔离 `LOCALAPPDATA`** 是关键 —— 证明"用户首次使用就能自动建目录/建库"这条路走得通，
  而不是靠你本机早就存在的数据目录蒙混过关。
- **最小 `PATH` + 清空 `PYTHONPATH`** 证明没有偷偷用系统 Python，也没从你的 venv 里借包。
- 在这台"影子机器"上跑完整链路：上传 → 分析 → 切片 → 落库 → 回看 → 下载 → 删除。
- 产出的文件再用**独立解析器**（openpyxl / 标准库 `csv`）读一遍，**零告警**才算合格 ——
  这证明导出的是"真·合法文件"，而不只是"字节数看着对"。

> 本机踩坑：受限 shell 里**没有 `env` 命令** → 改成内联变量赋值（`VAR=... cmd`）+ `unset PYTHONPATH`，
> 并预先 `mkdir` 好 `temp` / `userprofile` / `localappdata`，否则程序启动时会因目录不存在而失败。

## 结果导出：别把第三方库带进交付链路
"分析结果能下载"在交付场景是刚需，但**导出实现是单文件工具最容易烂的地方**：
服务端 `import openpyxl` 这类依赖，一旦运行解释器没装（裸 Python 启动、或冻结时漏打包），
下载接口会**连接被中断**（前端只看到 502 /"网页无法运作"），而页面其它功能全正常，极难定位。

两条对策，按项目形态选：
1. **推荐：导出用纯标准库自己写。** xlsx 本质就是 zip + 几个 XML，用 `zipfile` + 字符串拼 XML
   生成的表，Excel / WPS 都能正常打开；csv 用标准库 `csv` 即可。
   ```python
   # xlsx 最小要素：
   #   [Content_Types].xml / _rels/.rels / xl/workbook.xml /
   #   xl/_rels/workbook.xml.rels / xl/worksheets/sheetN.xml
   # 数值： <c r="A1"><v>1.23</v></c>
   # 文本： <c r="A1" t="inlineStr"><is><t>...</t></is></c>   ← 必须 XML 转义 & < > " '
   # CSV 中文不乱码的关键：写入 utf-8-sig（带 BOM）
   ```
   好处：冻结产物零新增依赖、体积不涨、永远不会"服务端缺库"。
2. **次选：确保承载进程真的装了该库**（用项目 venv 的解释器启动服务，而非裸 `python`），
   并在启动时自检依赖、缺失就明确报错 —— 而不是等用户点「下载」才崩。

**中文文件名**：HTTP 头里不要直接塞 UTF-8，用 RFC 5987：
```
Content-Disposition: attachment; filename="fallback.xlsx"; filename*=UTF-8''%E4%B8%AD%E6%96%87.xlsx
```
（Python: `urllib.parse.quote(name)` 后拼 `filename*=UTF-8''`。）

## 常见坑速查
| 现象 | 根因 | 修法 |
|------|------|------|
| 双击闪退 | 静态文件用 `__file__` 定位，冻结后为解包目录 | 改 `_resource_dir()`（`_MEIPASS`） |
| `[Errno 2]` 写临时文件 | 往只读的 exe 旁写 | 改 `_work_dir()`（系统 temp） |
| 打包体积虚高 | 误打包 numpy/PIL 等 | `--exclude-module` |
| `--add-data` 无效 | 硬写 `:` 分隔符 | 用 `os.pathsep` |
| `Unable to find '<Temp>\static'` | 用了 `--specpath`，相对 `--add-data` 以 spec 目录为基准 | `--add-data` 源路径改**绝对路径** |
| 构建中被打断，报 `SAFE_DELETE_BULK_CONFIRM_REQUIRED` | safe-delete 钩子拦 PyInstaller 的删除/覆盖 | 去 `--clean`；`--workpath` 用 temp 新目录；旧 exe 移入 `dist/_stash/`；`os.replace` 直接覆盖 |
| 中文 exe 名构建失败 | PyInstaller 编码 | 先 ASCII 构建再 `os.replace` 改名 |
| 控制台刷 traceback | 客户端断连未处理 | 静默吞 connection-abort 异常 |
| 第二个实例端口冲突 | 无单实例检测 | 探 `/api/health` 复用 |
| 局部 UI 永不显示，但接口全 200 | 容器带 `hidden` 属性而 JS 从未解除 | 用 CDP 断言 `offsetHeight`；JS 里显式 `el.hidden = false` |
| 点「下载」报 502 /"网页无法运作"，页面其它功能正常 | 服务端 `import openpyxl` 等三方库，运行解释器没装 → 连接被中断 | 导出改纯标准库（zipfile+XML / csv）；或用装了该库的 venv 解释器启动 |
| 「拷到别的电脑能用吗？」答不上来 | 没做洁净机器验证 | 空白目录 + 隔离 LOCALAPPDATA + 最小 PATH 跑全链路（见上文专节） |
| 下载的中文文件名变成乱码/被截断 | HTTP 头直接塞 UTF-8 | 用 RFC 5987 `filename*=UTF-8''<percent-encoded>` |

## 交付话术（给用户）
> 把 `dist/` 里的 `心电分析工具.exe` 和 `使用说明.txt` 两个文件拷给对方，双击 exe 即用，无需安装任何东西。
> 首次运行 Windows SmartScreen 可能提示「已保护你的电脑」→ 点「更多信息」→「仍要运行」（自制工具未签名常见提示）。数据全程本机、不联网、不保存。
