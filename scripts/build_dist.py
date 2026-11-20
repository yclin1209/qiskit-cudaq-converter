"""產生 Colab 離線上傳用 zip 套件。"""

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def build(output_dir: Path) -> Path:
    root = Path(__file__).resolve().parents[1]
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / "qcconvert_colab.zip"
    with ZipFile(archive, "w", ZIP_DEFLATED) as target:
        for source in sorted((root / "src" / "qcconvert").glob("*.py")):
            target.write(source, f"qcconvert/{source.name}")
        for name in ("qcconvert_demo.ipynb", "README_colab.md"):
            target.write(root / "colab" / name, name)
    return archive


def main() -> None:
    parser = argparse.ArgumentParser(description="建立 Colab zip")
    parser.add_argument("output_dir", nargs="?", type=Path, default=Path("dist"))
    print(build(parser.parse_args().output_dir))


if __name__ == "__main__":
    main()
