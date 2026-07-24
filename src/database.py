import json
import sqlite3
from pathlib import Path
from typing import Any

from src.config import DB


# 从网易云本地数据库读取曲目元数据和歌单映射
def metadata(path: Path) -> list[dict[str, Any]]:
    playlists = {entry.name for entry in path.iterdir() if entry.is_dir()}

    with sqlite3.connect(DB) as conn:
        trackdict: dict[int, dict[str, Any]] = {}
        for (row,) in conn.execute("SELECT jsonStr FROM dbTrack"):
            track = json.loads(row)
            trackId = int(track['id'])
            trackdict[trackId] = {
                'name': track['name'],
                'id': trackId,
                'position': track['position'],
                'artists': track['artists'],
                'album': track['album'],
                'alias': track['alias'],
                'mvid': track['mvid'] or 0,
            }

        playdict: dict[int, str] = {}
        for (row,) in conn.execute("SELECT jsonStr FROM persistentModel WHERE jsonStr LIKE '%hostResource%'"):
            for playlist in json.loads(row)['data']['createPlaylist']:
                if playlist['name'] in playlists:
                    playdict[playlist['id']] = playlist['name']

        metalist: list[dict[str, Any]] = []
        for pid, raw in conn.execute("SELECT id, jsonStr FROM playlistTrackIds"):
            if not (name := playdict.get(pid)):
                continue
            tracks = []
            for item in json.loads(raw)['trackIds']:
                if track := trackdict.get(int(item['id'])):
                    tracks.append(track)
            metalist.append({'name': name, 'tracks': tracks})
    return metalist


# 读取离线曲目实际比特率与最高可用比特率
def bitrate() -> tuple[dict[int, dict[str, Any]], dict[int, int]]:
    with sqlite3.connect(DB) as conn:
        maxBr: dict[int, int] = {}
        for (row,) in conn.execute("SELECT jsonStr FROM dbTrack"):
            track = json.loads(row)
            maxBr[int(track['id'])] = track['privilege']['maxDownBr']

        offlineBr: dict[int, dict[str, Any]] = {}
        for (row,) in conn.execute("SELECT jsonStr FROM offlineTrack"):
            data = json.loads(row)
            trackId = int(data['trackId'])
            offlineBr[trackId] = {
                'bitrate': data['bitrate'],
                'path': data['newRelativePath'].replace('\\', '/'),
            }
    return offlineBr, maxBr
