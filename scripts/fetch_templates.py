#!/usr/bin/env python3
"""Install only the export templates a project's presets need, not Godot's whole template bundle.

    python3 fetch_templates.py VERSION CHANNEL PLATFORMS PRESETS_FILE DEST

The official .tpz holds every platform's templates (about 1.3 GB for Godot 4.7); a release export
of one platform needs one or two files from it. A zip keeps its file index at the end, so this
reads the index with HTTP range requests (through curl) and downloads only the entries the
presets named "Windows", "Linux", "Web" and "macOS" (the ones the action exports) will use, plus
version.txt, which the editor checks. Anything it cannot work out (no presets file, a preset
missing, an option it does not know, a custom template, a failed transfer) falls back to the
whole bundle, exactly as before, so no project ends up with a template missing.
"""
import io
import os
import shutil
import subprocess
import sys
import zipfile

CHUNK = 8 << 20
# The action's platform names, and the export preset each one exports.
PRESETS = {"windows": "Windows", "linux": "Linux", "web": "Web", "macos": "macOS"}


class RangeFile(io.RawIOBase):
    """A read-only, seekable view of a remote file, one curl range request per read."""

    def __init__(self, url: str) -> None:
        self.url = url
        head = subprocess.run(["curl", "-sSfLI", url], check=True, capture_output=True, text=True).stdout
        lengths = [line.split(":", 1)[1] for line in head.splitlines() if line.lower().startswith("content-length:")]
        self.size = int(lengths[-1])  # the last response, after the redirects
        self.pos = 0

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.pos

    def seek(self, offset: int, whence: int = 0) -> int:
        self.pos = offset if whence == 0 else self.pos + offset if whence == 1 else self.size + offset
        return self.pos

    def readinto(self, buffer) -> int:
        count = min(len(buffer), self.size - self.pos, CHUNK)
        if count <= 0:
            return 0
        data = subprocess.run(["curl", "-sSfL", "--retry", "5", "-r", f"{self.pos}-{self.pos + count - 1}", self.url],
                              check=True, capture_output=True).stdout
        buffer[:len(data)] = data
        self.pos += len(data)
        return len(data)


def _unescaped_quotes(text: str) -> int:
    count = 0
    i = 0
    while i < len(text):
        if text[i] == "\\":
            i += 2  # the escaped character, whatever it is
            continue
        count += text[i] == '"'
        i += 1
    return count


def read_presets(path: str) -> dict:
    """Preset name -> its options, from export_presets.cfg. Godot's own config format, not an INI:
    a quoted value may run over several lines (the SSH remote-deploy scripts do), so a value is
    read until its quotes balance."""
    sections = {}
    current = None
    key = value = None
    for line in open(path, encoding="utf-8"):
        if key is not None:  # inside a multi-line string
            value += line
        else:
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                current = sections.setdefault(stripped[1:-1], {})
                continue
            if "=" not in stripped or current is None:
                continue
            key, value = stripped.split("=", 1)
        if _unescaped_quotes(value) % 2 == 0:
            current[key] = value.strip().strip('"')
            key = value = None
    presets = {}
    for name, section in sections.items():
        if name.startswith("preset.") and name.count(".") == 1:
            presets[section.get("name", "")] = sections.get(name + ".options", {})
    return presets


def templates_for(platform: str, options: dict) -> list:
    """The release template files an export of [platform] with these preset options reads.
    None when that cannot be told (the caller then installs everything)."""
    if options.get("custom_template/release", ""):
        return []  # the preset brings its own template
    arch = options.get("binary_format/architecture")
    if platform == "windows":
        return [f"windows_release_{arch}.exe", f"windows_release_{arch}_console.exe"] if arch else None
    if platform == "linux":
        return [f"linux_release.{arch}"] if arch else None
    if platform == "macos":
        return ["macos.zip"]
    if platform == "web":
        extensions = options.get("variant/extensions_support")
        threads = options.get("variant/thread_support")
        if extensions is None or threads is None:
            return None
        return ["web_" + ("dlink_" if extensions == "true" else "") + ("" if threads == "true" else "nothreads_") + "release.zip"]
    return None


def install_everything(url: str, dest: str) -> None:
    print("Installing the whole template bundle.")
    subprocess.run(["curl", "-sSfL", "--retry", "5", "-o", "templates.tpz", url], check=True)
    shutil.rmtree("templates", ignore_errors=True)
    subprocess.run(["unzip", "-q", "templates.tpz"], check=True)
    os.remove("templates.tpz")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.rmtree(dest, ignore_errors=True)
    shutil.move("templates", dest)


def main() -> None:
    version, channel, platforms, presets_file, dest = sys.argv[1:6]
    url = (f"https://github.com/godotengine/godot-builds/releases/download/{version}-{channel}/"
           f"Godot_v{version}-{channel}_export_templates.tpz")
    try:
        presets = read_presets(presets_file) if os.path.exists(presets_file) else {}
        wanted = []
        for platform in [p.strip() for p in platforms.split(",") if p.strip()]:
            names = templates_for(platform, presets[PRESETS[platform]]) if PRESETS.get(platform) in presets else None
            if names is None:
                print(f"Cannot tell which templates the '{platform}' export needs.")
                install_everything(url, dest)
                return
            wanted += names
        archive = zipfile.ZipFile(io.BufferedReader(RangeFile(url), CHUNK))
        os.makedirs(dest, exist_ok=True)
        for name in ["version.txt", *wanted]:
            entry = f"templates/{name}"
            # The CRC is checked as the entry is read: a damaged transfer raises here.
            with archive.open(entry) as source, open(os.path.join(dest, name), "wb") as target:
                shutil.copyfileobj(source, target, CHUNK)
            print(f"{archive.getinfo(entry).file_size / 1e6:8.1f} MB  {name}")
    except Exception as error:  # noqa: BLE001 - whatever went wrong, the whole bundle still works
        print(f"Fetching single templates failed ({error!r}).")
        install_everything(url, dest)


if __name__ == "__main__":
    main()
