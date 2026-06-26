import json
import sqlite3

from .config import DB


def metadata(path) -> list:
    playlists = {f.name for f in path.iterdir() if f.is_dir()}

    with sqlite3.connect(DB) as conn:
        trackdict = {}
        for (row,) in conn.execute("SELECT jsonStr FROM dbTrack"):
            track = json.loads(row)
            trackdict[int(track['id'])] = {
                'name': track['name'],
                'id': int(track['id']),
                'position': track['position'],
                'artists': track['artists'],
                'album': track['album'],
                'alias': track['alias'],
                'mvid': track['mvid'] or 0,
            }

        playdict = {}
        for (row,) in conn.execute("SELECT jsonStr FROM persistentModel WHERE jsonStr LIKE '%hostResource%'"):
            for playlist in json.loads(row)['data']['createPlaylist']:
                if playlist['name'] in playlists:
                    playdict[playlist['id']] = playlist['name']

        metalist = []
        for pid, raw in conn.execute("SELECT id, jsonStr FROM playlistTrackIds"):
            name = playdict.get(pid)
            if not name:
                continue
            metalist.append({
                'name': name,
                'tracks': [trackdict[int(item['id'])] for item in json.loads(raw)['trackIds']],
            })
    return metalist


def bitrate() -> tuple:
    with sqlite3.connect(DB) as conn:
        maxBr = {}
        for (row,) in conn.execute("SELECT jsonStr FROM dbTrack"):
            track = json.loads(row)
            maxBr[int(track['id'])] = track['privilege']['maxDownBr']

        offlineBr = {}
        for (row,) in conn.execute("SELECT jsonStr FROM offlineTrack"):
            data = json.loads(row)
            trackId = int(data['trackId'])
            offlineBr[trackId] = {
                'bitrate': data['bitrate'],
                'path': data['newRelativePath'].replace('\\', '/'),
            }
    return offlineBr, maxBr