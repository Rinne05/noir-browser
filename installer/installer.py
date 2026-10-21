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

import argparse
import configparser
import importlib
import os
import sys
import shutil
import json
import traceback
import hashlib
import re
import requests
import urllib.request, urllib.error
import certifi
import zipfile
from datetime import datetime, timezone
from pathlib import Path

home = str(Path.home())
data_path = str(Path(__file__).parent)

with open(f"{data_path}/installer.json") as file:
    installer_data = json.load(file)

chrome_manifest = [
    'content userchromejs ./',
    'content userscripts ../noir/scripts/',
    'skin userstyles classic/1.0 ../CSS/',
    'content userchrome ../resources/',
    'content natsumi ../noir/',
    'content natsumi-icons ../noir/icons/'
]

# What fx-autoconfig's own chrome.manifest looks like; restored when uninstalling
# only Noir while keeping fx-autoconfig for other mods.
fx_autoconfig_manifest = [
    'content userchromejs ./',
    'content userscripts ../JS/',
    'skin userstyles classic/1.0 ../CSS/',
    'content userchrome ../resources/'
]

# Written by the installer into the profile's chrome folder. The uninstaller
# reads it so that files added by future installer versions are removed without
# having to update the uninstall code.
INSTALL_MANIFEST_NAME = '.noir-install.json'

def read_install_manifest(profile):
    manifest_path = os.path.join(profile, 'chrome', INSTALL_MANIFEST_NAME)
    if not os.path.isfile(manifest_path):
        return None
    try:
        with open(manifest_path, encoding='utf-8') as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return None

def build_install_manifest(package_version, profile_paths, external_paths, pre_existing, backups, js_copies):
    """Data recorded at install time (profilePaths are profile-relative)."""
    return {
        "manifestVersion": 1,
        "brand": "noir-browser",
        "source": "rinne05/noir-browser",
        "packageVersion": package_version,
        "installedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "profilePaths": sorted(set(profile_paths)),
        "externalPaths": sorted(set(external_paths)),
        "preExisting": pre_existing,
        "backups": backups,
        "jsCopies": sorted(set(js_copies)),
    }

def write_install_manifest(profile, manifest):
    manifest_path = os.path.join(profile, 'chrome', INSTALL_MANIFEST_NAME)
    with open(manifest_path, 'w', encoding='utf-8') as file:
        json.dump(manifest, file, indent=2)
    print(f'Recorded install manifest at {manifest_path}')

def discover_extra_artifacts(profile, plan):
    """Find natsumi*/noir* leftovers the plan does not know about yet.

    Covers artifacts created by newer feature versions without code changes.
    They are backed up (or removed when empty) rather than deleted blindly.
    """
    covered = {os.path.normpath(path) for _, path, _ in plan}
    extras = []
    for directory in (profile, os.path.join(profile, 'chrome')):
        try:
            entries = sorted(os.listdir(directory))
        except OSError:
            continue
        for entry in entries:
            if '.noir-backup' in entry:
                continue
            if not (entry.startswith('natsumi') or entry.startswith('noir')):
                continue
            path = os.path.join(directory, entry)
            if os.path.normpath(path) in covered:
                continue
            extras.append(('content-dir' if os.path.isdir(path) else 'content-file', path, None))
    return extras

risk_string = "Noir is provided \"as-is\" without any warranties. By installing and using Noir, you agree\n\
to the GPLv3 software license found in the LICENSE file in the repository. You are responsible for\n\
any damages or issues that may arise from using Noir and you agree not to hold the developers\n\
liable for any such damages or issues.\n\n\
Additionally, Noir uses fx-autoconfig to apply JS scripts to your browser. If your system is\n\
infected with malware, installing Noir may put your browser data at higher risk of being accessed\n\
maliciously. Please ensure your system is secure before proceeding with installation."

def get_admin():
    if sys.platform == 'win32':
        try:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    return os.geteuid() == 0

def download_from_git(repository, branch, destination, is_tag=False):
    heads_string = 'heads'
    if is_tag:
        heads_string = 'tags'

    try:
        urllib.request.urlretrieve(f'https://github.com/{repository}/archive/refs/{heads_string}/{branch}.zip', f'.noir-installer/{destination}.zip')
    except urllib.error.URLError:
        try:
            r = requests.get(f'https://github.com/{repository}/archive/refs/{heads_string}/{branch}.zip')
        except:
            # retry with certifi.where()
            r = requests.get(f'https://github.com/{repository}/archive/refs/{heads_string}/{branch}.zip', verify=certifi.where())

        with open(f'.noir-installer/{destination}.zip', 'wb') as file:
            file.write(r.content)

    with zipfile.ZipFile(f'.noir-installer/{destination}.zip', 'r') as file:
        file.extractall('.noir-installer')

        if is_tag and branch.startswith('v'):
            branch = branch[1:]

        os.rename(f".noir-installer/{repository.split('/')[1]}-{branch}", f".noir-installer/{destination}")

class BrowserEntry:
    def __init__(self, name, name_universal, name_macos, name_flatpak, name_windows, name_windows_binary):
        self.name = name
        self.name_universal = name_universal
        self.name_macos = name_macos
        self.name_flatpak = name_flatpak
        self.name_windows = name_windows
        self.name_windows_binary = name_windows_binary

