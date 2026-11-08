"""Validate bundled renderers; keep the legacy script entry point usable."""

from pathlib import Path
import argparse


HERE = Path(__file__).resolve().parent
CORE_DIR = HERE / "core"
CORE_FILES = ("img2ascii.py", "bgmaker.py")


def main():
    for name in CORE_FILES:
        target = CORE_DIR / name
        if not target.is_file():
            raise FileNotFoundError(f"Missing bundled renderer: {target}")
        print(f"Verified bundled renderer: {target}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="检查本仓库 core/ 文件；保留旧调用兼容")
    parser.parse_args()
    main()
