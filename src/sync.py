import subprocess
from os import utime
from shutil import copy2

from .config import PATH, SYNC_PATH
from .utils import analyze, extract, write


# 扫描目录文件时间戳
def _scan_dir(target: str) -> tuple[dict, dict, dict]:
    directory = PATH if target == 'src' else SYNC_PATH
    flac = {}
    mp3 = {}
    others = {}
    for file in (file for file in directory.rglob('*/*') if file.is_file()):
        rel = file.relative_to(directory)
        mtime = file.stat().st_mtime
        if file.suffix == '.flac':
            flac[rel.with_suffix('')] = mtime
        elif file.suffix == '.mp3':
            mp3[rel.with_suffix('')] = mtime
        else:
            others[rel] = mtime
    return flac, mp3, others


# 删除目标目录中多余的项
def _remove_stale(keys: set, suffix: str) -> None:
    for key in keys:
        print(f'移除 {key}')
        (SYNC_PATH / key.with_name(key.name + suffix)).unlink(missing_ok=True)


# 从源目录复制/覆盖文件到目标目录
def _copy_files(keys: set, suffix: str) -> None:
    for key in keys:
        src = PATH / key.with_name(key.name + suffix)
        dest = SYNC_PATH / key.with_name(key.name + suffix)
        dest.parent.mkdir(parents=True, exist_ok=True)
        print(f'复制 {key}')
        copy2(src, dest)


# FLAC 转 MP3，继承源文件时间戳和元数据
def _convert_flac(keys: set, src_flac: dict) -> None:
    for key in keys:
        dest = SYNC_PATH / key.with_name(key.name + '.mp3')
        dest.parent.mkdir(parents=True, exist_ok=True)
        flac_path = PATH / key.with_name(key.name + '.flac')
        print(f'转换 {key}')
        subprocess.run(
            ['ffmpeg', '-i', str(flac_path), '-ab', '320k', '-y', str(dest)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        src_meta, codec = analyze(flac_path)
        comments = extract(flac_path, codec, src_meta)
        dest_meta, _ = analyze(dest)
        write(dest_meta, 'mp3', comments[0] if comments else '')
        utime(dest, (src_flac[key], src_flac[key]))


# 清理目标目录中的空文件夹
def _cleanup_dirs() -> None:
    omit = SYNC_PATH / '.stfolder'
    for folder in SYNC_PATH.rglob('*'):
        if folder.is_dir() and folder != omit and not any(folder.iterdir()):
            folder.rmdir()


# 增量同步 MP3
def sync() -> None:
    src_flac, src_mp3, src_others = _scan_dir('src')
    _, dest_mp3, dest_others = _scan_dir('dest')

    _remove_stale(dest_mp3.keys() - src_flac.keys() - src_mp3.keys(), '.mp3')
    _remove_stale(dest_others.keys() - src_others.keys(), '')
    _copy_files({key for key in src_mp3.keys() & dest_mp3.keys() if src_mp3[key] > dest_mp3[key]}, '.mp3')
    _copy_files({key for key in src_others.keys() & dest_others.keys() if src_others[key] > dest_others[key]}, '')
    _copy_files(src_mp3.keys() - dest_mp3.keys(), '.mp3')
    _copy_files(src_others.keys() - dest_others.keys(), '')
    _convert_flac({key for key in src_flac.keys() & dest_mp3.keys() if src_flac[key] > dest_mp3[key]}, src_flac)
    _convert_flac(src_flac.keys() - dest_mp3.keys(), src_flac)
    _cleanup_dirs()
