#!/usr/bin/env python3
"""
Noir Browser - update manifest writer.

Run from the repository root (by the release/publish GitHub workflows, or by
hand). Downloads the GitHub tag archive for the version in noir/version.json,
computes its SHA-256, and writes updates/<branch>.json. The client updater
(noir/scripts/updater.uc.mjs) fetches that manifest from
raw.githubusercontent.com/<repo>/main/updates/<branch>.json and verifies the
downloaded archive against the hash before installing.

The manifest cannot live inside the released tag itself: the hash only exists
after the tag is pushed and GitHub generates the archive, so the manifest is
committed to main *after* tagging.

Manifest fields: version, tag, hash, releasedAt.
"""

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_REPO = "rinne05/noir-browser"  # keep in sync with updater.uc.mjs download URL


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=DEFAULT_REPO, help=f"code repo (default: {DEFAULT_REPO})")
    parser.add_argument("--tag", help="tag to publish (default: v<version from noir/version.json>)")
    parser.add_argument("--branch", help="update branch file name (default: 'branch' from noir/version.json)")
    parser.add_argument("--output-dir", default="updates", help="manifest directory (default: updates)")
    parser.add_argument("--dry-run", action="store_true", help="print the manifest without writing it")
    parser.add_argument("--force", action="store_true", help="re-publish even if this version is already published")
    args = parser.parse_args()

    version_data = json.loads(Path("noir/version.json").read_text(encoding="utf-8"))
    version = version_data["version"]
    branch = args.branch or version_data["branch"]
    tag = args.tag or f"v{version}"

    out_path = Path(args.output_dir) / f"{branch}.json"
    if out_path.exists() and not args.force:
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
        if existing.get("version") == version:
            print(f"{out_path} already describes {version}; nothing to do (use --force to re-publish).")
            return 0

    url = f"https://github.com/{args.repo}/archive/refs/tags/{tag}.zip"
    print(f"Downloading {url}")
    try:
        with urllib.request.urlopen(url) as response:
            archive = response.read()
    except urllib.error.HTTPError as error:
        print(f"Failed to download tag archive (HTTP {error.code}). Is tag {tag} pushed to {args.repo}?")
        return 1

    manifest = {
        "version": version,
        "tag": tag,
        "hash": hashlib.sha256(archive).hexdigest(),
        "releasedAt": round(time.time()),
    }
    print(json.dumps(manifest, indent=2))

    if args.dry_run:
        print("Dry run: manifest not written.")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
