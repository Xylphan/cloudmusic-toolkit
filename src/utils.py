import re, json, base64, hashlib, requests
from Crypto.Cipher import AES
from Crypto.Util import Padding
from mutagen import mp3, flac, id3

KEY = bytes.fromhex('2331346C6A6B5F215C5D2630553C2728')


# 分析音乐文件格式与元数据
def analyze(path, easy=True):
    if path.suffix == '.flac':
        meta = flac.FLAC(path)
        format = 'flac'
    else:
        meta = mp3.EasyMP3(path) if easy else mp3.MP3(path)
        format = 'mp3'
    return meta, format


# 从音频文件读取注释
def extract(meta, format):
    if format == 'flac':
        comment = meta.get('description', '')
    else:
        comment = [text for item in meta.tags.getall('COMM') for text in item.text]
    return comment


# 写入注释
def write(meta, format, comment):
    if format == 'flac':
        meta['description'] = comment
        meta.save()
    else:
        meta.tags.RegisterTextKey('comment', 'COMM')
        meta['comment'] = comment
        meta.save(v2_version=3)


# 以红色打印失败列表
def warn(failed):
    print(f'\033[31m{"\n".join(f'{name}' for name in failed)}\033[0m')


# 由元数据生成标记并写入文件
def mark(path, track):
    def embed(item, content, type):
        item.encoding = 0
        item.type = type
        item.mime = 'image/png' if content[:4] == bytes.fromhex('89504E47') else 'image/jpeg'
        item.data = content

    meta, format = analyze(path)
    album = track['album']
    data = {
        'album': album['name'],
        'albumId': album['id'],
        'albumPic': album['picUrl'],
        'albumPicDocId': str(album['picId']),
        'alias': track['alias'],
        'artist': [[a['name'], a['id']] for a in track['artists']],
        'musicId': track['id'],
        'musicName': track['name'],
        'mvId': track['mvid'],
        'transNames': [],
        'format': format,
        'bitrate': meta.info.bitrate,
        'duration': int(meta.info.length * 1000),
        'mp3DocId': hashlib.md5(path.read_bytes()).hexdigest(),
    }
    tracknumber = str(track['position'])

    cryptor = AES.new(KEY, AES.MODE_ECB)
    comment = 'music:' + json.dumps(data)
    comment = cryptor.encrypt(Padding.pad(comment.encode('utf8'), 16))
    comment = '163 key(Don\'t modify):' + base64.b64encode(comment).decode('utf8')

    meta['title'] = data['musicName']
    meta['album'] = data['album']
    meta['artist'] = '/'.join([artist[0] for artist in data['artist']])
    meta['tracknumber'] = tracknumber

    write(meta, format, comment)

    data = requests.get(data['albumPic'] + '?param=300y300').content
    if format == 'flac':
        meta = flac.FLAC(path)
        image = flac.Picture()
        embed(image, data, 3)
        meta.clear_pictures()
        meta.add_picture(image)
        meta.save()
    else:
        meta = mp3.MP3(path)
        image = id3.APIC()
        embed(image, data, 6)
        meta.tags.add(image)
        meta.save(v2_version=3)


# 从链接获得元数据
def fetch(uri):
    """
    注：对于已经"消失"的曲目（无歌曲链接）：
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
    if 'event' in uri:  # 从用户动态链接获取
        id = re.search(r'[?&]id=(\d+)', uri).group(1)
        uid = re.search(r'[?&]uid=(\d+)', uri).group(1)
        response = requests.get('https://music.163.com/event', params={'id': id, 'uid': uid}, headers=headers)
        data = re.search(r'<textarea.+id="event-data".*>([\s\S]+?)</textarea>', response.text).group(1)
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
    elif 'album' in uri:  # 从专辑链接获取
        id = re.search(r'[?&]id=(\d+)', uri).group(1)
        response = requests.get('https://music.163.com/api/album/' + id, headers=headers)
        data = json.loads(response.text)
        return {'album': data['album'], 'artists': data['album']['artists']}
    elif 'song' in uri:  # 从曲目链接获取
        id = re.search(r'[?&]id=(\d+)', uri).group(1)
        response = requests.get('https://music.163.com/api/song/detail?ids=[' + id + ']', headers=headers)
        data = json.loads(response.text)
        return data['songs'][0]
