import subprocess
from pathlib import Path
from os import utime
from shutil import copy2

from .config import SYNC_PATH
from .utils import analyze, extract, write


def sync(path):
    if subprocess.run(['ffmpeg', '-version'], capture_output=True).returncode != 0:
        raise RuntimeError('未找到 ffmpeg')

    def scan(dir):
        flac = {}
        mp3 = {}
        others = {}
        for file in (file for file in dir.rglob('*/*') if file.is_file()):
            if file.suffix == '.flac':
                flac[file.relative_to(dir).with_suffix('')] = file.stat().st_mtime
            elif file.suffix == '.mp3':
                mp3[file.relative_to(dir).with_suffix('')] = file.stat().st_mtime
            else:
                others[file.relative_to(dir)] = file.stat().st_mtime
        return flac, mp3, others

    def remove(set, suffix):
        for key in set:
            print(f'移除 {key}')
            (dest_dir / key.parent / (key.name + suffix)).unlink(missing_ok=True)

    def copy(set, suffix):
        for key in set:
            src = src_dir / key.parent / (key.name + suffix)
            dest = dest_dir / key.parent / (key.name + suffix)
            dest.parent.mkdir(parents=True, exist_ok=True)
            print(f'复制 {key}')
            copy2(src, dest)

    def convert(set):
        for key in set:
            src = src_dir / key.parent / (key.name + '.flac')
            dest = dest_dir / key.parent / (key.name + '.mp3')
            dest.parent.mkdir(parents=True, exist_ok=True)
            print(f'转换 {key}')
            subprocess.run(
                ['ffmpeg', '-i', str(src), '-ab', '320k', '-y', str(dest)],
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
            )
            write(*analyze(dest), extract(*analyze(src)))
            utime(dest, (src_flac[key], src_flac[key]))

    def cleanup():
        for item in sorted(dest_dir.rglob('*'), key=lambda p: len(p.parts), reverse=True):
            if item.is_dir() and item != omit_folder and not any(item.iterdir()):
                item.rmdir()

    src_dir = path
    dest_dir = Path(SYNC_PATH)
    omit_folder = dest_dir / '.stfolder'
    src_flac, src_mp3, src_others = scan(src_dir)
    dest_flac, dest_mp3, dest_others = scan(dest_dir)
    remove(dest_mp3.keys() - src_flac.keys() - src_mp3.keys(), '.mp3')
    remove(dest_others.keys() - src_others.keys(), '')
    copy({key for key in src_mp3.keys() & dest_mp3.keys() if src_mp3[key] > dest_mp3[key]}, '.mp3')
    copy({key for key in src_others.keys() & dest_others.keys() if src_others[key] > dest_others[key]}, '')
    copy(src_mp3.keys() - dest_mp3.keys(), '.mp3')
    copy(src_others.keys() - dest_others.keys(), '')
    convert({key for key in src_flac.keys() & dest_mp3.keys() if src_flac[key] > dest_mp3[key]})
    convert(src_flac.keys() - dest_mp3.keys())
    cleanup()
