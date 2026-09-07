# -*- coding: utf-8 -*-
"""PyInstaller 单文件 exe 资源替换：把帧序列/单图替换为新视频生成的透明 PNG。

调用示例（命令行）：
    python replace_asset.py DeskPet.exe 猫视频.webm DeskPet_猫.exe

工作流程：
1. 解析原 exe 的 CArchive，定位所有 `frames/frame_NNNN.png` 条目（视频模式）
   以及可能存在的 `dog.png` 类静态兜底图。
2. 用 ffmpeg（libvpx-vp9 自动处理 alpha）按 12fps 抽帧、缩放到合适尺寸。
3. 重新 zlib 压缩新帧、重建 CArchive（PE bootloader 原样保留）。

如果原 exe 不含 `frames/` 序列、只含单图，则只替换该单图。
"""
import argparse
import os
import sys
import zlib

# 允许从同目录直接 import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pyinstaller_carchive as ca  # noqa: E402
import ffmpeg_helper as fh  # noqa: E402


FRAME_PREFIX = "frames\\"
STATIC_FALLBACK_NAMES = ["dog.png", "pet.png", "icon.png", "avatar.png"]


def detect_mode(arch: ca.CArchive):
    """返回 ('frames', [Entry...]) 或 ('static', Entry) 或 ('none', None)。"""
    frames = [e for e in arch.entries if e.name.startswith(FRAME_PREFIX)]
    if frames:
        return "frames", frames
    for n in STATIC_FALLBACK_NAMES:
        for e in arch.entries:
            if e.name == n:
                return "static", e
    # 兜底：找一个最大的 PNG 类资源作为静态目标
    pngs = [e for e in arch.entries if e.name.lower().endswith(".png")
            and e.ulen > 1000]
    if pngs:
        return "static", max(pngs, key=lambda e: e.ulen)
    return "none", None


def rebuild_with_replaced_frames(arch: ca.CArchive, new_png_dir: str,
                                 dst: str) -> dict:
    """把 frames/ 序列替换为新 PNG（按文件名匹配），多出帧追加、缺失帧删除。"""
    frames = [e for e in arch.entries if e.name.startswith(FRAME_PREFIX)]
    old_names = {os.path.basename(e.name): e for e in frames}
    new_names = {f for f in os.listdir(new_png_dir) if f.endswith(".png")}
    common = sorted(set(old_names) & new_names)
    extra = sorted(new_names - set(old_names))
    print(f"  匹配帧: {len(common)}, 新增帧: {len(extra)}")

    # 收集所有需要写回的数据 (按原 TOC 顺序、跳过被删除的旧帧)
    blobs = []
    new_entries = []
    cur = len(arch._data_prefix)

    for e in arch.entries:
        if e.name.startswith(FRAME_PREFIX):
            base = os.path.basename(e.name)
            if base in common:
                raw = open(os.path.join(new_png_dir, base), "rb").read()
                comp = zlib.compress(raw, 9)
                blobs.append(comp)
                new_entries.append(ca.Entry(cur, len(comp), len(raw), 1,
                                            e.typecd, e.name))
                cur += len(comp)
            # 旧帧多余 → 跳过
            continue
        if e.dlen == 0:
            new_entries.append(ca.Entry(cur, 0, 0, 0, e.typecd, e.name))
            continue
        blob = arch._raw[arch.pkgstart + e.doff:
                         arch.pkgstart + e.doff + e.dlen]
        blobs.append(blob)
        new_entries.append(ca.Entry(cur, len(blob), e.ulen, e.cflag,
                                    e.typecd, e.name))
        cur += len(blob)

    # 追加新增帧（在 TOC 的 frames 区域后插入）
    if extra:
        ins = max((i for i, e in enumerate(new_entries)
                   if e.name.startswith(FRAME_PREFIX)),
                  default=len(new_entries) - 1) + 1
        add_blobs = []
        for f in extra:
            raw = open(os.path.join(new_png_dir, f), "rb").read()
            comp = zlib.compress(raw, 9)
            add_blobs.append(comp)
            new_entries.insert(ins, ca.Entry(cur, len(comp), len(raw), 1,
                                             "b", FRAME_PREFIX + f))
            cur += len(comp)
            ins += 1
        # 找到对应插入位置：原 frames 区域在 blobs 中已被替换为压缩数据，
        # 新增帧应追加到数据流末尾，并在 TOC 中插队
        blobs.extend(add_blobs)

    arch.entries = new_entries
    out = arch.rebuild_with_blobs(blobs)
    open(dst, "wb").write(out)
    return {"old_size": len(arch._raw), "new_size": len(out),
            "common": len(common), "extra": len(extra)}


