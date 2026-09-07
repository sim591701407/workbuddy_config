# -*- coding: utf-8 -*-
"""定位并包装 ffmpeg，使解码透明 webm 等带 alpha 通道的视频变得简单。

实现要点：
- 优先尝试系统 PATH 中的 `ffmpeg`；
- 若不可用，则尝试 `imageio_ffmpeg.get_ffmpeg_exe()`（imageio-ffmpeg 包
  内置跨平台静态二进制，无需额外安装系统组件）；
- 仍找不到则抛出明确错误，提示安装命令。

只暴露高层函数 `extract_alpha_frames`。
"""
import os
import shutil
import subprocess
import tempfile
from typing import List, Optional


def find_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    try:
        import imageio_ffmpeg  # type: ignore
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as e:
        raise RuntimeError(
            "未找到 ffmpeg。请在隔离 Python 环境中安装：\n"
            "    pip install imageio-ffmpeg\n"
            "或在 PATH 中提供 ffmpeg 可执行文件。"
        ) from e


def probe_video(path: str) -> dict:
    """用 ffmpeg -i 解析视频基本信息。"""
    ffmpeg = find_ffmpeg()
    out = subprocess.run(
        [ffmpeg, "-i", path], capture_output=True, text=True, check=False
    )
    info = {"stderr": out.stderr}
    # 简易解析：codec / 分辨率 / fps / 时长
    import re
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out.stderr)
    if m:
        h, mi, s = map(float, m.groups())
        info["duration"] = h * 3600 + mi * 60 + s
    m = re.search(r"Video:\s+(\S+)\s*\([^)]*\),\s*([^\s,]+)", out.stderr)
    if m:
        info["codec"] = m.group(1)
        info["pix_fmt"] = m.group(2)
    m = re.search(r"alpha_mode\s*:\s*(\d+)", out.stderr)
    if m:
        info["alpha_mode"] = int(m.group(1))
    m = re.search(r"\b(\d+)x(\d+)\b", out.stderr)
    if m:
        info["width"], info["height"] = int(m.group(1)), int(m.group(2))
    m = re.search(r",\s*([\d.]+)\s*fps", out.stderr)
    if m:
        info["fps"] = float(m.group(1))
    return info


def extract_alpha_frames(src_video: str, out_dir: str,
                         target_fps: float = 12.0,
                         prefix: str = "frame_",
                         start_index: int = 0) -> List[str]:
    """解码带透明通道的视频，按 `target_fps` 抽帧为 PNG。

    自动选择保留 alpha 的解码器：
      - vp9/vp8  → libvpx-vp9/libvpx-vp8
      - 其他     → 默认解码器 (大多数情况可保留 alpha)

    返回所有生成的 PNG 路径列表（按数字顺序）。
    """
    ffmpeg = find_ffmpeg()
    os.makedirs(out_dir, exist_ok=True)
    info = probe_video(src_video)
    codec = info.get("codec", "")
    if "vp9" in codec:
        dec = ["-c:v", "libvpx-vp9"]
    elif "vp8" in codec:
        dec = ["-c:v", "libvpx-vp8"]
    elif "av1" in codec:
        dec = ["-c:v", "libaom-av1"]
    else:
        dec = []
    out_pattern = os.path.join(out_dir, f"{prefix}%04d.png")
    cmd = [ffmpeg, "-y", *dec, "-i", src_video,
           "-vf", f"fps={target_fps}",
           "-start_number", str(start_index),
           out_pattern]
    subprocess.run(cmd, check=True, capture_output=True)
    pngs = sorted(p for p in os.listdir(out_dir)
                  if p.startswith(prefix) and p.endswith(".png"))
    return [os.path.join(out_dir, p) for p in pngs]


def compress_pngs(png_paths: List[str], max_dim: Optional[int] = None) -> bytes:
    """读取一组 PNG 并用 PIL 缩放到目标尺寸，返回 ZIP 风格 bytes 流。
    这里改为直接返回原始字节流的总和；实际项目中通常要 numpy→PNG 序列化。
    保留为占位函数：调用方可自行遍历再压缩。
    """
    raise NotImplementedError("仅作为占位；请使用 PIL.Image 自行处理")