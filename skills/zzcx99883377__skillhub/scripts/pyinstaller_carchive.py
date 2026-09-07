# -*- coding: utf-8 -*-
"""PyInstaller CArchive 解析与重打包工具。

CArchive 是 PyInstaller 单文件 exe 末尾的"归档段"，从尾部搜索 magic
`MEI\014\013\012\013\016` 即可定位。结构：

    [PE bootloader ...] [归档数据区 ...] [TOC ...] [88 字节 cookie]

cookie 由 `!8sIIII`（magic、lengthofPackage、tocOff、tocLen、pyver）
和 64 字节 pylib 路径组成。
TOC 每条以 `!I`(elen) 起头，结构为 `!IIIIB c`(doff, dlen, ulen, cflag, typecd) + 名称 + \0 + 16 字节对齐填充。

仅依赖标准库；可在隔离 Python 环境中独立运行。
"""
import struct
import zlib
from dataclasses import dataclass, field
from typing import List, Optional

MAGIC = b"MEI\014\013\012\013\016"
COOKIE_LEN = 88


@dataclass
class Entry:
    """归档中的一条资源。"""
    doff: int        # 数据在归档段中的偏移
    dlen: int        # 数据在归档段中的长度（压缩后或原始）
    ulen: int        # 解压后长度
    cflag: int       # 1 表示 zlib 压缩，0 表示明文
    typecd: str      # 'b'=二进制 'm'=py模块 's'=脚本 'z'=PYZ ...
    name: str = field(default="")  # 资源相对路径

    def to_raw(self) -> bytes:
        nb = self.name.encode("utf-8") + b"\x00"
        body = struct.pack("!IIIIB c", self.doff, self.dlen, self.ulen,
                           self.cflag, self.typecd.encode()) + nb
        pad = (-len(body) - 4) % 16  # 16 字节对齐 (含 elen 4B)
        return struct.pack("!I", len(body) + pad) + body + b"\x00" * pad


