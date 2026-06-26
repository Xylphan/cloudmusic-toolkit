import subprocess
from shutil import move, rmtree

from .config import ROOT
from .database import metadata
from .utils import analyze, mark, warn


def arrange(path):
    playdict = {}
    result = metadata(path)
    for playlist in result:
        for track in playlist['tracks']:
            playdict[(track['name'], '/'.join([artist['name'] for artist in track['artists']]))] = (track, playlist['name'])

    vip = path / 'VipSongsDownload'
    if vip.is_dir():
        ncmdump = ROOT / 'bin' / 'ncmdump.exe'
        for f in vip.glob('*.ncm'):
            subprocess.run([ncmdump, f])

    files = [f for f in path.iterdir() if f.is_file() and f.suffix in ('.mp3', '.flac')]
    if vip.is_dir():
        files += [f for f in vip.iterdir() if f.suffix in ('.mp3', '.flac')]

    failed = []
    for f in files:
        meta = analyze(f)[0]
        key = (meta['title'][0], '/'.join([artist for artist in meta['artist']]))
        data = playdict.get(key)
        if data:
            track, folder = data
            print(f'{f.stem}')
            mark(f, track)
            move(f, path / folder / f.name)
        else:
            failed.append(f.stem)

    rmtree(vip, ignore_errors=True)
    for f in path.glob('*.lrc'):
        f.unlink()
    if failed:
        warn(failed)