def _get_macos_path(browser: BrowserEntry):
    path = home + f'/Library/Application Support/{browser.name_macos}/Profiles'

    if not os.path.exists(path):
        raise NotADirectoryError('Browser is not installed')

    return path

def _get_windows_path(browser: BrowserEntry):
    if not browser.name_windows:
        raise NotADirectoryError('Browser is not supported on Windows')

    roaming = os.environ.get('APPDATA')
    if not roaming:
        roaming = os.path.join(home, 'AppData', 'Roaming')

    parts = browser.name_windows.replace('\\', '/').split('/')
    path = os.path.join(roaming, *parts)

    if not os.path.isdir(path):
        raise NotADirectoryError('Browser is not installed')

    return path

WINDOWS_BROWSER_EXES = {
    'mozilla': 'firefox.exe',
    'floorp': 'floorp.exe',
    'waterfox': 'waterfox.exe',
    'librewolf': 'librewolf.exe',
    'glide-browser': 'glide.exe',
}

def _get_windows_install_path(browser: BrowserEntry):
    exe_name = WINDOWS_BROWSER_EXES.get(browser.name_universal)
    folder_name = browser.name_windows_binary
    if not exe_name or not folder_name:
        raise NotADirectoryError('Browser is not supported on Windows')

    candidates = []

    try:
        winreg = importlib.import_module('winreg')
    except ImportError:
        winreg = None

    if winreg:
        key_path = rf'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}'
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
                try:
                    with winreg.OpenKey(hive, key_path, 0, winreg.KEY_READ | view) as key:
                        value, _ = winreg.QueryValueEx(key, None)
                    value = os.path.expandvars(value.strip('"'))
                    if value:
                        candidates.append(os.path.dirname(value))
                except OSError:
                    continue

    roots = [
        os.environ.get('ProgramFiles'),
        os.environ.get('ProgramFiles(x86)'),
        os.environ.get('LOCALAPPDATA'),
        os.path.join(home, 'AppData', 'Local'),
    ]

    for root in roots:
        if not root:
            continue
        candidates.append(os.path.join(root, folder_name))
        candidates.append(os.path.join(root, 'Programs', folder_name))
        if browser.name_universal == 'waterfox':
            candidates.append(os.path.join(root, 'Waterfox', 'Waterfox'))

    seen = set()
    for candidate in candidates:
        if not candidate:
            continue
        candidate = os.path.normpath(candidate)
        if candidate in seen:
            continue
        seen.add(candidate)
        if os.path.isfile(os.path.join(candidate, exe_name)):
            return candidate

    raise NotADirectoryError('Browser is not installed')

def _get_linux_path(browser: BrowserEntry):
    browser_path = home + f'/.{browser.name_universal}'
    path = home + browser_path + '/Profiles'

    if os.path.exists(browser_path):
        if os.path.exists(path):
            return path

        else:
            if os.path.exists(browser_path):
                return browser_path

    raise NotADirectoryError('Browser is not installed')

def _get_flatpak_path(browser: BrowserEntry):
    if not browser.name_flatpak:
        raise NotADirectoryError('Browser does not support Flatpak')

    path = home + f'/.var/app/{browser.name_flatpak}/.{browser.name_universal}'

    if not os.path.exists(path):
        raise NotADirectoryError('Browser is not installed')

    return path

browsers = [
    BrowserEntry('Firefox', 'mozilla', 'Firefox', 'org.mozilla.firefox', 'Mozilla/Firefox', 'Mozilla Firefox'),
    BrowserEntry('Floorp', 'floorp', 'Floorp', None, 'Floorp', 'Floorp'),
    BrowserEntry('Waterfox', 'waterfox', 'Waterfox', None, 'Waterfox', 'Waterfox'),
    BrowserEntry('Librewolf', 'librewolf', 'LibreWolf', 'io.gitlab.librewolf-community', 'librewolf', 'LibreWolf'),
    BrowserEntry('Glide', 'glide-browser', 'Glide', None, None, None)
]

def get_profiles(path):
    if os.path.isfile(os.path.join(path, 'prefs.js')) or os.path.isfile(os.path.join(path, 'times.json')):
        return [os.path.normpath(path)]

    profiles = []

    ini_path = os.path.join(path, 'profiles.ini')
    if os.path.isfile(ini_path):
        parser = configparser.ConfigParser(interpolation=None)
        try:
            parser.read(ini_path, encoding='utf-8-sig')
        except (configparser.Error, OSError, UnicodeError):
            parser = None
        if parser:
            for section in parser.sections():
                if not section.startswith('Profile'):
                    continue
                raw_path = parser.get(section, 'Path', fallback='').strip()
                if not raw_path:
                    continue
                is_relative = parser.get(section, 'IsRelative', fallback='1').strip() != '0'
                candidate = raw_path if not is_relative else os.path.join(path, raw_path)
                candidate = os.path.normpath(candidate)
                if os.path.isdir(candidate) and candidate not in profiles:
                    profiles.append(candidate)

    for base in (path, os.path.join(path, 'Profiles')):
        try:
            entries = os.listdir(base)
        except OSError:
            continue
        for entry in entries:
            candidate = os.path.normpath(os.path.join(base, entry))
            if candidate in profiles or not os.path.isdir(candidate):
                continue
            if ('.' in entry
                    or os.path.isfile(os.path.join(candidate, 'prefs.js'))
                    or os.path.isfile(os.path.join(candidate, 'times.json'))):
                profiles.append(candidate)

    return profiles

