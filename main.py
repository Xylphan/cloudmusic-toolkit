import argparse
from pathlib import Path

from src.config import PATH
from src.arrange import arrange
from src.check import check
from src.sync import sync


def main():
    parser = argparse.ArgumentParser(description='网易云音乐本地文件管理工具')
    sub = parser.add_subparsers(dest='command', required=True)

    sub.add_parser('arrange', help='解析本地数据库歌单元数据，写入 ID3/FLAC 标签，按歌单分目录整理')
    sub.add_parser('check', help='对比已下载文件码率与可下载最高码率，列出可升级曲目')
    sub.add_parser('sync', help='同步音乐目录，将 FLAC 转码为 320k MP3')

    args = parser.parse_args()
    path = Path(PATH)

    if args.command == 'arrange':
        arrange(path)
    elif args.command == 'check':
        check(path)
    elif args.command == 'sync':
        sync(path)


if __name__ == '__main__':
    main()
