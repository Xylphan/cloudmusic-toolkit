import ctypes
from pathlib import Path
from shutil import move, rmtree
from typing import Any

from src.config import ROOT
from src.database import metadata
from src.utils import analyze, decrypt, extract, mark


# 构建查找表
def _build_table(
    result: list[dict[str, Any]],
) -> tuple[dict, dict]:
    playdict = {}
    trackmap = {}
    for playlist in result:
        for track in playlist['tracks']:
            playdict[
                (
                    track['name'],
                    '/'.join(artist['name'] for artist in track['artists']),
                    track['album']['name'],
                    str(track['position']),
                )
            ] = (
                track,
                playlist['name'],
            )
            trackmap[track['id']] = (track, playlist['name'])
    return playdict, trackmap


# 扫描并解密音频文件
def _collect_files(path: Path) -> list[Path]:
    files = [f for f in path.iterdir() if f.is_file() and f.suffix in ('.mp3', '.flac')]

    vip = path / 'VipSongsDownload'
    if vip.is_dir():
        dll_path = ROOT / 'bin' / 'libncmdump.dll'
        if not dll_path.is_file():
            raise FileNotFoundError('未找到 bin/libncmdump.dll')
        dll = ctypes.CDLL(str(dll_path))
        dll.CreateNeteaseCrypt.argtypes = [ctypes.c_char_p]
        dll.CreateNeteaseCrypt.restype = ctypes.c_void_p
        dll.Dump.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        dll.Dump.restype = ctypes.c_int
        dll.FixMetadata.argtypes = [ctypes.c_void_p]
        dll.DestroyNeteaseCrypt.argtypes = [ctypes.c_void_p]

        for f in vip.glob('*.ncm'):
            crypt = dll.CreateNeteaseCrypt(str(f).encode())
            ok = dll.Dump(crypt, str(vip).encode()) == 0
            if ok:
                dll.FixMetadata(crypt)
            dll.DestroyNeteaseCrypt(crypt)
            if ok:
                f.unlink()

        files += [f for f in vip.iterdir() if f.suffix in ('.mp3', '.flac')]

    return files


# 匹配文件元数据并归类
def _match_file(file: Path, playdict: dict, trackmap: dict, base: Path) -> str | None:
    meta, codec = analyze(file, easy=False)
    comments = extract(file, codec, meta)

    if comment := next((c for c in comments if c.startswith("163 key(Don't modify):")), None):
        decrypted = decrypt(comment)
        data = trackmap.get(int(decrypted['musicId']))
    else:
        key = (
            (meta.get('title') or [''])[0],
            '/'.join(meta.get('artist') or []),
            (meta.get('album') or [''])[0],
            (meta.get('tracknumber') or [''])[0],
        )
        data = playdict.get(key)

    if not data:
        return file.stem

    track, folder = data
    if not comment:
        mark(file, track)

    (base / folder).mkdir(exist_ok=True)
    move(file, base / folder / file.name)
    print(file.stem)
    return None


# 解析元数据并按目录归类
def arrange(path: Path) -> None:
    playdict, trackmap = _build_table(metadata(path))
    files = _collect_files(path)

    failed: list[str] = []
    for f in files:
        if stem := _match_file(f, playdict, trackmap, path):
            failed.append(stem)

    vip = path / 'VipSongsDownload'
    rmtree(vip, ignore_errors=True)
    for f in path.glob('*.lrc'):
        f.unlink()
    if failed:
        print(f'\033[31m{"\n".join(failed)}\033[0m')