def prompt_for_path(message):
    while True:
        user_input = input(f"{message}\nFile path (type 'exit' to quit): ").strip().strip('"')
        if user_input.lower() == 'exit':
            sys.exit(0)
        if os.path.exists(user_input):
            return user_input
        print("Path does not exist. Please try again.")

def select_browser(prompt='Select the browser to install Noir to:'):
    available = [browser for browser in browsers if sys.platform != 'win32' or browser.name_windows]
    print(prompt)
    for idx, browser in enumerate(available):
        print(f"{idx+1}. {browser.name}")
    while True:
        try:
            choice = int(input()) - 1
            if choice < 0 or choice >= len(available):
                raise ValueError()
            return available[choice]
        except ValueError:
            print(f'Invalid input. Please choose a number between 1 and {len(available)}.')
        except KeyboardInterrupt:
            sys.exit(0)

def detect_install_and_profiles(browser):
    # Detect install path
    install_path = None
    profile_root = None

    try:
        if sys.platform == 'darwin':
            install_path = f'/Applications/{browser.name_macos}.app/Contents/Resources'
            profile_root = _get_macos_path(browser)
        elif sys.platform.startswith('linux'):
            install_path = f'/usr/lib/{browser.name_universal}'
            try:
                profile_root = _get_linux_path(browser)
            except NotADirectoryError:
                if browser.name_flatpak:
                    try:
                        profile_root = _get_flatpak_path(browser)
                    except NotADirectoryError:
                        profile_root = None
                else:
                    profile_root = None
        elif sys.platform == 'win32':
            install_path = _get_windows_install_path(browser)
            profile_root = _get_windows_path(browser)
        else:
            raise NotImplementedError('Unsupported platform')
    except NotADirectoryError:
        profile_root = None

    if not install_path or not os.path.isdir(install_path):
        if sys.platform == 'darwin':
            os_specific_instructions = "On macOS, this would be /path/to/Browser.app/Contents/Resources."
        elif sys.platform == 'win32':
            os_specific_instructions = (
                "On Windows, this is the folder containing the browser executable "
                "(for example C:\\Program Files\\Mozilla Firefox)."
            )
        else:
            os_specific_instructions = "On Linux, this would be the folder the browser's binary is located in."

        install_path = prompt_for_path(
            f"Could not detect install location for {browser.name}. Please enter the browser's install location.\n{os_specific_instructions}"
        )

    if not profile_root or not os.path.isdir(profile_root):
        profile_root = prompt_for_path(f"Could not detect profiles directory for {browser.name}.")

    # Get profiles
    profile_paths = get_profiles(profile_root)
    if not profile_paths:
        print(f"No profiles found in {profile_root}.")

        if sys.platform == 'darwin':
            os_specific_instructions = "On macOS, this would usually be /Users/user/Library/Application Support/Browser/Profiles."
        elif sys.platform == 'win32':
            os_specific_instructions = (
                "On Windows, this is usually %APPDATA%\\Mozilla\\Firefox "
                "(or the folder containing profiles.ini)."
            )
        else:
            os_specific_instructions = "On Linux, this would be the parent folder to your profile folders (e.g. /home/user/.browser)."

        profile_root = prompt_for_path(
            f"Please enter a valid profile directory for {browser.name}.\n{os_specific_instructions}"
        )
        profile_paths = get_profiles(profile_root)

    return install_path, profile_paths

def select_profile(profile_paths, prompt):
    print(prompt)
    for idx, profile in enumerate(profile_paths):
        print(f"{idx+1}. {profile}")
    while True:
        try:
            choice = int(input()) - 1
            if choice < 0 or choice >= len(profile_paths):
                raise ValueError()
            return profile_paths[choice]
        except ValueError:
            print(f'Invalid input. Please choose a number between 1 and {len(profile_paths)}.')
        except KeyboardInterrupt:
            sys.exit(0)

def _sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as file:
        for chunk in iter(lambda: file.read(65536), b''):
            digest.update(chunk)
    return digest.hexdigest()

def _is_loader_only(path, import_fragments):
    """True if a userChrome/userContent file references Noir and holds nothing
    but comments and @import statements (i.e. it is the installer's loader).
    import_fragments is a tuple so both current and legacy loaders match."""
    try:
        with open(path, encoding='utf-8', errors='replace') as file:
            text = file.read()
    except OSError:
        return False
    if not any(fragment in text for fragment in import_fragments):
        return False
    stripped = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    stripped = re.sub(r"//[^\n]*", "", stripped)
    stripped = re.sub(r"@import\s+(?:url\()?['\"][^'\"]*['\"]\)?\s*;", "", stripped)
    return stripped.strip() == ""

