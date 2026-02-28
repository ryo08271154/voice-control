import pkgutil
import subprocess
import sys

import plugins


def build(entry_script: str, name: str):
    hidden_imports = []
    for module_info in pkgutil.iter_modules(plugins.__path__):
        hidden_imports.extend(["--hidden-import", f"plugins.{module_info.name}"])

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--name",
        name,
        *hidden_imports,
        entry_script,
    ]
    print(" ".join(cmd))
    subprocess.check_call(cmd)


if __name__ == "__main__":
    # GUI版
    build("control.py", "voice-control-gui")
    # CUI版
    build("voice_control.py", "voice-control-cui")
    print("Build completed. dist/ 以下を配布してください。")
