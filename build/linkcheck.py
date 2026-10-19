#!/usr/bin/env python3
"""Check the generated site: internal anchors, internal files, tagged-repo
links, and the APK download.

A page full of numbers that nobody can follow is not evidence, so the links
carrying that evidence are checked rather than assumed:

* `#anchor` targets must exist as ids in the page.
* `/path` references must exist in dist/.
* every `github.com/chezgoulet/phonon/blob/<ref>/<path>` link must name a path
  that exists at that ref — checked against the local checkout, so a rename at
  the tag cannot leave a dead "source" link behind.
* the APK URL is fetched, and its Content-Length is compared with the size the
  page prints.

Usage: build/linkcheck.py dist --app-repo app --ref v0.1.13 [--offline]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

FAILURES: list[str] = []


def note(message: str):
    FAILURES.append(message)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist", type=Path)
    parser.add_argument("--app-repo", type=Path, default=None,
                        help="checkout used to verify links into the tagged repo")
    parser.add_argument("--ref", default=None)
    parser.add_argument("--offline", action="store_true",
                        help="skip the network check on the APK URL")
    args = parser.parse_args()

    page = (args.dist / "index.html").read_text(encoding="utf-8")
    # A commented-out link is not a link. The demo video placeholder is a
    # comment on purpose, so the checker must not chase it.
    page = re.sub(r"<!--.*?-->", "", page, flags=re.S)
    data_path = args.dist / "site-data.json"
    data = json.loads(data_path.read_text()) if data_path.exists() else {}

    # ---- internal anchors -------------------------------------------------
    ids = set(re.findall(r'\sid="([^"]+)"', page))
    for anchor in sorted(set(re.findall(r'href="#([^"]+)"', page))):
        if anchor not in ids:
            note(f"internal anchor #{anchor} has no matching id")

    # ---- internal files ---------------------------------------------------
    internal = set(re.findall(r'(?:href|src)="(/[^"]+)"', page))
    for ref in sorted(internal):
        target = args.dist / ref.lstrip("/")
        if not target.exists():
            note(f"internal reference {ref} is not in dist/ ({target})")

    # ---- links into the tagged repository ---------------------------------
    # A ref may contain slashes (a branch, a release candidate tag), so the ref
    # and the path cannot be separated by a single split. Try every split and
    # accept the one that resolves against the checkout.
    blob = re.compile(r'https://github\.com/chezgoulet/phonon/blob/([^"#?]+)')
    if args.app_repo:
        for remainder in sorted(set(blob.findall(page))):
            parts = remainder.split("/")
            resolved = None
            for cut in range(1, len(parts)):
                ref = "/".join(parts[:cut])
                path = "/".join(parts[cut:])
                proc = subprocess.run(
                    ["git", "-C", str(args.app_repo), "cat-file", "-e", f"{ref}:{path}"],
                    capture_output=True,
                )
                if proc.returncode == 0:
                    resolved = (ref, path)
                    break
            if resolved is None:
                note(f"link to {remainder} — no ref:path pair at that URL exists in the repo")
                continue
            ref, _ = resolved
            if args.ref and ref != args.ref:
                note(f"link points at {ref} but the page describes {args.ref}")
    else:
        print("note: no --app-repo given; skipping tagged-repo link checks",
              file=sys.stderr)

    # ---- the APK ----------------------------------------------------------
    url = data.get("release", {}).get("apk_url")
    size = data.get("release", {}).get("apk_bytes")
    if url and not args.offline:
        request = urllib.request.Request(url, method="HEAD")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                length = response.headers.get("Content-Length")
                if response.status != 200:
                    note(f"APK URL returned {response.status}")
                elif size is not None and length is not None and int(length) != int(size):
                    note(f"APK URL serves {length} bytes; the page says {size}")
        except Exception as exc:
            note(f"APK URL could not be fetched: {exc}")

    if FAILURES:
        print(f"link check failed: {len(FAILURES)} problem(s)", file=sys.stderr)
        for failure in FAILURES:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    print(f"link check passed: {len(ids)} ids, {len(internal)} internal references"
          f"{'' if args.offline else ', APK reachable'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