def plan_uninstall(profile, install_path=None, full_cleanup=False):
    """Build the list of actions that uninstalling Noir from a profile requires.

    Actions: ('dir'|'file'|'backup'|'restore'|'restore+backup'|'manifest', path, extra)
    """
    chrome = os.path.join(profile, 'chrome')
    plan = []

    # Noir folders, updater leftovers. Both the current (noir) and the legacy
    # (natsumi) layout are handled so pre-rename installs can still be removed.
    for path in [
        os.path.join(chrome, 'noir'),
        os.path.join(chrome, 'noir-old'),
        os.path.join(chrome, 'noir-new'),
        os.path.join(chrome, 'natsumi'),
        os.path.join(chrome, 'natsumi-old'),
        os.path.join(chrome, 'natsumi-new'),
        os.path.join(profile, 'noir-updater-downloads'),
        os.path.join(profile, 'natsumi-updater-downloads'),
        os.path.join(profile, 'noir-bento-temp'),
        os.path.join(profile, 'natsumi-bento-temp'),
    ]:
        if os.path.exists(path) or os.path.islink(path):
            plan.append(('dir', path, None))

    # Runtime artifacts holding user-created data: back up instead of deleting.
    for prefix in ('noir', 'natsumi'):
        for name in ('themes', 'bento', 'uploads'):
            path = os.path.join(profile, f'{prefix}-{name}')
            if os.path.exists(path):
                plan.append(('content-dir', path, None))
        path = os.path.join(profile, f'{prefix}-shortcuts.json')
        if os.path.exists(path):
            plan.append(('content-file', path, None))
        path = os.path.join(chrome, f'{prefix}-config.css')
        if os.path.exists(path):
            plan.append(('file', path, None))

    # userChrome.css / userContent.css: restore pre-install backup, else remove;
    # if the file was customized after install, keep a copy before touching it.
    for name, fragments in [
        ('userChrome.css', ('noir/noir.css', 'natsumi/natsumi.css')),
        ('userContent.css', ('noir/noir-pages.css', 'natsumi/natsumi-pages.css')),
    ]:
        current = os.path.join(chrome, name)
        backup = current + '.bak'
        if os.path.isfile(current) and os.path.isfile(backup):
            if _is_loader_only(current, fragments):
                plan.append(('restore', current, backup))
            else:
                plan.append(('restore+backup', current, backup))
        elif os.path.isfile(backup):
            plan.append(('restore', current, backup))
        elif os.path.isfile(current):
            try:
                with open(current, encoding='utf-8', errors='replace') as file:
                    loader_text = file.read()
                references_noir = any(fragment in loader_text for fragment in fragments)
            except OSError:
                references_noir = False
            if not references_noir:
                plan.append(('keep', current, None))
            elif _is_loader_only(current, fragments):
                plan.append(('file', current, None))
            else:
                plan.append(('backup', current, None))

    # Scripts copied into chrome/JS when the folder existed before install.
    # Only remove files that are byte-identical to the installed copies.
    scripts_dirs = [path for path in (
        os.path.join(chrome, 'noir', 'scripts'),
        os.path.join(chrome, 'natsumi', 'scripts'),
    ) if os.path.isdir(path)]
    js_dir = os.path.join(chrome, 'JS')
    if scripts_dirs and os.path.isdir(js_dir):
        for scripts_dir in scripts_dirs:
            for entry in sorted(os.listdir(scripts_dir)):
                if not entry.endswith(('.js', '.mjs')):
                    continue
                source = os.path.join(scripts_dir, entry)
                target = os.path.join(js_dir, entry)
                if os.path.isfile(source) and os.path.isfile(target):
                    try:
                        if _sha256(source) == _sha256(target):
                            plan.append(('file', target, None))
                    except OSError:
                        pass

    # chrome.manifest: restore fx-autoconfig's own version (Noir-only uninstall)
    manifest = os.path.join(chrome, 'utils', 'chrome.manifest')
    if not full_cleanup and os.path.isfile(manifest):
        try:
            with open(manifest, encoding='utf-8', errors='replace') as file:
                manifest_text = file.read()
        except OSError:
            manifest_text = ""
        if 'natsumi' in manifest_text or '/noir/' in manifest_text:
            plan.append(('manifest', manifest, None))

    if full_cleanup:
        for path in [
            os.path.join(chrome, 'utils'),
            os.path.join(chrome, 'CSS'),
            os.path.join(chrome, 'resources'),
        ]:
            if os.path.exists(path):
                plan.append(('dir', path, None))
        if os.path.isdir(js_dir):
            plan.append(('empty-dir', js_dir, None))

        if install_path:
            for path in [
                os.path.join(install_path, 'config.js'),
                os.path.join(install_path, 'defaults', 'pref', 'config-prefs.js'),
            ]:
                if os.path.exists(path):
                    plan.append(('file', path, None))
            if os.path.exists(os.path.join(install_path, 'librewolf.cfg')):
                for path in [
                    os.path.join(profile, '..', 'librewolf.overrides.cfg'),
                    os.path.join(str(Path.home()), '.librewolf', 'librewolf.overrides.cfg'),
                ]:
                    if os.path.exists(path):
                        plan.append(('file', path, None))

    # Install manifest: everything the install recorded, including files from
    # newer versions that this uninstall code does not know about yet.
    install_manifest = read_install_manifest(profile)
    if install_manifest:
        covered = {os.path.normpath(path) for _, path, _ in plan}

        def add_manifest_path(path):
            if not path or not os.path.exists(path):
                return
            normalized = os.path.normpath(path)
            if normalized in covered:
                return
            plan.append(('dir' if os.path.isdir(path) else 'file', path, None))
            covered.add(normalized)

        for relative in install_manifest.get('profilePaths', []):
            add_manifest_path(os.path.join(profile, relative))
        for path in install_manifest.get('externalPaths', []):
            add_manifest_path(path)
        for record in install_manifest.get('backups', []):
            current = os.path.join(profile, record.get('path', ''))
            backup = os.path.join(profile, record.get('backup', ''))
            if record.get('backup') and os.path.isfile(backup) and os.path.normpath(current) not in covered:
                plan.append(('restore', current, backup))
                covered.add(os.path.normpath(current))
        for relative in install_manifest.get('jsCopies', []):
            path = os.path.join(profile, relative)
            if os.path.isfile(path) and os.path.normpath(path) not in covered:
                # Recorded as our copy, but the source may be gone; keep a backup.
                plan.append(('content-file', path, None))
                covered.add(os.path.normpath(path))
        plan.append(('file', os.path.join(chrome, INSTALL_MANIFEST_NAME), None))

    # Anything natsumi*/noir* that the plan does not know about (new features).
    plan.extend(discover_extra_artifacts(profile, plan))

    return plan

