"""Copy the shared renderer into the self-contained Buildozer source tree."""

from pathlib import Path
import shutil
import hashlib
import argparse


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent
DESTINATION = HERE / "core"
CORE_FILES = ("img2ascii.py", "bgmaker.py")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(check=False):
    DESTINATION.mkdir(exist_ok=True)
    for name in CORE_FILES:
        source = SOURCE / name
        if not source.exists():
            raise FileNotFoundError(source)
        target = DESTINATION / name
        if check:
            if not target.exists() or digest(source) != digest(target):
                raise RuntimeError(f"Android 核心副本已过期：{name}；请运行 python sync_core.py")
            print(f"Verified {target}")
            continue
        shutil.copy2(source, target)
        if digest(source) != digest(target):
            raise RuntimeError(f"同步校验失败：{name}")
        print(f"Synced and verified {source} -> {target}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="只检查核心副本是否最新")
    main(parser.parse_args().check)