def rebuild_with_replaced_static(arch: ca.CArchive, target_entry: ca.Entry,
                                 new_png: str, dst: str) -> dict:
    """替换单个 PNG 条目。"""
    raw = open(new_png, "rb").read()
    comp = zlib.compress(raw, 9)

    blobs = []
    new_entries = []
    cur = len(arch._data_prefix)
    replaced = False
    for e in arch.entries:
        if e.name == target_entry.name:
            blobs.append(comp)
            new_entries.append(ca.Entry(cur, len(comp), len(raw), 1,
                                        e.typecd, e.name))
            replaced = True
            cur += len(comp)
            continue
        if e.dlen == 0:
            new_entries.append(ca.Entry(cur, 0, 0, 0, e.typecd, e.name))
            continue
        blob = arch._raw[arch.pkgstart + e.doff:
                         arch.pkgstart + e.doff + e.dlen]
        blobs.append(blob)
        new_entries.append(ca.Entry(cur, len(blob), e.ulen, e.cflag,
                                    e.typecd, e.name))
        cur += len(blob)
    if not replaced:
        raise RuntimeError("目标条目未在 TOC 中找到")
    arch.entries = new_entries
    out = arch.rebuild_with_blobs(blobs)
    open(dst, "wb").write(out)
    return {"old_size": len(arch._raw), "new_size": len(out)}


def main():
    ap = argparse.ArgumentParser(description="替换 PyInstaller exe 中的帧序列/静态图")
    ap.add_argument("exe", help="原 PyInstaller 单文件 exe")
    ap.add_argument("video", help="新视频文件 (webm/mp4/mov, 推荐带 alpha)")
    ap.add_argument("output", help="输出新 exe 路径")
    ap.add_argument("--fps", type=float, default=12.0,
                    help="抽帧帧率，默认 12fps (匹配 83ms 切帧)")
    ap.add_argument("--workdir", default=None,
                    help="中间文件目录，默认 <exe 所在目录>/_replace_tmp")
    ap.add_argument("--width", type=int, default=600,
                    help="输出帧宽度（保持 4:3 比例）")
    args = ap.parse_args()

    workdir = args.workdir or os.path.join(
        os.path.dirname(os.path.abspath(args.exe)), "_replace_tmp")
    os.makedirs(workdir, exist_ok=True)
    new_png_dir = os.path.join(workdir, "new_frames")
    os.makedirs(new_png_dir, exist_ok=True)

    print(f"[1/4] 解析 {args.exe}")
    arch = ca.CArchive.from_file(args.exe)
    print(f"      pkgstart={arch.pkgstart} pyver={arch.pyver} "
          f"entries={len(arch.entries)}")

    mode, target = detect_mode(arch)
    print(f"      模式: {mode}  目标: "
          f"{[e.name for e in target] if isinstance(target, list) else target}")

    print(f"[2/4] 探测视频 {args.video}")
    info = fh.probe_video(args.video)
    print(f"      codec={info.get('codec')} "
          f"alpha_mode={info.get('alpha_mode')} "
          f"fps={info.get('fps')} duration={info.get('duration'):.2f}s")

    print(f"[3/4] 抽帧到 {new_png_dir} @ {args.fps}fps")
    pngs = fh.extract_alpha_frames(args.video, new_png_dir,
                                   target_fps=args.fps)
    print(f"      生成 {len(pngs)} 帧")

    # 缩放（如果指定）
    if args.width:
        try:
            from PIL import Image
            w, h = args.width, int(args.width * 3 / 4)
            print(f"      缩放到 {w}x{h}")
            for p in pngs:
                im = Image.open(p).convert("RGBA")
                if im.size != (w, h):
                    im = im.resize((w, h), Image.LANCZOS)
                im.save(p, optimize=True)
        except ImportError:
            print("      (PIL 未安装，跳过缩放)")

    print(f"[4/4] 重打包到 {args.output}")
    if mode == "frames":
        result = rebuild_with_replaced_frames(arch, new_png_dir, args.output)
    elif mode == "static":
        result = rebuild_with_replaced_static(arch, target, pngs[0], args.output)
    else:
        sys.exit("未找到可替换的帧/图像资源，请确认 exe 是 PyInstaller 打包且含有 PNG 资源")

    print("✅ 完成：", result)
    print(f"   原始 {result['old_size']/1e6:.1f}MB → 新 {result['new_size']/1e6:.1f}MB")


if __name__ == "__main__":
    main()