def perform_uninstall(plan, dry_run=False):
    skipped = []
    for action, path, extra in plan:
        try:
            if action == 'dir':
                print(f"  [REMOVE DIR]  {path}")
                if not dry_run:
                    if os.path.islink(path):
                        os.unlink(path)
                    else:
                        shutil.rmtree(path)
            elif action == 'file':
                print(f"  [REMOVE FILE] {path}")
                if not dry_run:
                    os.remove(path)
            elif action == 'backup':
                keep = path + '.noir-backup'
                print(f"  [BACKUP]      {path} -> {keep} (file was customized)")
                if not dry_run:
                    shutil.copyfile(path, keep)
                    os.remove(path)
            elif action == 'keep':
                print(f"  [KEEP]        {path} (no Noir reference; left untouched)")
            elif action == 'content-dir':
                with os.scandir(path) as entries:
                    has_items = any(entries)
                if not has_items:
                    print(f"  [REMOVE DIR]  {path} (empty)")
                    if not dry_run:
                        os.rmdir(path)
                else:
                    keep = path + '.noir-backup'
                    print(f"  [BACKUP]      {path} -> {keep} (contains your own data)")
                    if not dry_run:
                        os.rename(path, keep)
            elif action == 'content-file':
                keep = path + '.noir-backup'
                print(f"  [BACKUP]      {path} -> {keep} (contains your own data)")
                if not dry_run:
                    os.rename(path, keep)
            elif action == 'restore':
                print(f"  [RESTORE]     {path} from {extra}")
                if not dry_run:
                    shutil.copyfile(extra, path)
                    os.remove(extra)
            elif action == 'restore+backup':
                keep = path + '.noir-backup'
                print(f"  [RESTORE]     {path} from {extra} (current file kept as {keep})")
                if not dry_run:
                    shutil.copyfile(path, keep)
                    shutil.copyfile(extra, path)
                    os.remove(extra)
            elif action == 'manifest':
                print(f"  [RESTORE]     {path} (fx-autoconfig default)")
                if not dry_run:
                    with open(path, 'w+') as file:
                        file.write('\n'.join(fx_autoconfig_manifest))
            elif action == 'empty-dir':
                print(f"  [REMOVE DIR]  {path} (only if empty)")
                if not dry_run:
                    try:
                        os.rmdir(path)
                    except OSError:
                        print(f"    kept: {path} still has other files")
        except PermissionError:
            print(f"  [SKIP]        {path} (permission denied)")
            skipped.append(path)
        except OSError as error:
            print(f"  [SKIP]        {path} ({error.strerror or error})")
            skipped.append(path)
    return skipped

def noir_pref_lines(profile, full_cleanup=False):
    """Return (prefs_path, kept_lines, removed_lines) for a profile's prefs.js."""
    prefs_path = os.path.join(profile, 'prefs.js')
    if not os.path.isfile(prefs_path):
        return prefs_path, None, []
    prefixes = ['user_pref("natsumi.']
    if full_cleanup:
        prefixes.append('user_pref("userChromeJS.')
    removed, kept = [], []
    with open(prefs_path, encoding='utf-8', errors='replace') as file:
        for line in file:
            if any(line.lstrip().startswith(prefix) for prefix in prefixes):
                removed.append(line.strip())
            else:
                kept.append(line)
    return prefs_path, kept, removed

def clean_prefs(profile, full_cleanup=False, dry_run=False):
    """Remove Noir/fx-autoconfig prefs from prefs.js. Firefox must be closed,
    otherwise Firefox rewrites the file on exit and the prefs come back."""
    prefs_path, kept, removed = noir_pref_lines(profile, full_cleanup)
    if kept is None:
        print(f'[WARN] No prefs.js found in {profile}; skipping pref cleanup.')
        return 0
    if not removed:
        print('No Noir prefs found in prefs.js.')
        return 0
    if dry_run:
        print(f'prefs.js: {len(removed)} pref(s) would be removed')
        return len(removed)
    shutil.copyfile(prefs_path, prefs_path + '.noir-backup')
    with open(prefs_path, 'w', encoding='utf-8') as file:
        file.writelines(kept)
    print(f'prefs.js: removed {len(removed)} pref(s); backup at {prefs_path}.noir-backup')
    return len(removed)

