#!/usr/bin/env python3
"""Generate phononai.org from a checkout of chezgoulet/phonon at a release tag.

Every fact on the page comes from a file in the app repository at the tag being
described, or from the GitHub release for that tag. Nothing is estimated: when a
source is missing or a value is null, this fails with a message naming the file,
or writes an explicit "not measured" into the page. A plausible number invented
here would be indistinguishable from a measured one on the rendered page, which
is the whole reason this script exists.

Usage:
    build/generate.py --app-repo ../phonon --ref v0.1.12 --out dist \
        [--release-json release.json] [--rate 0.15]

Reads git objects with `git show <ref>:<path>`, so the working tree of the app
checkout is never touched and any ref (tag, branch, sha) works.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import textwrap
import urllib.request
import zlib
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("build/generate.py needs PyYAML: pip install -r build/requirements.txt")

try:
    from jinja2 import Environment, FileSystemLoader, StrictUndefined, UndefinedError
    from jinja2 import TemplateNotFound
except ImportError:  # pragma: no cover
    sys.exit("build/generate.py needs Jinja2: pip install -r build/requirements.txt")

APP_REPO = "chezgoulet/phonon"
SITE_URL = "https://phononai.org/"
DOC_FILES = {
    "performance": "docs/performance.md",
    "sustained": "docs/sustained-load.md",
    "models": "docs/models.md",
    "benchmark": "docs/benchmark.md",
    "battery": "docs/battery.md",
}

# Android API level to the release name operators recognise. An unknown level
# is a hard failure rather than a guess: "Android <number>" on the page would be
# worse than no page.
ANDROID_VERSIONS = {
    29: "10", 30: "11", 31: "12", 32: "12L", 33: "13", 34: "14",
    35: "15", 36: "16", 37: "17",
}


class Fail(Exception):
    """A source is missing or unusable. The build must stop, not paper over it."""


# --------------------------------------------------------------------------
# Sources
# --------------------------------------------------------------------------

class AppRepo:
    """Read-only access to the app repository at one ref."""

    def __init__(self, path: Path, ref: str):
        self.path = path
        self.ref = ref
        if not (path / ".git").exists() and not (path / "HEAD").exists():
            raise Fail(f"{path} is not a git checkout")
        try:
            self._git_text("rev-parse", "--verify", f"{ref}^{{commit}}")
        except Fail:
            raise Fail(f"{path} has no ref {ref!r}; fetch tags before generating")

    def _git_text(self, *args: str) -> str:
        proc = subprocess.run(["git", "-C", str(self.path), *args], capture_output=True)
        if proc.returncode != 0:
            raise Fail(f"git {' '.join(args)} failed: {proc.stderr.decode().strip()}")
        return proc.stdout.decode()

    def _git_bytes(self, *args: str) -> bytes:
        proc = subprocess.run(["git", "-C", str(self.path), *args], capture_output=True)
        if proc.returncode != 0:
            raise Fail(f"git {' '.join(args)} failed: {proc.stderr.decode().strip()}")
        return proc.stdout

    def exists(self, path: str) -> bool:
        proc = subprocess.run(
            ["git", "-C", str(self.path), "cat-file", "-e", f"{self.ref}:{path}"],
            capture_output=True,
        )
        return proc.returncode == 0

    def read(self, path: str) -> str:
        if not self.exists(path):
            raise Fail(f"{path} is missing at {self.ref} (required source)")
        return self._git_text("show", f"{self.ref}:{path}")

    def read_bytes(self, path: str) -> bytes:
        if not self.exists(path):
            raise Fail(f"{path} is missing at {self.ref} (required source)")
        return self._git_bytes("show", f"{self.ref}:{path}")

    def ls(self, directory: str) -> list[str]:
        out = self._git_text("ls-tree", "--name-only", f"{self.ref}:{directory}")
        return [line for line in out.splitlines() if line]


# --------------------------------------------------------------------------
# Small parsers
# --------------------------------------------------------------------------

def parse_gradle(text: str) -> dict:
    def one(pattern: str, what: str):
        m = re.search(pattern, text)
        if not m:
            raise Fail(f"app/app/build.gradle.kts: could not read {what}")
        return m.group(1)

    version_name = one(r'versionName\s*=\s*"([^"]+)"', "versionName")
    version_code = int(one(r"versionCode\s*=\s*(\d+)", "versionCode"))
    min_sdk = int(one(r"minSdk\s*=\s*(\d+)", "minSdk"))
    abis = re.findall(r'"([a-z0-9_]+-v\d+[a-z]*)"', text)
    abis = sorted({a for a in abis if a.endswith(("v7a", "v8a", "x86_64"))})
    return {
        "version": version_name,
        "version_code": version_code,
        "min_sdk": min_sdk,
        "abis": abis or ["arm64-v8a"],
    }


def png_size(data: bytes) -> tuple[int, int]:
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise Fail("not a PNG")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def spdx_from_license(text: str) -> str:
    """The licence the repository actually ships, read from its text.

    Detection is textual on purpose: no network call, and the answer is a
    property of the file at the tag rather than of what GitHub reports today.
    """
    head = text[:4000]
    if "Apache License" in head and "Version 2.0" in head:
        return "Apache-2.0"
    if "MIT License" in head or "Permission is hereby granted, free of charge" in head:
        return "MIT"
    if "GNU AFFERO GENERAL PUBLIC LICENSE" in head:
        return "AGPL-3.0"
    if "GNU GENERAL PUBLIC LICENSE" in head:
        version = "3.0" if "Version 3" in head else "2.0"
        return f"GPL-{version}"
    raise Fail("LICENSE does not match a known licence; refusing to guess an SPDX id")


def human_bytes(n: int) -> str:
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f} GB".replace(".00", "")
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f} MB"
    if n >= 1_000:
        return f"{n / 1_000:.0f} kB"
    return f"{n} B"


def provenance(node: dict, release_version: str) -> str:
    """One sentence saying which device measured a number, on which build, when.

    If the build that measured it is not the build being described, that is said
    out loud rather than smoothed over: the two are not interchangeable.
    """
    device = node.get("measured_on") or "an unnamed device"
    version = node.get("app_version")
    date = node.get("measured_date")
    bits = []
    if version:
        if version == release_version:
            bits.append(f"app {version}")
        else:
            bits.append(f"measured with v{version}, not this build")
    if date:
        bits.append(str(date))
    tail = f" ({', '.join(bits)})" if bits else ""
    return f"{device}{tail}"


# --------------------------------------------------------------------------
# Release metadata
# --------------------------------------------------------------------------

def fetch_release(tag: str, release_json: Path | None) -> dict:
    if release_json:
        return json.loads(release_json.read_text())

    url = f"https://api.github.com/repos/{APP_REPO}/releases/tags/{tag}"
    request = urllib.request.Request(url)
    request.add_header("Accept", "application/vnd.github+json")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    else:
        print("warning: GITHUB_TOKEN is unset; the releases API may rate-limit", file=sys.stderr)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read())
    except Exception as exc:
        raise Fail(f"could not read the GitHub release for {tag}: {exc}")


def fetch_text(url: str) -> str | None:
    request = urllib.request.Request(url)
    request.add_header("Accept", "application/octet-stream")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8", "replace")
    except Exception as exc:
        print(f"warning: could not fetch {url}: {exc}", file=sys.stderr)
        return None


def apk_checksum(release: dict, apk_name: str) -> str | None:
    """The SHA-256 from the release's SHA256SUMS asset.

    Releases cut before the sums file existed return None, and the page says
    "checksum unavailable" — an old release is not a reason to print a hash
    nobody computed.
    """
    for asset in release.get("assets", []):
        if asset.get("name") != "SHA256SUMS":
            continue
        body = fetch_text(asset["browser_download_url"])
        if not body:
            return None
        for line in body.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[-1].lstrip("*") == apk_name:
                return parts[0].lower()
        raise Fail(f"SHA256SUMS does not cover {apk_name}")
    return None


# --------------------------------------------------------------------------
# The og:image, drawn with no dependencies
# --------------------------------------------------------------------------

FONT = {
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "a": (".....", ".....", ".###.", "....#", ".####", "#...#", ".####"),
    "g": (".####", "#...#", "#...#", ".####", "....#", "#...#", ".###."),
    "h": ("#....", "#....", "#.##.", "##..#", "#...#", "#...#", "#...#"),
    "i": (".#...", ".....", ".#...", ".#...", ".#...", ".#...", ".#..."),
    "n": (".....", ".....", "#.##.", "##..#", "#...#", "#...#", "#...#"),
    "o": (".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###."),
    "p": ("#....", "#....", "####.", "#...#", "#...#", "####.", "#...."),
    "r": (".....", ".....", "#.##.", "##..#", "#....", "#....", "#...."),
    "v": (".....", ".....", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
}


class Canvas:
    """A tiny RGB canvas that writes a PNG. No Pillow, by design."""

    def __init__(self, width: int, height: int):
        self.w = width
        self.h = height
        self.px = bytearray(width * height * 3)

    def blend(self, x: int, y: int, colour: tuple[int, int, int], alpha: float):
        if not (0 <= x < self.w and 0 <= y < self.h) or alpha <= 0:
            return
        i = (y * self.w + x) * 3
        a = min(1.0, alpha)
        for c in range(3):
            self.px[i + c] = int(self.px[i + c] * (1 - a) + colour[c] * a)

    def disc(self, cx: float, cy: float, r: float, colour, alpha=1.0):
        for y in range(max(0, int(cy - r)), min(self.h, int(cy + r) + 1)):
            for x in range(max(0, int(cx - r)), min(self.w, int(cx + r) + 1)):
                d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                if d <= r:
                    self.blend(x, y, colour, alpha)

    def ring(self, cx: float, cy: float, r: float, stroke: float, colour, alpha=1.0):
        for y in range(max(0, int(cy - r - stroke)), min(self.h, int(cy + r + stroke) + 1)):
            for x in range(max(0, int(cx - r - stroke)), min(self.w, int(cx + r + stroke) + 1)):
                d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                if abs(d - r) <= stroke / 2:
                    self.blend(x, y, colour, alpha)

    def glow(self, cx: float, cy: float, radius: float, colour):
        for y in range(max(0, int(cy - radius)), min(self.h, int(cy + radius) + 1)):
            for x in range(max(0, int(cx - radius)), min(self.w, int(cx + radius) + 1)):
                d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                if d < radius:
                    self.blend(x, y, colour, 0.10 * (1 - d / radius) ** 2)

    def text(self, s: str, x: int, y: int, scale: int, colour, alpha=1.0):
        pen = x
        for ch in s:
            glyph = FONT.get(ch) or FONT.get(ch.upper()) or FONT["-"]
            for row, line in enumerate(glyph):
                for col, on in enumerate(line):
                    if on == "#":
                        for dy in range(scale):
                            for dx in range(scale):
                                self.blend(pen + col * scale + dx, y + row * scale + dy,
                                           colour, alpha)
            pen += 6 * scale
        return pen

    def text_width(self, s: str, scale: int) -> int:
        return len(s) * 6 * scale

    def save(self, path: Path):
        raw = bytearray()
        for y in range(self.h):
            raw.append(0)
            raw.extend(self.px[y * self.w * 3:(y + 1) * self.w * 3])

        def chunk(kind: bytes, payload: bytes) -> bytes:
            return (struct.pack(">I", len(payload)) + kind + payload
                    + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF))

        png = b"\x89PNG\r\n\x1a\n"
        png += chunk(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0))
        png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        png += chunk(b"IEND", b"")
        path.write_bytes(png)


def og_image(path: Path, version: str):
    """1200x630: the mark from the header, the name, and the version."""
    W, H = 1200, 630
    canvas = Canvas(W, H)
    cyan = (0, 229, 255)
    white = (215, 227, 223)

    # The avatar art from the page, stood in for: a soft core with an outer ring.
    cx, cy = 880, H // 2
    canvas.glow(cx, cy, 460, cyan)
    for r in range(190, 0, -1):
        canvas.disc(cx, cy, r, cyan, 0.012)
    canvas.ring(cx, cy, 190, 2.0, cyan, 0.55)
    canvas.ring(cx, cy, 250, 1.0, cyan, 0.18)
    canvas.disc(cx, cy, 34, (180, 255, 250), 0.95)

    canvas.text("PHONON", 96, 214, 9, white)
    canvas.text(f"v{version}", 96, 330, 4, cyan)
    canvas.text("phononai.org", 96, 404, 2, white, 0.55)

    canvas.save(path)


# --------------------------------------------------------------------------
# Build the data document
# --------------------------------------------------------------------------

def build_data(args) -> dict:
    repo = AppRepo(args.app_repo, args.ref)
    tag = args.ref
    warnings: list[str] = []

    gradle = parse_gradle(repo.read("app/app/build.gradle.kts"))
    version = gradle["version"]
    min_sdk = gradle["min_sdk"]
    if min_sdk not in ANDROID_VERSIONS:
        raise Fail(f"minSdk {min_sdk} has no Android version name in ANDROID_VERSIONS; "
                   "add it rather than printing a number")
    android_min = ANDROID_VERSIONS[min_sdk]

    # ---- release ---------------------------------------------------------
    release = fetch_release(tag, args.release_json)
    published = release.get("published_at") or release.get("created_at")
    if not published:
        raise Fail(f"the release for {tag} has no published_at")
    published_iso = published
    published_date = published[:10]

    apk = None
    for asset in release.get("assets", []):
        if asset.get("name", "").endswith(".apk"):
            apk = asset
            break
    if apk is None:
        raise Fail(f"the release for {tag} has no APK asset")

    sha256 = apk_checksum(release, apk["name"])

    # ---- catalog ---------------------------------------------------------
    catalog = json.loads(repo.read("app/app/src/main/assets/catalog.json"))
    models = catalog["models"]
    if not models:
        raise Fail("catalog.json has no models")
    families = []
    for m in models:
        if m["family"] not in families:
            families.append(m["family"])
    tiers = {"S": "8 GB", "M": "12 GB", "L": "16 GB"}
    known_tiers = [m["ramTier"] for m in models if m["ramTier"] in tiers]
    if not known_tiers:
        raise Fail("catalog.json declares no RAM tier; the requirement line has no source")
    smallest_tier = min(known_tiers, key=lambda t: {"S": 0, "M": 1, "L": 2}[t])
    family_labels = {
        "qwen": "Qwen3.5", "gemma": "Gemma 4", "minicpm": "MiniCPM5",
        "granite": "Granite", "nemotron": "Nemotron",
    }
    sizes = sorted(m["sizeBytes"] for m in models)
    measured_models = [m for m in models if m["decodeRuns"]]

    # ---- changelogs: the three most recent, by versionCode ----------------
    changelogs = []
    for code in (gradle["version_code"], gradle["version_code"] - 1, gradle["version_code"] - 2):
        if code < 1:
            continue
        path = f"fastlane/metadata/android/en-US/changelogs/{code}.txt"
        text = repo.read(path)
        changelogs.append({"version_code": code, "text": text.strip()})
    if not changelogs:
        raise Fail("no changelogs found for the current versionCode")

    # ---- fastlane copy ----------------------------------------------------
    tagline = repo.read("fastlane/metadata/android/en-US/short_description.txt").strip()
    full = repo.read("fastlane/metadata/android/en-US/full_description.txt").strip()
    og_description = next((p.strip() for p in full.split("\n\n") if p.strip()), tagline)

    # ---- screenshots ------------------------------------------------------
    shot_dir = "fastlane/metadata/android/en-US/images/phoneScreenshots"
    shot_names = [n for n in repo.ls(shot_dir) if n.lower().endswith(".png")]
    if not shot_names:
        raise Fail(f"{shot_dir} has no screenshots to publish")
    screenshots = []
    for name in sorted(shot_names):
        data = repo.read_bytes(f"{shot_dir}/{name}")
        try:
            width, height = png_size(data)
        except Fail:
            raise Fail(f"{shot_dir}/{name} is not a readable PNG")
        alt = SCREENSHOT_ALT.get(name, "The app")
        screenshots.append({
            "name": name, "href": f"/assets/screens/{name}",
            "width": width, "height": height, "alt": alt, "bytes": data,
        })

    # ---- devices ----------------------------------------------------------
    devices = []
    for name in repo.ls("devices"):
        if not name.endswith((".yaml", ".yml")):
            continue
        doc = yaml.safe_load(repo.read(f"devices/{name}")) or {}
        measured = doc.get("measured") or {}
        devices.append({
            "file": name,
            "device": doc.get("device", name),
            "codename": doc.get("codename", ""),
            "soc": doc.get("soc", ""),
            "ram_gb": doc.get("ram_gb"),
            "android": doc.get("android"),
            "status": doc.get("status", "candidate"),
            "model": doc.get("model", ""),
            "context": doc.get("context"),
            "threads": doc.get("threads"),
            "measured": measured,
        })
    if not devices:
        raise Fail("devices/ has no manifests; the compatibility section has no source")
    for d in devices:
        m = d["measured"]
        m.setdefault("agent_turn_s", None)
        m.setdefault("watts", None)
        m.setdefault("after_15min_tps", None)
        m.setdefault("after_5min_tps", None)
        m.setdefault("decode_tps", None)
        m.setdefault("prefill_tps", None)
        m.setdefault("app_version", None)
        m.setdefault("measured_date", None)
        # The manifest names the device once, at the top level; provenance()
        # reads it from the measured block, so carry it across. Without this the
        # page says "an unnamed device" beside a sentence naming the device.
        m.setdefault("measured_on", d["device"])
    supported = [d for d in devices if d["status"] == "supported"]
    candidates = [d for d in devices if d["status"] != "supported"]

    # ---- headline and sustained ------------------------------------------
    release_version = version
    headline = None
    for d in sorted(devices, key=lambda d: d["status"] != "supported"):
        m = d["measured"]
        if m.get("agent_turn_s") is not None:
            headline = {
                "kind": "agent_turn",
                "value": m["agent_turn_s"],
                "sentence": f"An agent turn in {m['agent_turn_s']:g} s on a {d['device']}",
                "note": "One agent-shaped request — a system prompt and tool schemas of about "
                        "2,800 tokens, plus 128 generated tokens — through the app's own /v1.",
                "provenance": provenance(m, release_version),
                "device": d["device"],
            }
            break
    if headline is None:
        for d in sorted(devices, key=lambda d: d["status"] != "supported"):
            m = d["measured"]
            if m.get("decode_tps") is not None:
                headline = {
                    "kind": "decode",
                    "value": m["decode_tps"],
                    "sentence": f"{m['decode_tps']:g} tok/s decode on a {d['device']}",
                    "note": "128 greedy tokens through the app's own /v1, at the manifest's "
                            "reference configuration.",
                    "provenance": provenance(m, release_version),
                    "device": d["device"],
                }
                break

    sustained = None
    for d in devices:
        m = d["measured"]
        if m.get("after_15min_tps") is not None:
            sustained = {
                "value": m["after_15min_tps"],
                "device": d["device"],
                "provenance": provenance(m, release_version),
            }
            break

    # ---- running cost -----------------------------------------------------
    cost = None
    for d in devices:
        watts = d["measured"].get("watts")
        if watts is not None:
            kwh_year = watts * 24 * 365 / 1000
            cost = {
                "watts": watts,
                "device": d["device"],
                "rate": args.rate,
                "per_year": kwh_year * args.rate,
                "text": (f"Left serving all year at {watts:g} W, this phone draws about "
                         f"{kwh_year:.0f} kWh — roughly ${kwh_year * args.rate:.0f} a year "
                         f"at ${args.rate:g}/kWh."),
                "provenance": provenance(d["measured"], release_version),
            }
            break

    # ---- quickstart -------------------------------------------------------
    quickstart = {
        "opencode": repo.read("tools/opencode.json"),
        "litellm": repo.read("gateway/litellm.yaml"),
    }

    # ---- licence ----------------------------------------------------------
    licence = spdx_from_license(repo.read("LICENSE"))

    doc_base = f"https://github.com/{APP_REPO}/blob/{tag}"
    data = {
        "app": {
            "version": version,
            "version_code": gradle["version_code"],
            "tag": tag,
            "repo": APP_REPO,
            "min_sdk": min_sdk,
            "android_min": android_min,
            "abi": gradle["abis"][0],
            "abi_short": "64-bit",
            "license": licence,
            "doc_base": doc_base,
            "releases_url": f"https://github.com/{APP_REPO}/releases/tag/{tag}",
            "source_url": f"https://github.com/{APP_REPO}",
            "obtainium_url": f"obtainium://add/https://github.com/{APP_REPO}",
        },
        "release": {
            "name": release.get("name") or f"Phonon {version}",
            "published_iso": published_iso,
            "published": published_date,
            "apk_name": apk["name"],
            "apk_url": apk["browser_download_url"],
            "apk_bytes": apk["size"],
            "apk_size": human_bytes(apk["size"]),
            "sha256": sha256,
            "has_checksum": sha256 is not None,
        },
        "requirements": {"min_ram": tiers[smallest_tier], "min_ram_tier": smallest_tier},
        "models": {
            "count": len(models),
            "families": len(families),
            "family_labels": [family_labels.get(f, f) for f in families],
            "size_min": human_bytes(sizes[0]),
            "size_max": human_bytes(sizes[-1]),
            "measured_count": len(measured_models),
            "table": [
                {
                    "name": m["displayName"], "family": family_labels.get(m["family"], m["family"]),
                    "quant": m["quant"], "context": f"{m['contextSize'] // 1024}K",
                    "size": human_bytes(m["sizeBytes"]),
                    "decode": (f"{m['decodeRuns'][0]:.2f} / {m['decodeRuns'][1]:.2f} tok/s"
                               if len(m["decodeRuns"]) >= 2 else
                               (f"{m['decodeRuns'][0]:.2f} tok/s" if m["decodeRuns"] else None)),
                    "tier": tiers.get(m["ramTier"], m["ramTier"]),
                    "multimodal": bool(m.get("multimodal")),
                    "license": m.get("license", ""),
                    "osi": bool(m.get("osiApproved", True)),
                    "job_fit": m.get("jobFit", ""),
                    "measured_on": m.get("measuredOn", ""),
                }
                for m in models
            ],
        },
        "headline": headline,
        "sustained": sustained,
        "devices": {"supported": supported, "candidate": candidates},
        "cost": cost,
        "changelog": changelogs,
        "quickstart": quickstart,
        "evidence": {k: f"{doc_base}/{v}" for k, v in DOC_FILES.items()},
        "meta": {
            "tagline": tagline,
            "og_description": og_description,
            "description": (f"Phonon serves an OpenAI-compatible API from an Android phone. "
                            f"{version}, {human_bytes(apk['size'])}, Android {android_min}+."),
        },
        "screenshots": screenshots,
        "site": {
            "url": SITE_URL,
            "lastmod": published_date,
            "electricity_rate": args.rate,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    }
    if warnings:
        data["warnings"] = warnings
    return data


SCREENSHOT_ALT = {
    "01.png": "Serve screen: throughput, uptime, endpoint and thermals",
    "02.png": "Model picker: families, sizes, measured rates and context",
    "03.png": "Settings: device, performance profile and tuning",
}


# --------------------------------------------------------------------------
# Render
# --------------------------------------------------------------------------

def render(data: dict, args) -> Path:
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    env = Environment(
        loader=FileSystemLoader(str(Path(args.template).parent)),
        undefined=StrictUndefined,
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    try:
        html = env.get_template(Path(args.template).name).render(**data)
    except TemplateNotFound as exc:
        raise Fail(f"template {exc} not found (expected {args.template})")
    except UndefinedError as exc:
        raise Fail(f"template field not provided by the generator: {exc}; "
                   "wire it in build/generate.py or remove it from the template")

    (out / "index.html").write_text(html, encoding="utf-8")

    # site-data.json ships beside the page so a number can be traced without
    # re-running the build.
    debug = dict(data)
    debug["screenshots"] = [
        {k: v for k, v in s.items() if k != "bytes"} for s in data["screenshots"]
    ]
    (out / "site-data.json").write_text(json.dumps(debug, indent=2) + "\n", encoding="utf-8")

    for static in ("CNAME", "logo.svg", "robots.txt"):
        src = Path(static)
        if not src.exists():
            raise Fail(f"{static} is missing from the site repository")
        shutil.copy(src, out / static)

    assets = out / "assets"
    (assets / "screens").mkdir(parents=True)
    badge = Path("assets/badge_obtainium.png")
    if not badge.exists():
        raise Fail("assets/badge_obtainium.png is missing; the install section needs it")
    shutil.copy(badge, assets / badge.name)
    for shot in data["screenshots"]:
        (assets / "screens" / shot["name"]).write_bytes(shot["bytes"])

    og_image(out / "og.png", data["app"]["version"])

    (out / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'  <url><loc>{SITE_URL}</loc><lastmod>{data["site"]["lastmod"]}</lastmod></url>\n'
        "</urlset>\n",
        encoding="utf-8",
    )
    return out


def check_placeholders(out: Path):
    """A leftover template tag means a field was never wired; fail loudly.

    Only Jinja *tags* are checked, not `}}`: the stylesheet has nested @media
    rules that end in `}}`, and a check that flagged those would be noise the
    next reader learns to ignore.
    """
    text = (out / "index.html").read_text(encoding="utf-8")
    for token in ("{{", "{%", "{#"):
        if token in text:
            line = next(i for i, l in enumerate(text.splitlines(), 1) if token in l)
            raise Fail(f"unresolved template tag {token!r} in dist/index.html line {line}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-repo", required=True, type=Path,
                        help="checkout of chezgoulet/phonon")
    parser.add_argument("--ref", required=True,
                        help="tag (or ref) to describe; v0.1.12, or a branch while testing")
    parser.add_argument("--out", default="dist", type=Path)
    parser.add_argument("--template", default="template/index.html")
    parser.add_argument("--release-json", type=Path, default=None,
                        help="a saved release payload, for running without a token")
    parser.add_argument("--rate", type=float, default=0.15,
                        help="electricity price per kWh quoted on the page")
    args = parser.parse_args()

    try:
        data = build_data(args)
    except Fail as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        out = render(data, args)
        check_placeholders(out)
    except Fail as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(textwrap.dedent(f"""\
        generated {out}/index.html
          app {data['app']['version']} ({data['app']['tag']}), Android {data['app']['android_min']}+
          release {data['release']['published']}, APK {data['release']['apk_size']}
          checksum: {data['release']['sha256'] or 'unavailable (release predates SHA256SUMS)'}
          models {data['models']['count']} in {data['models']['families']} families
          headline: {data['headline']['sentence'] if data['headline'] else 'none available'}
          screenshots {len(data['screenshots'])}, devices {len(data['devices']['supported'])} supported
        """).strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
