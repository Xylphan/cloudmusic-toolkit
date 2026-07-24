import re
import json
import base64
import hashlib
from pathlib import Path
from typing import Any

import requests
from Crypto.Cipher import AES
from Crypto.Util import Padding
from mutagen import mp3, flac, id3

KEY = bytes.fromhex('2331346C6A6B5F215C5D2630553C2728')


# 分析音乐文件格式与元数据
def analyze(path: Path, easy: bool = True) -> tuple[Any, str]:
    if path.suffix == '.flac':
        return flac.FLAC(path), 'flac'
    else:
        return (mp3.EasyMP3(path) if easy else mp3.MP3(path)), 'mp3'


# 读取音频文件注释
def extract(path: Path, codec: str, meta: Any = None) -> list[str]:
    if codec == 'flac':
        handle = meta if meta else flac.FLAC(path)
        desc = handle.get('description', [])
        assert desc
        return desc
    else:
        handle = meta if meta else mp3.MP3(path)
        if handle.tags is None:
            return []
        return [text for tag in handle.tags.getall('COMM') for text in tag.text if not tag.desc]


# 从注释解密元数据
def decrypt(comment: str) -> dict[str, Any]:
    b64 = comment[22:]
    raw = base64.b64decode(b64 + '=' * (-len(b64) % 4))
    plain = Padding.unpad(AES.new(KEY, AES.MODE_ECB).decrypt(raw), 16)
    return json.loads(plain.decode('utf8')[6:])


# 写入注释
def write(meta: Any, codec: str, comment: str) -> None:
    if codec == 'flac':
        meta['description'] = comment
        meta.save()
    else:
        meta.tags.RegisterTextKey('comment', 'COMM')
        meta['comment'] = comment
        meta.save(v2_version=3)


# 构建加密注释
def _build_comment(track: dict[str, Any], codec: str, meta: Any, file_path: Path) -> str:
    album = track['album']
    data = {
        'album': album['name'],
        'albumId': album['id'],
        'albumPic': album['picUrl'],
        'albumPicDocId': str(album['picId']),
        'alias': track['alias'],
        'artist': [[artist['name'], artist['id']] for artist in track['artists']],
        'musicId': track['id'],
        'musicName': track['name'],
        'mvId': track['mvid'],
        'transNames': [],
        'format': codec,
        'bitrate': getattr(meta.info, 'bitrate', 0),
        'duration': int(meta.info.length * 1000),
        'mp3DocId': hashlib.md5(file_path.read_bytes()).hexdigest(),
    }
    cryptor = AES.new(KEY, AES.MODE_ECB)
    key = 'music:' + json.dumps(data)
    key = cryptor.encrypt(Padding.pad(key.encode('utf8'), 16))
    return '163 key(Don\'t modify):' + base64.b64encode(key).decode('utf8')


# 下载并嵌入专辑封面
def _embed_cover(file_path: Path, codec: str, cover_url: str, meta: Any = None) -> None:
    def _embed(item: Any, content: bytes, img_type: int) -> None:
        item.encoding = 0
        item.type = img_type
        item.mime = 'image/png' if content[:4] == bytes.fromhex('89504E47') else 'image/jpeg'
        item.data = content

    cover = requests.get(cover_url + '?param=300y300', timeout=3).content
    if codec == 'flac':
        flac_meta = meta if meta else flac.FLAC(file_path)
        image = flac.Picture()
        _embed(image, cover, 3)
        flac_meta.clear_pictures()
        flac_meta.add_picture(image)
        flac_meta.save()
    else:
        mp3_meta = meta if meta else mp3.MP3(file_path)
        if mp3_meta.tags is None:
            return
        image = id3.APIC()
        _embed(image, cover, 6)
        mp3_meta.tags.add(image)
        mp3_meta.save(v2_version=3)


# 生成标记并写入文件
def mark(file_path: Path, track: dict[str, Any], meta: Any = None) -> None:
    handle, codec = meta if meta else analyze(file_path)
    comment = _build_comment(track, codec, handle, file_path)

    handle['title'] = track['name']
    handle['album'] = track['album']['name']
    handle['artist'] = '/'.join(artist['name'] for artist in track['artists'])
    handle['tracknumber'] = str(track['position'])

    write(handle, codec, comment)
    _embed_cover(file_path, codec, track['album']['picUrl'], handle)


# 从链接获得元数据
def fetch(uri: str) -> dict[str, Any] | None:
    """注：对于已经"消失"的曲目（无歌曲链接）：
    若曾分享单曲到动态，可从用户的动态中提取信息
    若曲目消失而专辑未下架，可用专辑信息重建数据，再填充歌曲ID
    若曾下载过相同专辑的其他歌曲，可拷贝已有文件的标记，再填充歌曲ID
    （2/3情况下默认同专辑歌手一致，歌名将从ID3的tag"title"中读取，请预先设置）
    """
    from .config import USER_AGENT

    headers = {
        'X-Real-IP': '211.161.244.70',
        'User-Agent': USER_AGENT,
    }
    if 'event' in uri:
        match = re.search(r'[?&]id=(\d+)', uri)
        assert match
        mid = match.group(1)
        match = re.search(r'[?&]uid=(\d+)', uri)
        assert match
        uid = match.group(1)
        response = requests.get('https://music.163.com/event', params={'id': mid, 'uid': uid}, headers=headers, timeout=3)
        match = re.search(r'<textarea.+id="event-data".*>([\s\S]+?)</textarea>', response.text)
        assert match
        data = match.group(1)
        data = json.loads(data.replace('"', '"'))
        data = json.loads(data['json'])
        if 'song' in data:
            return data['song']
        elif 'resource' in data:
            return json.loads(data['resource']['resourceInfo'])
        elif 'event' in data:
            data = json.loads(data['event']['json'])
            if 'song' in data:
                return data['song']
            elif 'resource' in data:
                return json.loads(data['resource']['resourceInfo'])
    elif 'album' in uri:
        match = re.search(r'[?&]id=(\d+)', uri)
        assert match
        mid = match.group(1)
        response = requests.get('https://music.163.com/api/album/' + mid, headers=headers, timeout=3)
        data = json.loads(response.text)
        return {'album': data['album'], 'artists': data['album']['artists']}
    elif 'song' in uri:
        match = re.search(r'[?&]id=(\d+)', uri)
        assert match
        mid = match.group(1)
        response = requests.get('https://music.163.com/api/song/detail?ids=[' + mid + ']', headers=headers, timeout=3)
        data = json.loads(response.text)
        return data['songs'][0]