def uninstall_main(args=None):
    args = args or argparse.Namespace()
    profile = getattr(args, 'profile', None)
    install_path = getattr(args, 'install_path', None)
    full_cleanup = getattr(args, 'full', False)
    assume_yes = getattr(args, 'yes', False)
    dry_run = getattr(args, 'dry_run', False)
    clean_prefs_flag = getattr(args, 'clean_prefs', False)

    if not profile:
        browser = select_browser('Select the browser to uninstall Noir from:')
        install_path, profile_paths = detect_install_and_profiles(browser)
        if not profile_paths:
            print('No profiles found to uninstall from.')
            sys.exit(1)
        profile = select_profile(profile_paths, 'Select the profile to uninstall Noir from:')
    elif not install_path and not full_cleanup:
        print('[INFO] No --install-path given; fx-autoconfig program files will be kept.')

    if not full_cleanup and not assume_yes:
        print('Uninstall options:')
        print('1. Remove Noir only (keeps fx-autoconfig and other JS mods)')
        print('2. Remove Noir and fx-autoconfig (full cleanup)')
        while True:
            try:
                choice = int(input()) - 1
                if choice not in (0, 1):
                    raise ValueError()
                full_cleanup = choice == 1
                break
            except ValueError:
                print('Invalid input. Please choose 1 or 2.')
            except KeyboardInterrupt:
                sys.exit(0)

    plan = plan_uninstall(profile, install_path, full_cleanup)
    pref_count = 0
    if clean_prefs_flag:
        _, _, removed_prefs = noir_pref_lines(profile, full_cleanup)
        pref_count = len(removed_prefs)

    if not plan and not pref_count:
        print('Nothing to uninstall: Noir does not appear to be installed in this profile.')
        return

    print('The following will be ' + ('shown only (dry run)' if dry_run else 'removed') + ':')
    for action, path, extra in plan:
        print(f"  {action}: {path}" + (f" (from {extra})" if extra else ""))
    if pref_count:
        print(f"  prefs.js: {pref_count} pref(s) (Firefox must be closed)")
    if full_cleanup:
        print('Note: fx-autoconfig will be removed. Other mods depending on it will stop working.')
        install_manifest = read_install_manifest(profile)
        if install_manifest:
            pre_existing = install_manifest.get('preExisting', {})
            if pre_existing.get('fxAutoconfigProgram') or pre_existing.get('fxAutoconfigProfile'):
                print('Note: fx-autoconfig was already installed before Noir; it will still be removed.')

    if not assume_yes:
        print("Type 'y' to continue.")
        if input().lower() != 'y':
            print('Aborted.')
            sys.exit(1)

    skipped = perform_uninstall(plan, dry_run)
    if clean_prefs_flag:
        clean_prefs(profile, full_cleanup, dry_run)
    if skipped:
        print()
        print('Some items could not be removed (permission denied). Re-run this installer')
        print('with sudo/administrator rights, or remove these paths manually:')
        for path in skipped:
            print(f'  {path}')
    if dry_run:
        print('Dry run: nothing was changed.')
    else:
        print('Noir uninstalled. Restart your browser to apply the changes.')

