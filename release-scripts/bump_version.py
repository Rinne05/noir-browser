#!/usr/bin/env python3
"""Bump Noir's version in every release manifest.

Noir uses independent semantic versions (for example ``1.0.0``). The script
updates noir/version.json, installer/installer.json and theme.json together so
they cannot drift.
"""

import argparse
import json
import re
from pathlib import Path

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
CHANNEL_FIELDS = {
    "stable": "version",
    "rc": "version_rc",
    "beta": "version_beta",
    "alpha": "version_alpha",
}


def load(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def write(path, data):
    Path(path).write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="new version, e.g. 1.0.0")
    parser.add_argument(
        "--branch",
        default="stable",
        choices=sorted(CHANNEL_FIELDS),
        help="release channel/manifest name (default: stable)",
    )
    parser.add_argument("--codename", help="optional Noir codename")
    parser.add_argument("--dry-run", action="store_true", help="show the result without writing")
    args = parser.parse_args()

    if not VERSION_RE.match(args.version):
        parser.error("version must look like 1.0.0")

    version_path = Path("noir/version.json")
    installer_path = Path("installer/installer.json")
    theme_path = Path("theme.json")

    for path in (version_path, installer_path, theme_path):
        if not path.is_file():
            parser.error(f"missing {path}; run from the repository root")

    version_data = load(version_path)
    installer_data = load(installer_path)
    theme_data = load(theme_path)
    package = installer_data["package"]
    channel_field = CHANNEL_FIELDS[args.branch]

    old_version = version_data.get("version")
    version_data["version"] = args.version
    version_data["branch"] = args.branch
    if args.codename is not None:
        version_data["codename"] = args.codename

    package[channel_field] = args.version
    theme_data["version"] = args.version

    print(f"{old_version} -> {args.version} ({args.branch})")
    print(f"- noir/version.json: {args.version}")
    print(f"- installer/installer.json: {channel_field}={args.version}")
    print(f"- theme.json: {args.version}")
    if args.codename:
        print(f"- codename: {args.codename}")

    if args.dry_run:
        print("Dry run: no files written.")
        return 0

    write(version_path, version_data)
    write(installer_path, installer_data)
    write(theme_path, theme_data)
    print("Version manifests updated. Run release-scripts/check_version.py before tagging.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
