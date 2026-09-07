---
name: pyinstaller-asset-replacer
description: This skill should be used when a user wants to replace image/video resources (PNG sequences, static PNGs) inside a PyInstaller single-file Windows executable (`.exe`) without re-running the original build. It parses the PyInstaller CArchive overlay, swaps out `frames/*.png` sequences or fallback PNGs with new transparent WebM/MP4-derived PNG frames, and rebuilds the executable while preserving the original PE bootloader, Python runtime, and all other entries. Triggers on requests like "把桌面宠物 exe 里的小狗视频换成猫" / "替换 PyInstaller exe 里的图片资源" / "swap the dog animation inside this exe with a cat" / "patch a single-file PyInstaller exe to use different assets".
agent_created: true
---

# pyinstaller-asset-replacer

## When to use

Use this skill when the user provides:

1. A **PyInstaller single-file Windows `.exe`** (PE format, single overlay at end).
2. An **alternative video or image** (preferably WebM with alpha channel, MP4/MOV also work) intended to replace the asset(s) inside the exe.
3. An **output path** for the new exe.

Typical triggers:
- "把小狗桌宠里的视频换成猫猫"
- "替换这个 exe 里的小狗图片，但别改其它东西"
- "patch this PyInstaller app's animation"

## How to use

### Step 1 — Confirm inputs

Ask for (or read from `user_references`):

- `<exe>` — path to the original single-file exe
- `<video>` — path to replacement video (WebM with alpha is preferred)
- `<output>` — path to write the new exe

Verify each exists. If a video lacks an alpha channel but the original exe shows the asset on a transparent background, warn the user: the replacement may show a black/white background.

### Step 2 — Install ffmpeg (one-time)

The skill uses `imageio-ffmpeg` which bundles a static ffmpeg binary, so no system install is needed. In an isolated Python environment:

```
pip install imageio-ffmpeg pillow
```

These are needed because:
- `imageio-ffmpeg` provides a static ffmpeg that can decode WebM alpha.
- `Pillow` is used to resize the generated PNG frames.

### Step 3 — Run the replacement

Execute `scripts/replace_asset.py` with the three paths:

```
python scripts/replace_asset.py <exe> <video> <output> --fps 12 --width 600
```

The script:
1. Parses the exe CArchive (see `references/pyinstaller_format.md`).
2. Detects whether the exe contains a `frames/frame_NNNN.png` sequence (video mode) or only a single PNG fallback (static mode).
3. Probes the replacement video with ffmpeg to detect codec, alpha, fps, resolution.
4. Extracts frames at `--fps` (default 12 = 83ms per frame, matching common DeskPet-style animators) preserving alpha. Uses `libvpx-vp9`/`libvpx-vp8`/`libaom-av1` decoder when needed.
5. Resizes frames to `--width` keeping 4:3 ratio (default 600×450).
6. Rebuilds the CArchive:
   - Keeps the PE bootloader bytes unchanged.
   - Compresses new frames with zlib level 9.
   - Reuses original compression streams for all other entries (Python runtime, Qt DLLs, main script, etc.).
   - Recomputes TOC offsets and the 88-byte cookie (`lengthofPackage`, `tocOff`, `tocLen`).

### Step 4 — Validate

After writing the new exe, do a smoke test:

1. Re-parse the new exe with the same script — all 253+ entries must decompress without error.
2. Launch the exe briefly and verify it does not crash (the cookie's `lengthofPackage` will silently corrupt the bootloader if miscalculated).
3. Optionally screenshot to confirm visual change.

### Step 5 — Deliver

Use `present_files` to deliver the new exe to the user. Note that this skill only replaces image assets — it cannot change Python source code, add new dependencies, or modify the bootloader.

## Reusable resources in this skill

- **`scripts/pyinstaller_carchive.py`** — pure-stdlib CArchive parser & writer. Use directly when you need to inspect or modify a PyInstaller exe from Python.
- **`scripts/ffmpeg_helper.py`** — locates ffmpeg via PATH or `imageio_ffmpeg`, probes a video, and extracts alpha-preserving PNG frames at a target fps.
- **`scripts/replace_asset.py`** — the end-to-end CLI tool. Wires the two helpers together and handles mode detection (frames vs static).
- **`references/pyinstaller_format.md`** — full byte-level format of the CArchive overlay, cookie, and TOC. Read this when troubleshooting rebuild errors or supporting a different PyInstaller version.

## Failure modes & fixes

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `未找到 PyInstaller cookie magic` | exe is not a PyInstaller single-file build (could be PyInstaller folder, Nuitka, cx_Freeze, Electron) | Reject the request; skill only supports `--onefile` PyInstaller |
| New exe crashes immediately | `lengthofPackage` miscalculated | Check that `tocOff + tocLen + 88 == lengthofPackage` before writing |
| Generated frames have black background | Source video has no alpha channel | Re-export source video with alpha (WebM VP9 + alpha) or warn user |
| Output exe is huge | Frames not optimized | Add `optimize=True` to PIL save, or downscale further |
| `未找到 ffmpeg` | Neither system ffmpeg nor `imageio-ffmpeg` installed | `pip install imageio-ffmpeg` in the active Python env |

## Limitations

- Only PyInstaller `--onefile` executables are supported. Folder-mode (`--onedir`) builds embed resources differently.
- Only PNG image assets can be replaced. Audio, fonts, or other binary formats will be replaced as-is but may not render correctly.
- The skill does not handle PyInstaller bootloader version differences below 5.x — older versions use a 64-byte cookie. Most modern exe files use the 88-byte format.
- Cannot patch the main Python script. To change program logic, the user must rebuild from source.