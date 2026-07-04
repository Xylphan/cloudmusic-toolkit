import os
from configparser import ConfigParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path(os.path.expandvars(r'%LOCALAPPDATA%\Netease\CloudMusic\Library\webdb.dat'))

_parser = ConfigParser()
_env_path = ROOT / '.env'
if not _parser.read(_env_path):
    raise FileNotFoundError('未找到 .env')
_config = _parser['DEFAULT']

PATH = Path(_config['PATH'])
USER_AGENT = _config['USER_AGENT']
SYNC_PATH = Path(_config['SYNC_PATH'])
