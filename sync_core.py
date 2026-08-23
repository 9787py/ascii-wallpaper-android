"""Copy the shared renderer into the self-contained Buildozer source tree."""

from pathlib import Path
import shutil


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent
DESTINATION = HERE / "core"
CORE_FILES = ("img2ascii.py", "bgmaker.py")


def main():
    DESTINATION.mkdir(exist_ok=True)
    for name in CORE_FILES:
        source = SOURCE / name
        if not source.exists():
            raise FileNotFoundError(source)
        target = DESTINATION / name
        shutil.copy2(source, target)
        print(f"Synced {source} -> {target}")


if __name__ == "__main__":
    main()
