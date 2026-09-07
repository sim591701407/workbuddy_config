# PyInstaller CArchive 格式参考

## 文件整体结构

PyInstaller 的单文件 exe 由两部分组成：

```
[PE bootloader ............] [CArchive 归档段 ........] [88B cookie]
└─── pkgstart ───────────────────────────────────┘    ▲
                                                     │
                                                  文件末尾
```

- **PE bootloader**：标准 Windows PE 文件，包含解包运行时所需的 Python 解释器与启动代码。**通常不需要修改**。
- **CArchive 归档段**：用户脚本 `deskpet.py`、依赖库、第三方二进制、PNG 资源等全部以压缩条目形式存放在此。
- **Cookie**：88 字节，固定在文件末尾，由 bootloader 反向搜索 magic 定位。

## Cookie 结构

| 偏移 | 长度 | 类型 | 说明 |
|------|------|------|------|
| 0    | 8    | `char[8]` | magic = `b"MEI\014\013\012\013\016"` |
| 8    | 4    | `uint32` | `lengthofPackage`（归档段总长 = TOC + 88） |
| 12   | 4    | `uint32` | `tocOff`（TOC 在归档段内的偏移） |
| 16   | 4    | `uint32` | `tocLen`（TOC 总字节数） |
| 20   | 4    | `uint32` | `pyver`（Python 主版本号，如 313） |
| 24   | 64   | `char[64]` | pylib（如 `python313.dll`），NUL 结尾 |

读取时按 `struct.unpack('!8sIIII', ...)` 解 24 字节，再读 64 字节 pylib。

`pkgstart` 计算：

```
pkgstart = cookie_pos + 88 - lengthofPackage
```

## TOC 条目

TOC 由连续条目构成，每条以 4 字节 `elen` 开头，整体按 16 字节对齐：

```
┌──────────┬───────────────────────────────────┬─────┬────────┐
│ elen (4) │ doff(4) | dlen(4) | ulen(4) |      │typecd│ name │ pad │
│          │ cflag(1) |                         │  (1) │  +0  │     │
└──────────┴───────────────────────────────────┴─────┴────────┘
```

| 字段 | 含义 |
|------|------|
| `doff` | 数据在归档段内的偏移（相对 `pkgstart`） |
| `dlen` | 磁盘上数据长度（压缩后或原始） |
| `ulen` | 解压后长度 |
| `cflag` | 1 = zlib 压缩；0 = 明文 |
| `typecd` | 资源类型：`b`=binary、`s`=script、`m`=pyc、`z`=PYZ、`o`=option、`x`=其他 |
| `name` | UTF-8 字符串，NUL 结尾 |

`typecd == 'o'` 的条目 `dlen=ulen=0`，不占数据区。

## 重建 CArchive

新增/替换条目时必须重建数据区 + TOC + cookie：

1. 跳过不存在的条目（删除）；
2. 压缩新条目（zlib level 9，匹配默认）；
3. 重新按 TOC 顺序拼接数据流，记录每条新 `doff`；
4. 序列化 TOC 到末尾；
5. 更新 cookie 的 `lengthofPackage = tocOff + tocLen + 88`。

## bootloader 兼容性

- PyInstaller ≥5.x：使用 88 字节 cookie + `lengthofPackage` 字段。
- PyInstaller <5.x：使用 64 字节 cookie，不含 `pyver` 字段。
- 二者都通过 `MEI\014\013\012\013\016` magic 反向搜索定位。

## 常见陷阱

- **不要修改 PE 头**：bootloader 会从文件末尾向前找 cookie，覆盖 PE 头会导致无法启动。
- **TOC 16 字节对齐**：每条 `elen + body` 总长必须是 16 的倍数，不足补 NUL。
- **`lengthofPackage` 必须精确**：差 1 字节就会让 bootloader 读取 TOC 时越界。
- **保持 zlib level 一致**：默认 level 9；用其他 level 也能跑，但与原 exe 文件体积不匹配。