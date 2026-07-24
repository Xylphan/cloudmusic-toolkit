from pathlib import Path

from src.database import bitrate


# 筛除低音质文件
def check(path: Path) -> None:
    offlineBr, maxBr = bitrate()
    upgrade: list[Path] = []
    ignore_file = path / 'ignore.txt'
    ignore = set(ignore_file.read_text(encoding='utf-8').splitlines()) if ignore_file.is_file() else set()
    for trackId, data in offlineBr.items():
        if data['bitrate'] < maxBr.get(trackId, 0):
            target = path / data['path']
            if target.stem in ignore or not target.is_file():
                continue
            print(target.stem)
            upgrade.append(target)

    if upgrade and input('\n直接删除？(Y/[N])').lower() == 'y':
        for f in upgrade:
            f.unlink()
