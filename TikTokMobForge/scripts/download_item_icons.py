"""Bundle version-matched inventory renders with pinned provenance, no runtime downloads."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from io import BytesIO
import hashlib
import json
import sys
import time
import urllib.request
import zipfile
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "web/assets/minecraft-inventory"
REPO = "TinyTank800/MinecraftAllImages"

def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "TikTokMobForge-AssetBuilder/1.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read()
        except OSError:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)

def main():
    jar = Path(sys.argv[1])
    commit = json.loads(fetch(f"https://api.github.com/repos/{REPO}/commits/main"))["sha"]
    base = f"https://raw.githubusercontent.com/{REPO}/{commit}"
    with zipfile.ZipFile(jar) as archive:
        ids = sorted({Path(name).stem for name in archive.namelist()
                      if name.startswith("assets/minecraft/items/") and name.endswith(".json")} - {"air"})
    # The gallery has component variants for these items. Their default inventory
    # silhouettes are represented explicitly, never fuzzy-matched to another ID.
    manifest = json.loads(fetch(base + "/public/images-v2/26.2/manifest.json"))
    tree = json.loads(fetch(f"https://api.github.com/repos/{REPO}/git/trees/{commit}?recursive=1"))
    prefix = "public/images-v2/26.2/"
    files = {entry["path"][len(prefix):]: entry["sha"] for entry in tree["tree"]
             if entry["path"].startswith(prefix) and entry["path"].endswith(".png")}
    if tree.get("truncated"):
        raise RuntimeError("Git tree truncated; cannot safely map assets")
    aliases = {}
    for item in ids:
        if item + ".png" in files:
            continue
        variants = sorted(name for name in files if name.startswith(item + "__"))
        if item in ("potion", "splash_potion", "lingering_potion"):
            variants = [name for name in variants if "water" in name] or variants
        if not variants:
            raise RuntimeError(f"Missing exact item/variant: {item}")
        aliases[item] = variants[0]
    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / "LICENSE-gallery.txt").write_bytes(fetch(base + "/LICENSE"))
    records = {}

    def download(item):
        filename = aliases.get(item, item + ".png")
        path = DEST / (item + ".png")
        content = path.read_bytes() if path.is_file() else b""
        blob = lambda data: hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        url = base + "/" + prefix + filename
        if blob(content) != files[filename]:
            content = fetch(url)
        if blob(content) != files[filename]:
            raise RuntimeError(f"Asset hash mismatch: {item}")
        with Image.open(BytesIO(content)) as image:
            image.load()
            if image.format != "PNG" or not image.convert("RGBA").getchannel("A").getbbox():
                raise RuntimeError(f"Empty or invalid item icon: {item}")
            dimensions = list(image.size)
        path.write_bytes(content)
        return item, {"source": url, "sha256": hashlib.sha256(content).hexdigest(), "size": dimensions}

    with ThreadPoolExecutor(max_workers=10) as pool:
        for index, future in enumerate(as_completed([pool.submit(download, item) for item in ids]), 1):
            item, record = future.result()
            records[item] = record
            if index % 100 == 0:
                print(f"Downloaded {index}/{len(ids)}", flush=True)
    (DEST / "manifest.json").write_text(json.dumps({
        "minecraft_version": "26.2", "repository": f"https://github.com/{REPO}",
        "commit": commit, "variant_representations": aliases, "items": dict(sorted(records.items()))
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Bundled {len(records)} inventory icons; {len(aliases)} explicit component-variant representations.", flush=True)

if __name__ == "__main__":
    main()
