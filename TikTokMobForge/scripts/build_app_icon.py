"""Convert the supplied PNG to a multi-resolution Windows ICO for packaging."""
from pathlib import Path
from PIL import Image

root = Path(__file__).resolve().parents[1]
with Image.open(root / "web/assets/iconapp.png") as source:
    icon = source.convert("RGBA")
    icon.save(root / "Desktop/iconapp.ico", format="ICO",
              sizes=[(size, size) for size in (16, 24, 32, 48, 64, 128, 256)])