def main():
    browser = select_browser()
    install_path, profile_paths = detect_install_and_profiles(browser)

    profile = select_profile(profile_paths, 'Select the profile to install Noir to:')

    print('Select the version to install:')

    version_keys = ['version', 'version_rc', 'version_beta', 'version_alpha']
    version_keys_text = {
        'version': 'Stable',
        'version_rc': 'Release Candidate',
        'version_beta': 'Beta',
        'version_alpha': 'Alpha'
    }
    installable_versions = []
    for version_key in version_keys:
        version = installer_data["package"].get(version_key)
        if version:
            installable_versions.append(version)
        else:
            continue
        print(f'{len(installable_versions)}. {version} ({version_keys_text[version_key]})')

    while True:
        try:
            choice = int(input()) - 1

            if choice < 0 or choice >= len(installable_versions):
                raise ValueError()

            break
        except ValueError:
            print(f'Invalid input. Please choose a number between 1 and {len(installable_versions)}.')
        except KeyboardInterrupt:
            sys.exit(0)

    version_to_install = installable_versions[choice]

    # For Flatpak, we may need to check if the user is running as root
    needs_sudo = False
    if browser.name_flatpak and '.var/app' in profile:
        # Check install location
        if os.path.isdir(f'/var/lib/flatpak/app/{browser.name_flatpak}'):
            needs_sudo = True
    elif sys.platform.startswith('linux'):
        # Check install location
        needs_sudo = True
    elif sys.platform == 'win32':
        # fx-autoconfig's program files live in the browser install folder.
        needs_sudo = True

    # Create temporary directory
    current_dir = os.getcwd()
    if not os.path.exists(f'{current_dir}/.noir-installer'):
        os.mkdir(f'{current_dir}/.noir-installer')

    # Get fx-autoconfig install status
    fx_autoconfig_installed = False
    if os.path.isfile(f'{install_path}/config.js') and os.path.isdir(f'{install_path}/defaults'):
        fx_autoconfig_installed = True

    if not os.path.exists(f'{profile}/chrome'):
        os.mkdir(f'{profile}/chrome')

    # Install manifest bookkeeping: record every path this installer creates so
    # the uninstaller does not need to know about it. When adding a new copy
    # step below, append its target here as well.
    manifest_profile_paths = []
    manifest_external_paths = []
    manifest_backups = []
    manifest_js_copies = []
    js_folder_pre_existed = os.path.isdir(f'{profile}/chrome/JS')

    fx_autoconfig_profile_installed = False
    if os.path.isdir(f'{profile}/chrome/utils'):
        fx_autoconfig_profile_installed = True

    fx_autoconfig_downloaded = False
    sine_support = False

    print("Noir will now be installed. Please read the following before proceeding:")
    print(risk_string)
    print("If you have read the above and agree to the terms, type 'y' to continue.")
    confirm = input().lower() == "y"

    if not confirm:
        sys.exit(1)

    if not fx_autoconfig_installed:
        if needs_sudo and not get_admin():
            if sys.platform == 'win32':
                print('Administrator is required to write the fx-autoconfig files.')
                print('Right-click the installer and choose "Run as administrator".')
            else:
                print('Sudo/administrator is required to install Noir to this browser.')
            sys.exit(1)

        print('Installing fx-autoconfig...')
        try:
            download_from_git('greeeen-dev/fx-autoconfig', 'master', 'fx-autoconfig')
        except:
            print('Failed to clone fx-autoconfig repository.')
            raise

        fx_autoconfig_downloaded = True

        print('Copying fx-autoconfig browser files...')

        # Copy config.js
        shutil.copyfile('.noir-installer/fx-autoconfig/program/config.js', f'{install_path}/config.js')
        manifest_external_paths.append(f'{install_path}/config.js')

        # Create default prefs directories if it doesn't exist
        os.makedirs(f'{install_path}/defaults', exist_ok=True)
        os.makedirs(f'{install_path}/defaults/pref', exist_ok=True)

        # Copy fx-autoconfig files
        if "librewolf.cfg" in os.listdir(install_path):
            # Assume we're on LibreWolf. Portable builds keep the override in the
            # profile folder; installed builds use the per-user config root.
            if os.path.isdir(os.path.join(install_path, 'Profiles')):
                profile_root = profile
            else:
                profile_root = os.path.dirname(os.path.abspath(profile))
                if os.path.basename(profile_root) == 'Profiles':
                    profile_root = os.path.dirname(profile_root)
                if sys.platform == 'darwin':
                    # LibreWolf reads overrides from ~/.librewolf.
                    profile_root = os.path.join(home, '.librewolf')
                elif sys.platform == 'win32':
                    # Installed LibreWolf reads overrides from %USERPROFILE%\.librewolf.
                    profile_root = os.path.join(home, '.librewolf')
            os.makedirs(profile_root, exist_ok=True)

            shutil.copyfile('.noir-installer/fx-autoconfig/program/config.js', f'{profile_root}/librewolf.overrides.cfg')
            shutil.copy('.noir-installer/fx-autoconfig/program/defaults/pref/config-prefs-librewolf.js', f'{install_path}/defaults/pref/config-prefs.js')
            manifest_external_paths.append(f'{profile_root}/librewolf.overrides.cfg')
        else:
            shutil.copy('.noir-installer/fx-autoconfig/program/defaults/pref/config-prefs.js', f'{install_path}/defaults/pref/config-prefs.js')
        manifest_external_paths.append(f'{install_path}/defaults/pref/config-prefs.js')
    if not fx_autoconfig_profile_installed:
        if not fx_autoconfig_downloaded:
            print('Installing fx-autoconfig...')

            try:
                download_from_git('greeeen-dev/fx-autoconfig', 'master', 'fx-autoconfig')
            except:
                print('Failed to clone fx-autoconfig repository.')
                raise

        print('Copying fx-autoconfig profile files...')
        shutil.copytree('.noir-installer/fx-autoconfig/profile/chrome/CSS', f'{profile}/chrome/CSS', dirs_exist_ok=True)
        shutil.copytree('.noir-installer/fx-autoconfig/profile/chrome/utils', f'{profile}/chrome/utils', dirs_exist_ok=True)
        shutil.copytree('.noir-installer/fx-autoconfig/profile/chrome/resources', f'{profile}/chrome/resources', dirs_exist_ok=True)
        manifest_profile_paths.extend(['chrome/CSS', 'chrome/utils', 'chrome/resources'])

        if os.path.isdir(f'{profile}/chrome/JS'):
            print('A JS folder already exists in your profile. The installer will copy Noir Append files to there.')
            sine_support = True

    print('Installing Noir...')
    try:
        download_from_git('rinne05/noir-browser', f'v{version_to_install}', 'natsumi', is_tag=True)
    except:
        print('Failed to clone Noir repository.')
        raise

    for old_folder in ['noir', 'natsumi']:
        old_path = f'{profile}/chrome/{old_folder}'
        if os.path.islink(old_path):
            print('Removing existing Noir dev symlink...')
            os.unlink(old_path)
        elif os.path.exists(old_path):
            print('Removing existing Noir installation...')
            shutil.rmtree(old_path)

    shutil.copytree('.noir-installer/natsumi/noir', f'{profile}/chrome/noir', dirs_exist_ok=True)
    manifest_profile_paths.append('chrome/noir')

    # Back up original userChrome files
    try:
        shutil.copy(f'{profile}/chrome/userChrome.css', f'{profile}/chrome/userChrome.css.bak')
        manifest_backups.append({'path': 'chrome/userChrome.css', 'backup': 'chrome/userChrome.css.bak'})
    except FileNotFoundError:
        pass
    try:
        shutil.copy(f'{profile}/chrome/userContent.css', f'{profile}/chrome/userContent.css.bak')
        manifest_backups.append({'path': 'chrome/userContent.css', 'backup': 'chrome/userContent.css.bak'})
    except FileNotFoundError:
        pass

    shutil.copy('.noir-installer/natsumi/userChrome.css', f'{profile}/chrome/userChrome.css')
    shutil.copy('.noir-installer/natsumi/userContent.css', f'{profile}/chrome/userContent.css')
    manifest_profile_paths.extend(['chrome/userChrome.css', 'chrome/userContent.css'])
    if os.path.isfile('.noir-installer/natsumi/noir-config.css'):
        shutil.copy('.noir-installer/natsumi/noir-config.css', f'{profile}/chrome/noir-config.css')
        manifest_profile_paths.append('chrome/noir-config.css')
    else:
        print('[WARN] noir-config.css not found in download. Skipping.')

    if sine_support:
        for file in os.listdir('.noir-installer/natsumi/noir/scripts'):
            if file.endswith('.js') or file.endswith('.mjs'):
                shutil.copy(f'.noir-installer/natsumi/noir/scripts/{file}', f'{profile}/chrome/JS/{file}')
                manifest_js_copies.append(f'chrome/JS/{file}')
    else:
        with open(f'{profile}/chrome/utils/chrome.manifest', 'w+') as file:
            file.write('\n'.join(chrome_manifest))

    write_install_manifest(profile, build_install_manifest(
        package_version=version_to_install,
        profile_paths=manifest_profile_paths,
        external_paths=manifest_external_paths,
        pre_existing={
            'fxAutoconfigProgram': fx_autoconfig_installed,
            'fxAutoconfigProfile': fx_autoconfig_profile_installed,
            'jsFolder': js_folder_pre_existed,
        },
        backups=manifest_backups,
        js_copies=manifest_js_copies,
    ))

    if sys.platform != 'win32' and get_admin():
        sudo_user = os.environ.get('SUDO_USER')
        if sudo_user:
            print('Fixing permissions...')
            os.system(f'chown -R {sudo_user} "{profile}/chrome"')

    print('Noir installed successfully! ^w^')

