import os
import sys


def get_app_dir() -> str:
    """設定ファイルなどの書き込み先ディレクトリを返す。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_resource_dir() -> str:
    """同梱リソースの参照先ディレクトリを返す。"""
    if hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return get_app_dir()


def ensure_config_dir() -> str:
    config_dir = os.path.join(get_app_dir(), "config")
    os.makedirs(config_dir, exist_ok=True)
    return config_dir
