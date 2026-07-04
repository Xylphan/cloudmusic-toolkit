import argparse

from src.config import PATH
from src.arrange import arrange
from src.check import check
from src.sync import sync

commands = {'arrange': arrange, 'check': check}


def main() -> None:
    parser = argparse.ArgumentParser(description='网易云音乐本地文件管理工具')
    sub = parser.add_subparsers(dest='command', required=True)

    for cmd in commands:
        sub.add_parser(cmd)
    sub.add_parser('sync')

    args = parser.parse_args()
    if args.command == 'sync':
        sync()
        return
    commands[args.command](PATH)


if __name__ == '__main__':
    main()