def parse_args():
    parser = argparse.ArgumentParser(description='Noir Browser installer and uninstaller.')
    parser.add_argument('--uninstall', action='store_true', help='uninstall instead of installing')
    parser.add_argument('--profile', metavar='PATH', help='profile folder (skips browser/profile detection)')
    parser.add_argument('--install-path', metavar='PATH',
                        help='browser install folder; needed to remove fx-autoconfig program files')
    parser.add_argument('--full', action='store_true', help='uninstall: also remove fx-autoconfig')
    parser.add_argument('--clean-prefs', action='store_true',
                        help='uninstall: also remove natsumi.*/userChromeJS.* prefs from prefs.js (Firefox must be closed)')
    parser.add_argument('--yes', action='store_true', help='uninstall: skip confirmation prompts')
    parser.add_argument('--dry-run', action='store_true', help='uninstall: show what would be removed')
    return parser.parse_args()

if __name__ == '__main__':
    should_prompt_exit = True
    args = parse_args()
    try:
        if os.path.isdir('.noir-installer'):
            shutil.rmtree('.noir-installer')
        print('Welcome to the Noir installer! >w<')
        action = 'uninstall' if args.uninstall else 'install'
        if not args.uninstall and not args.profile:
            print('1. Install Noir')
            print('2. Uninstall Noir')
            action = 'uninstall' if input().strip() == '2' else 'install'

        if action == 'uninstall':
            uninstall_main(args)
        else:
            if args.profile:
                print('[WARN] --profile only applies to uninstalling and will be ignored.')
            main()

        if os.path.exists('.noir-installer'):
            shutil.rmtree('.noir-installer')
    except KeyboardInterrupt:
        if os.path.exists('.noir-installer'):
            shutil.rmtree('.noir-installer')
        should_prompt_exit = False
    except SystemExit:
        if os.path.exists('.noir-installer'):
            shutil.rmtree('.noir-installer')
        should_prompt_exit = False
    except EOFError:
        # stdin closed (piped/scripted run) - exit cleanly
        if os.path.exists('.noir-installer'):
            shutil.rmtree('.noir-installer')
        should_prompt_exit = False
    except:
        if os.path.exists('.noir-installer'):
            shutil.rmtree('.noir-installer')
        traceback.print_exc()

    if should_prompt_exit and sys.stdin.isatty():
        print('Press enter to exit:')
        input()
