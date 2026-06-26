from .database import bitrate


def check(path):
    offlineBr, maxBr = bitrate()
    upgrade = []
    ignore_file = path / 'ignore.txt'
    ignore = ignore_file.read_text(encoding='utf-8').splitlines() if ignore_file.is_file() else []
    for tid, info in offlineBr.items():
        if info['bitrate'] < maxBr.get(tid, 0):
            p = path / info['path']
            if p.stem in ignore or not p.is_file():
                continue
            print(p.stem)
            upgrade.append(p)

    if upgrade and input('\n直接删除？(y/[n])') in ['y', 'Y']:
        for f in upgrade:
            f.unlink()