@dataclass
class CArchive:
    """完整的 PyInstaller CArchive。"""
    pkgstart: int                                # PE 之后的归档起点
    pyver: int                                   # Python 主版本号 (e.g. 313)
    pylib: bytes                                 # cookie 中的 64B pylib 名
    entries: List[Entry] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: str) -> "CArchive":
        data = open(path, "rb").read()
        pos = data.rfind(MAGIC)
        if pos < 0:
            raise ValueError(f"未找到 PyInstaller cookie magic：{path} 不是单文件 exe？")
        cookie = data[pos:pos + COOKIE_LEN]
        magic, lengthofPackage, tocOff, tocLen, pyver = struct.unpack(
            "!8sIIII", cookie[:24])
        if magic != MAGIC:
            raise ValueError("cookie magic 不匹配")
        pkgstart = pos + COOKIE_LEN - lengthofPackage
        if pkgstart < 0:
            raise ValueError("lengthofPackage 异常")
        arch = cls(pkgstart=pkgstart, pyver=pyver,
                   pylib=cookie[24:COOKIE_LEN])
        # 解析 TOC
        toc = data[pkgstart + tocOff: pkgstart + tocOff + tocLen]
        i = 0
        while i < len(toc):
            (elen,) = struct.unpack("!I", toc[i:i + 4])
            e = toc[i + 4:i + elen]
            doff, dlen, ulen, cflag = struct.unpack("!IIIB", e[:13])
            typecd = chr(e[13])
            name = e[14:].rstrip(b"\x00").decode("utf-8", "replace")
            arch.entries.append(Entry(doff, dlen, ulen, cflag, typecd, name))
            i += elen
        arch._raw = data
        arch._data_prefix = data[pkgstart:pkgstart + min(
            (e.doff for e in arch.entries if e.dlen > 0), default=0)]
        return arch

    def find(self, name_substr: str) -> List[Entry]:
        return [e for e in self.entries if name_substr in e.name]

    def extract(self, name: str, dst_path: str) -> bytes:
        for e in self.entries:
            if e.name == name:
                blob = self._raw[self.pkgstart + e.doff:
                                 self.pkgstart + e.doff + e.dlen]
                raw = zlib.decompress(blob) if e.cflag else blob
                open(dst_path, "wb").write(raw)
                return raw
        raise KeyError(name)

    def replace_zlib(self, name: str, raw: bytes) -> int:
        """用 zlib 压缩后的数据替换指定条目；返回压缩后大小。
        注意：调用者需要按顺序重建归档数据区。
        """
        for e in self.entries:
            if e.name == name:
                comp = zlib.compress(raw, 9)
                e.cflag = 1
                e.ulen = len(raw)
                e.dlen = len(comp)
                return e.dlen
        raise KeyError(name)

    def remove(self, name: str) -> None:
        """删除某条目（仅从 TOC 移除；调用者负责跳过其数据）。"""
        self.entries = [e for e in self.entries if e.name != name]

    def rebuild(self) -> bytes:
        """按当前 entries 顺序重建归档段；保留原 PE 与数据前缀不变。"""
        cur = len(self._data_prefix)
        blobs: List[bytes] = []
        new_entries: List[Entry] = []
        for e in self.entries:
            if e.dlen == 0 and e.name == "pyi-contents-directory _internal":
                new_entries.append(Entry(cur, 0, 0, 0, "o",
                                         "pyi-contents-directory _internal"))
                continue
            if e.cflag and e.ulen > 0:
                # 压缩数据需要重新生成（替换过内容）或沿用原始压缩流
                # 此处假设 dlen 对应 _raw 中的 zlib 流；如果替换过请确保已写入
                blob = self._raw[self.pkgstart + e.doff:
                                 self.pkgstart + e.doff + e.dlen]
                # 把压缩流取出供回填
                blobs.append(blob)
                new_entries.append(Entry(cur, len(blob), e.ulen, 1, e.typecd, e.name))
                cur += len(blob)
            else:
                blob = self._raw[self.pkgstart + e.doff:
                                 self.pkgstart + e.doff + e.dlen]
                blobs.append(blob)
                new_entries.append(Entry(cur, len(blob), e.ulen, e.cflag,
                                         e.typecd, e.name))
                cur += len(blob)
        toc_bytes = b"".join(e.to_raw() for e in new_entries)
        toc_off = cur
        toc_len = len(toc_bytes)
        pkglen = toc_off + toc_len + COOKIE_LEN
        cookie = struct.pack("!8sIIII", MAGIC, pkglen, toc_off, toc_len,
                             self.pyver) + self.pylib
        assert len(cookie) == COOKIE_LEN
        return (self._raw[:self.pkgstart] + self._data_prefix
                + b"".join(blobs) + toc_bytes + cookie)

    def rebuild_with_blobs(self, blobs: List[bytes]) -> bytes:
        """高级接口：调用方提供按 TOC 顺序的数据 blobs（已压缩/未压缩均可）。"""
        cur = len(self._data_prefix)
        new_entries: List[Entry] = []
        i = 0
        for e in self.entries:
            if e.dlen == 0 and e.name == "pyi-contents-directory _internal":
                new_entries.append(Entry(cur, 0, 0, 0, "o",
                                         "pyi-contents-directory _internal"))
                continue
            blob = blobs[i]
            i += 1
            new_entries.append(Entry(cur, len(blob), e.ulen, e.cflag,
                                     e.typecd, e.name))
            cur += len(blob)
        toc_bytes = b"".join(e.to_raw() for e in new_entries)
        toc_off = cur
        toc_len = len(toc_bytes)
        pkglen = toc_off + toc_len + COOKIE_LEN
        cookie = struct.pack("!8sIIII", MAGIC, pkglen, toc_off, toc_len,
                             self.pyver) + self.pylib
        assert len(cookie) == COOKIE_LEN
        return (self._raw[:self.pkgstart] + self._data_prefix
                + b"".join(blobs) + toc_bytes + cookie)