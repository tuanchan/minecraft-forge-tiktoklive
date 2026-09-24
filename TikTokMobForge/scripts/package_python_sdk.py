"""Package the pure-Python SDK without long filesystem paths in the installer."""
from pathlib import Path
import sys
from zipfile import ZipFile, ZIP_DEFLATED

source, destination = map(Path, sys.argv[1:])
package = source / "elevenlabs"
if not package.is_dir():
    raise SystemExit("Missing elevenlabs package")
destination.mkdir(parents=True, exist_ok=True)
with ZipFile(destination / "elevenlabs.zip", "w", ZIP_DEFLATED) as archive:
    for path in package.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            if path.suffix.lower() in (".pyd", ".dll"):
                raise SystemExit("SDK contains native code and cannot be stored in zipimport")
            archive.write(path, path.relative_to(source).as_posix())
(destination / "elevenlabs-archive.pth").write_text("elevenlabs.zip\n", encoding="utf-8")
