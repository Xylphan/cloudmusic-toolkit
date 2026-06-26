import os
from configparser import ConfigParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = os.path.expandvars(r'%LOCALAPPDATA%\Netease\CloudMusic\Library\webdb.dat')

_parser = ConfigParser()
_parser.read(ROOT / '.env')
_config = _parser['DEFAULT']

PATH = _config['PATH']
USER_AGENT = _config['USER_AGENT']
SYNC_PATH = _config['SYNC_PATH']
