#!/usr/bin/env python3
"""Build deterministic source archives; --ui-dir optionally supplies index.html/extension.js."""

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile


def build(ui_dir=None):
    root = Path(__file__).resolve().parent
    ui_dir = ui_dir or root.parent
    files = [("server.py", root / "server.py", 0o755)]
    if ui_dir:
        files.extend((name, ui_dir / name, 0o644) for name in ("extension.js", "index.html"))
    output = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0, compresslevel=9) as compressed:
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            for name, path, mode in files:
                content = path.read_bytes()
                info = tarfile.TarInfo(name)
                info.size = len(content)
                info.mode = mode
                archive.addfile(info, io.BytesIO(content))
    content = output.getvalue()
    manifest_path = root.parent / "canvas-extension.json"
    manifest = json.loads(manifest_path.read_text())
    for architecture in ("amd64", "arm64"):
        target = root / ("linux-" + architecture + ".tar.gz")
        target.write_bytes(content)
        digest = hashlib.sha256(content).hexdigest()
        manifest["backend"]["artifacts"]["linux-" + architecture]["sha256"] = digest
        print(digest, target.name)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ui-dir", type=Path)
    build(parser.parse_args().ui_dir)
