"""
Natsumi Browser - Welcome to your personal internet.

Copyright (c) 2024-present Green (@greeeen-dev)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import json
import re
import sys

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
ALLOWED_BRANCHES = ("stable", "rc", "beta", "alpha")
CHANNEL_FIELDS = {
    "stable": "version",
    "rc": "version_rc",
    "beta": "version_beta",
    "alpha": "version_alpha",
}

ref = sys.argv[-1] if len(sys.argv) > 1 else "main"
print(f"Detected ref: {ref}")

with open("noir/version.json", "r", encoding="utf-8") as file:
    version_data = json.load(file)
package_version = version_data["version"]
branch = version_data.get("branch", "stable")

with open("installer/installer.json", "r", encoding="utf-8") as file:
    package = json.load(file)["package"]

with open("theme.json", "r", encoding="utf-8") as file:
    sine_version = json.load(file)["version"]

is_tag = ref.startswith("v")
check_sine = ref == "main" or is_tag
version_match = bool(VERSION_RE.match(package_version))
channel_field = CHANNEL_FIELDS.get(branch)
channel_version = package.get(channel_field) if channel_field else None
installer_versions = [
    package[field]
    for field in CHANNEL_FIELDS.values()
    if package.get(field)
]

installer_match = channel_version == package_version
tag_match = not is_tag or ref == f"v{package_version}"
branch_match = branch in ALLOWED_BRANCHES
sine_match = not check_sine or package_version == sine_version

if not check_sine:
    print("Not a main/tag build; Sine version check skipped.")

if not version_match:
    print(f"Invalid version format: {package_version} (expected semantic version, e.g. 1.0.0)")
if not branch_match:
    print(f"Invalid version branch: {branch} (allowed: {', '.join(ALLOWED_BRANCHES)})")
if not tag_match:
    print(f"Tag mismatch: expected v{package_version}, got {ref}")
if not installer_match:
    print(f"Installer channel mismatch: {branch} should be {package_version}, got {channel_version}")
if not sine_match:
    print(f"Sine version mismatch: expected {package_version}, got {sine_version}")

can_proceed = version_match and installer_match and tag_match and branch_match and sine_match

if can_proceed:
    print("Version matches!")
else:
    print("Version mismatch, cannot build!")

print(f"- Package version (noir/version.json): {package_version}")
print(f"- Version branch/channel: {branch}")
print(f"- Installer version for channel: {channel_version}")
print(f"- Installer versions: {'/'.join(installer_versions)}")
print(f"- Sine version (theme.json): {sine_version}")

if not can_proceed:
    sys.exit(1)
