#!/usr/bin/env python3
"""End-to-end tests for the Noir installer's uninstall flow (installer.py)."""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(tempfile.gettempdir()) / 'noir-installer-tests'
INSTALLER = str(Path(__file__).resolve().parent / 'installer.py')

def load_installer_module():
    spec = importlib.util.spec_from_file_location('noir_installer', INSTALLER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

LOADER_CHROME = """/*

This is an example userChrome.css file. Use it if you don't already have a userChrome file.
If you already have one, append the import statement below at the top of your userChrome file.

*/

@import "noir/noir.css";

/* You can import additional mods above, or add your own userchrome CSS below. */
"""
LOADER_CONTENT = '@import "noir/noir-pages.css";\n'
ORIGINAL_USER_CHROME = '/* my own config */\n#nav-bar { color: red; }\n'
FX_MANIFEST = ('content userchromejs ./\n'
               'content userscripts ../JS/\n'
               'skin userstyles classic/1.0 ../CSS/\n'
               'content userchrome ../resources/')

results = []

def check(name, condition, detail=''):
    results.append((name, bool(condition), detail))
    print(f"  {'PASS' if condition else 'FAIL'}: {name}" + (f"  [{detail}]" if detail and not condition else ''))

def build_browser():
    browser = ROOT / 'browser'
    (browser / 'defaults' / 'pref').mkdir(parents=True, exist_ok=True)
    (browser / 'config.js').write_text('// fx-autoconfig config\n')
    (browser / 'defaults' / 'pref' / 'config-prefs.js').write_text('pref("x", true);\n')
    (browser / 'librewolf.cfg').write_text('// librewolf marker\n')
    return browser

def build_profile(name, *, manifest=True, chrome_js=True, with_bak=True,
                  modified_loader=False, modified_content=False):
    profile = ROOT / name
    if profile.exists():
        shutil.rmtree(profile)
    chrome = profile / 'chrome'
    (chrome / 'noir' / 'scripts').mkdir(parents=True)
    (chrome / 'noir' / 'noir.css').write_text('/* noir skin */\n')
    (chrome / 'noir' / 'scripts' / 'alpha.uc.mjs').write_text('// alpha script\n')
    (chrome / 'noir' / 'scripts' / 'beta.sys.mjs').write_text('// beta script\n')
    (chrome / 'noir-old').mkdir(); (chrome / 'noir-old' / 'old.txt').write_text('old\n')
    (chrome / 'noir-new').mkdir(); (chrome / 'noir-new' / 'new.txt').write_text('new\n')
    (chrome / 'noir-config.css').write_text('/* config */\n')
    (chrome / 'userChrome.css').write_text(LOADER_CHROME + ('\n#my-own { color: blue; }\n' if modified_loader else ''))
    (chrome / 'userContent.css').write_text(LOADER_CONTENT + ('\nbody { background: pink; }\n' if modified_content else ''))
    if with_bak:
        (chrome / 'userChrome.css.bak').write_text(ORIGINAL_USER_CHROME)
    (chrome / 'utils').mkdir()
    if manifest:
        (chrome / 'utils' / 'chrome.manifest').write_text(
            'content userchromejs ./\ncontent userscripts ../noir/scripts/\nskin userstyles classic/1.0 ../CSS/\n'
            'content userchrome ../resources/\ncontent noir ../noir/\ncontent noir-icons ../noir/icons/')
    (chrome / 'utils' / 'module_loader.mjs').write_text('// fx-autoconfig\n')
    (chrome / 'CSS').mkdir(); (chrome / 'CSS' / 'style.css').write_text('/* css */\n')
    (chrome / 'resources').mkdir(); (chrome / 'resources' / 'f.txt').write_text('r\n')
    if chrome_js:
        js = chrome / 'JS'; js.mkdir()
        (js / 'alpha.uc.mjs').write_text('// alpha script\n')
        (js / 'beta.sys.mjs').write_text('// beta script\n')
        (js / 'mymod.uc.mjs').write_text('// user own mod\n')
    (profile / 'noir-updater-downloads').mkdir()
    (profile / 'noir-updater-downloads' / 'update.zip').write_text('zip\n')
    (profile.parent / 'librewolf.overrides.cfg').write_text('// overrides\n')
    return profile

def run(args, expect_exit=0):
    proc = subprocess.run([sys.executable, INSTALLER, *args], capture_output=True, text=True, timeout=60)
    if expect_exit is not None and proc.returncode != expect_exit:
        print(proc.stdout)
        print(proc.stderr)
    return proc

def main():
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True)
    browser = build_browser()

    # ---- Scenario 1: full cleanup, dry run leaves everything in place ----
    print('\n[Scenario 1] full cleanup, --dry-run')
    profile = build_profile('p-full')
    proc = run(['--uninstall', '--profile', str(profile), '--install-path', str(browser),
                '--full', '--yes', '--dry-run'])
    check('exit code 0', proc.returncode == 0)
    check('dry run mentions nothing changed', 'nothing was changed' in proc.stdout)
    check('dry run keeps noir folder', (profile / 'chrome' / 'noir').is_dir())
    check('dry run keeps chrome.manifest', (profile / 'chrome' / 'utils' / 'chrome.manifest').is_file())

    # ---- Scenario 2: full cleanup, real run ----
    print('\n[Scenario 2] full cleanup, real run')
    proc = run(['--uninstall', '--profile', str(profile), '--install-path', str(browser), '--full', '--yes'])
    check('exit code 0', proc.returncode == 0)
    chrome = profile / 'chrome'
    check('noir folder removed', not (chrome / 'noir').exists())
    check('noir-old removed', not (chrome / 'noir-old').exists())
    check('noir-new removed', not (chrome / 'noir-new').exists())
    check('updater downloads removed', not (profile / 'noir-updater-downloads').exists())
    check('noir-config.css removed', not (chrome / 'noir-config.css').exists())
    check('userChrome.css restored from backup', (chrome / 'userChrome.css').read_text() == ORIGINAL_USER_CHROME)
    check('userChrome.css.bak consumed', not (chrome / 'userChrome.css.bak').exists())
    check('loader-only userContent.css removed', not (chrome / 'userContent.css').exists())
    check('no stray backup for loader userChrome.css', not (chrome / 'userChrome.css.noir-backup').exists())
    check('no stray backup for loader userContent.css', not (chrome / 'userContent.css.noir-backup').exists())
    check('copied JS script alpha removed', not (chrome / 'JS' / 'alpha.uc.mjs').exists())
    check('copied JS script beta removed', not (chrome / 'JS' / 'beta.sys.mjs').exists())
    check('user JS mod kept', (chrome / 'JS' / 'mymod.uc.mjs').is_file())
    check('utils removed', not (chrome / 'utils').exists())
    check('CSS removed', not (chrome / 'CSS').exists())
    check('resources removed', not (chrome / 'resources').exists())
    check('program config.js removed', not (browser / 'config.js').exists())
    check('program config-prefs.js removed', not (browser / 'defaults' / 'pref' / 'config-prefs.js').exists())
    check('librewolf overrides removed', not (ROOT / 'librewolf.overrides.cfg').exists())

    # ---- Scenario 3: Noir-only uninstall restores fx-autoconfig manifest ----
    print('\n[Scenario 3] Noir-only (keep fx-autoconfig)')
    browser = build_browser()  # scenario 2 removed the program files
    profile = build_profile('p-noir')
    proc = run(['--uninstall', '--profile', str(profile), '--yes'])
    check('exit code 0', proc.returncode == 0)
    chrome = profile / 'chrome'
    check('noir folder removed', not (chrome / 'noir').exists())
    check('utils kept', (chrome / 'utils' / 'module_loader.mjs').is_file())
    check('CSS kept', (chrome / 'CSS' / 'style.css').is_file())
    check('resources kept', (chrome / 'resources' / 'f.txt').is_file())
    check('program config.js kept', (browser / 'config.js').is_file())
    check('manifest restored to fx-autoconfig default', (chrome / 'utils' / 'chrome.manifest').read_text() == FX_MANIFEST)
    check('userChrome.css restored', (chrome / 'userChrome.css').read_text() == ORIGINAL_USER_CHROME)
    check('copied JS script alpha removed', not (chrome / 'JS' / 'alpha.uc.mjs').exists())
    check('user JS mod kept', (chrome / 'JS' / 'mymod.uc.mjs').is_file())

    # ---- Scenario 4: customized loader + backup present ----
    print('\n[Scenario 4] customized userChrome.css with .bak present')
    profile = build_profile('p-modified', modified_loader=True)
    proc = run(['--uninstall', '--profile', str(profile), '--yes'])
    chrome = profile / 'chrome'
    check('exit code 0', proc.returncode == 0)
    check('original restored', (chrome / 'userChrome.css').read_text() == ORIGINAL_USER_CHROME)
    check('customized version kept as .noir-backup',
          (chrome / 'userChrome.css.noir-backup').is_file()
          and '#my-own' in (chrome / 'userChrome.css.noir-backup').read_text())

    # ---- Scenario 5: customized userContent.css without .bak ----
    print('\n[Scenario 5] customized userContent.css without backup')
    profile = build_profile('p-modified2', with_bak=False, modified_content=True)
    proc = run(['--uninstall', '--profile', str(profile), '--yes'])
    chrome = profile / 'chrome'
    check('exit code 0', proc.returncode == 0)
    check('customized userContent kept as .noir-backup',
          (chrome / 'userContent.css.noir-backup').is_file()
          and 'pink' in (chrome / 'userContent.css.noir-backup').read_text())
    check('userContent.css removed', not (chrome / 'userContent.css').exists())
    check('loader-only userChrome.css removed', not (chrome / 'userChrome.css').exists())

    # ---- Scenario 6: nothing installed ----
    print('\n[Scenario 6] nothing installed')
    empty = ROOT / 'p-empty' / 'chrome'
    empty.mkdir(parents=True)
    proc = run(['--uninstall', '--profile', str(ROOT / 'p-empty'), '--yes'])
    check('exit code 0', proc.returncode == 0)
    check('reports nothing to uninstall', 'Nothing to uninstall' in proc.stdout)

    # ---- Scenario 7: permission denied is reported, not a crash ----
    print('\n[Scenario 7] permission denied handling')
    profile = ROOT / 'p-perm'
    chrome = profile / 'chrome'
    chrome.mkdir(parents=True)
    (chrome / 'noir-config.css').write_text('/* cfg */\n')
    os.chmod(chrome, 0o555)
    try:
        proc = run(['--uninstall', '--profile', str(profile), '--yes'])
        check('exit code 0', proc.returncode == 0)
        check('permission skip reported', '[SKIP]' in proc.stdout and 'permission denied' in proc.stdout)
        check('sudo hint printed', 'sudo/administrator' in proc.stdout)
        check('file kept', (chrome / 'noir-config.css').is_file())
    finally:
        os.chmod(chrome, 0o755)

    # ---- Scenario 8: unrelated user file is left untouched ----
    print('\n[Scenario 8] unrelated userChrome.css without Noir reference')
    profile = ROOT / 'p-foreign'
    chrome = profile / 'chrome'
    (chrome / 'noir').mkdir(parents=True)
    (chrome / 'noir' / 'noir.css').write_text('/* skin */\n')
    (chrome / 'userChrome.css').write_text('@import "my-other-mod.css";\n')
    proc = run(['--uninstall', '--profile', str(profile), '--yes'])
    check('exit code 0', proc.returncode == 0)
    check('foreign file kept', (chrome / 'userChrome.css').is_file()
          and 'my-other-mod' in (chrome / 'userChrome.css').read_text())
    check('no backup created for foreign file', not (chrome / 'userChrome.css.noir-backup').exists())
    check('noir folder still removed', not (chrome / 'noir').exists())

    # ---- Scenario 9: prefs cleanup (full) ----
    print('\n[Scenario 9] --clean-prefs with --full')
    profile = build_profile('p-prefs')
    prefs = profile / 'prefs.js'
    prefs.write_text(
        '// Mozilla User Preferences\n'
        'user_pref("browser.startup.page", 3);\n'
        'user_pref("natsumi.theme.type", "gradient");\n'
        'user_pref("natsumi.tabs.type", "blade");\n'
        'user_pref("userChromeJS.enabled", true);\n'
        'user_pref("userChromeJS.scriptsDisabled", "[]");\n'
        'user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);\n')
    proc = run(['--uninstall', '--profile', str(profile), '--full', '--yes', '--clean-prefs'])
    check('exit code 0', proc.returncode == 0)
    text = prefs.read_text()
    check('natsumi prefs removed', 'natsumi.' not in text)
    check('userChromeJS prefs removed', 'userChromeJS.' not in text)
    check('unrelated prefs kept', 'browser.startup.page' in text
          and 'toolkit.legacyUserProfileCustomizations.stylesheets' in text)
    check('prefs backup created', (profile / 'prefs.js.noir-backup').is_file())

    # ---- Scenario 10: prefs cleanup (Noir-only keeps userChromeJS prefs) ----
    print('\n[Scenario 10] --clean-prefs without --full')
    profile = build_profile('p-prefs2')
    prefs = profile / 'prefs.js'
    prefs.write_text(
        'user_pref("natsumi.theme.type", "gradient");\n'
        'user_pref("userChromeJS.enabled", true);\n')
    proc = run(['--uninstall', '--profile', str(profile), '--yes', '--clean-prefs'])
    check('exit code 0', proc.returncode == 0)
    text = prefs.read_text()
    check('natsumi prefs removed', 'natsumi.' not in text)
    check('userChromeJS prefs kept', 'userChromeJS.enabled' in text)

    # ---- Scenario 11: runtime artifacts (user data backed up, cache deleted) ----
    print('\n[Scenario 11] runtime artifacts')
    profile = build_profile('p-runtime')
    (profile / 'noir-themes').mkdir()
    (profile / 'noir-themes' / 'my-theme.json').write_text('{"accent": "red"}\n')
    (profile / 'noir-uploads').mkdir()  # empty -> removed
    (profile / 'noir-bento-temp').mkdir()
    (profile / 'noir-bento-temp' / 'junk.tmp').write_text('junk\n')
    (profile / 'noir-shortcuts.json').write_text('{"custom": true}\n')
    proc = run(['--uninstall', '--profile', str(profile), '--yes'])
    check('exit code 0', proc.returncode == 0)
    check('theme data backed up',
          (profile / 'noir-themes.noir-backup' / 'my-theme.json').is_file())
    check('original theme dir gone', not (profile / 'noir-themes').exists())
    check('shortcuts file backed up', (profile / 'noir-shortcuts.json.noir-backup').is_file())
    check('original shortcuts file gone', not (profile / 'noir-shortcuts.json').exists())
    check('empty uploads dir removed', not (profile / 'noir-uploads').exists())
    check('bento temp removed', not (profile / 'noir-bento-temp').exists())

    # ---- Scenario 12: install manifest drives removal of unknown paths ----
    print('\n[Scenario 12] install manifest with future paths')
    profile = build_profile('p-manifest')
    chrome = profile / 'chrome'
    (chrome / 'future-loader.css').write_text('/* new feature */\n')          # not known to the uninstaller
    (chrome / 'JS' / 'gone-script.uc.mjs').write_text('// stale copy\n')      # source no longer exists
    manifest_data = {
        "manifestVersion": 1,
        "brand": "noir-browser",
        "packageVersion": "9.9.9",
        "profilePaths": ["chrome/noir", "chrome/future-loader.css",
                         "chrome/userChrome.css", "chrome/userContent.css"],
        "externalPaths": [],
        "preExisting": {"fxAutoconfigProgram": False, "fxAutoconfigProfile": False, "jsFolder": False},
        "backups": [{"path": "chrome/userChrome.css", "backup": "chrome/userChrome.css.bak"}],
        "jsCopies": ["chrome/JS/gone-script.uc.mjs"],
    }
    (chrome / '.noir-install.json').write_text(json.dumps(manifest_data))
    proc = run(['--uninstall', '--profile', str(profile), '--yes'])
    check('exit code 0', proc.returncode == 0)
    check('future file removed via manifest', not (chrome / 'future-loader.css').exists())
    check('stale JS copy backed up', (chrome / 'JS' / 'gone-script.uc.mjs.noir-backup').is_file())
    check('manifest itself removed', not (chrome / '.noir-install.json').exists())
    check('userChrome restored via manifest backup record',
          (chrome / 'userChrome.css').read_text() == ORIGINAL_USER_CHROME)

    # ---- Scenario 13: discovery of unknown noir*/noir* leftovers ----
    print('\n[Scenario 13] unknown artifact discovery')
    profile = build_profile('p-discover')
    (profile / 'noir-future-thing.json').write_text('{"future": true}\n')
    (profile / 'noir-state').mkdir()
    (profile / 'noir-state' / 'state.bin').write_text('state\n')
    (profile / 'noir-empty-future').mkdir()
    (profile / 'noir-old-thing.json.noir-backup').write_text('previous backup\n')
    proc = run(['--uninstall', '--profile', str(profile), '--yes'])
    check('exit code 0', proc.returncode == 0)
    check('unknown file backed up', (profile / 'noir-future-thing.json.noir-backup').is_file())
    check('unknown dir backed up', (profile / 'noir-state.noir-backup' / 'state.bin').is_file())
    check('empty unknown dir removed', not (profile / 'noir-empty-future').exists())
    check('previous .noir-backup untouched', (profile / 'noir-old-thing.json.noir-backup').is_file())

    # ---- Scenario 14: offline install -> uninstall round trip ----
    print('\n[Scenario 14] install -> uninstall round trip')
    roundtrip = ROOT / 'roundtrip'
    if roundtrip.exists():
        shutil.rmtree(roundtrip)
    fix = roundtrip / 'fixtures'
    # repo extraction fixture
    (fix / 'noir' / 'noir' / 'scripts').mkdir(parents=True)
    (fix / 'noir' / 'noir' / 'noir.css').write_text('/* skin */\n')
    (fix / 'noir' / 'noir' / 'scripts' / 'alpha.uc.mjs').write_text('// alpha\n')
    (fix / 'noir' / 'noir' / 'scripts' / 'beta.sys.mjs').write_text('// beta\n')
    (fix / 'noir' / 'userChrome.css').write_text(LOADER_CHROME)
    (fix / 'noir' / 'userContent.css').write_text(LOADER_CONTENT)
    (fix / 'noir' / 'noir-config.css').write_text('/* config */\n')
    # fx-autoconfig fixture
    (fix / 'fx-autoconfig' / 'program' / 'defaults' / 'pref').mkdir(parents=True)
    (fix / 'fx-autoconfig' / 'program' / 'config.js').write_text('// fxa config\n')
    (fix / 'fx-autoconfig' / 'program' / 'defaults' / 'pref' / 'config-prefs.js').write_text('pref("x", 1);\n')
    (fix / 'fx-autoconfig' / 'program' / 'defaults' / 'pref' / 'config-prefs-librewolf.js').write_text('pref("y", 1);\n')
    (fix / 'fx-autoconfig' / 'profile' / 'chrome' / 'CSS').mkdir(parents=True)
    (fix / 'fx-autoconfig' / 'profile' / 'chrome' / 'CSS' / 'style.css').write_text('/* fxa css */\n')
    (fix / 'fx-autoconfig' / 'profile' / 'chrome' / 'utils').mkdir(parents=True)
    (fix / 'fx-autoconfig' / 'profile' / 'chrome' / 'utils' / 'module_loader.mjs').write_text('// fxa\n')
    (fix / 'fx-autoconfig' / 'profile' / 'chrome' / 'resources').mkdir(parents=True)
    (fix / 'fx-autoconfig' / 'profile' / 'chrome' / 'resources' / 'r.txt').write_text('r\n')
    # fake targets
    fake_browser = roundtrip / 'browser'
    fake_browser.mkdir(parents=True)
    fake_profile = roundtrip / 'profile' / 'chrome'
    fake_profile.mkdir(parents=True)
    (fake_profile / 'JS').mkdir()
    (fake_profile / 'userChrome.css').write_text('/* my original loader */\n')

    module = load_installer_module()
    def fake_download(repository, branch, destination, is_tag=False):
        source = fix / ('noir' if destination == 'natsumi' else 'fx-autoconfig')
        shutil.copytree(source, Path('.noir-installer') / destination, dirs_exist_ok=True)

    old_cwd = os.getcwd()
    os.chdir(roundtrip)
    try:
        with mock.patch.object(module, 'download_from_git', fake_download), \
             mock.patch.object(module, 'select_browser',
                               return_value=SimpleNamespace(name='Fake', name_flatpak=None)), \
             mock.patch.object(module, 'detect_install_and_profiles',
                               return_value=(str(fake_browser), [str(roundtrip / 'profile')])), \
             mock.patch.object(module, 'select_profile', return_value=str(roundtrip / 'profile')), \
             mock.patch.object(module, 'get_admin', return_value=True), \
             mock.patch('builtins.input', side_effect=['1', 'y']), \
             mock.patch('os.system'), mock.patch.dict(os.environ, {'SUDO_USER': 'tester'}):
            with contextlib.redirect_stdout(io.StringIO()):
                module.main()
    finally:
        os.chdir(old_cwd)

    manifest_path = Path(fake_profile) / '.noir-install.json'
    check('install wrote manifest', manifest_path.is_file())
    data = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
    check('manifest records skin dir', 'chrome/noir' in data.get('profilePaths', []))
    check('manifest records JS copies',
          'chrome/JS/alpha.uc.mjs' in data.get('jsCopies', []))
    check('manifest records backup',
          {'path': 'chrome/userChrome.css', 'backup': 'chrome/userChrome.css.bak'} in data.get('backups', []))
    check('manifest records program files',
          str(fake_browser / 'config.js') in data.get('externalPaths', []))
    check('manifest records pre-existing JS folder',
          data.get('preExisting', {}).get('jsFolder') is True)

    proc = run(['--uninstall', '--profile', str(roundtrip / 'profile'),
                '--install-path', str(fake_browser), '--full', '--yes'])
    check('uninstall exit code 0', proc.returncode == 0)
    leftover = sorted(p.name for p in fake_profile.iterdir()
                      if p.name.startswith('noir') or p.name.startswith('noir'))
    check('profile clean after uninstall', leftover == [], f'leftovers={leftover}')
    check('original loader restored', (fake_profile / 'userChrome.css').read_text() == '/* my original loader */\n')
    check('program files removed', not (fake_browser / 'config.js').exists()
          and not (fake_browser / 'defaults' / 'pref' / 'config-prefs.js').exists())


    # ---- Scenario 15: legacy natsumi/ layout is still uninstalled ----
    print('\n[Scenario 15] legacy natsumi layout')
    profile = ROOT / 'p-legacy'
    chrome = profile / 'chrome'
    (chrome / 'natsumi' / 'scripts').mkdir(parents=True)
    (chrome / 'natsumi' / 'natsumi.css').write_text('/* skin */\n')
    (chrome / 'natsumi' / 'scripts' / 'alpha.uc.mjs').write_text('// alpha\n')
    (chrome / 'natsumi-old').mkdir()
    (chrome / 'natsumi-config.css').write_text('/* cfg */\n')
    (chrome / 'userChrome.css').write_text('/* comment */\n\n@import "natsumi/natsumi.css";\n')
    (chrome / 'userContent.css').write_text('@import "natsumi/natsumi-pages.css";\n')
    (chrome / 'JS').mkdir()
    (chrome / 'JS' / 'alpha.uc.mjs').write_text('// alpha\n')
    (profile / 'natsumi-themes').mkdir()
    (profile / 'natsumi-themes' / 'theme.json').write_text('{}\n')
    (profile / 'natsumi-shortcuts.json').write_text('{}\n')
    proc = run(['--uninstall', '--profile', str(profile), '--yes'])
    check('legacy exit code 0', proc.returncode == 0)
    check('legacy natsumi folder removed', not (chrome / 'natsumi').exists())
    check('legacy natsumi-old removed', not (chrome / 'natsumi-old').exists())
    check('legacy config removed', not (chrome / 'natsumi-config.css').exists())
    check('legacy loader-only userChrome.css deleted', not (chrome / 'userChrome.css').exists())
    check('legacy JS copy removed (hash match)', not (chrome / 'JS' / 'alpha.uc.mjs').exists())
    check('legacy runtime data backed up', (profile / 'natsumi-themes.noir-backup').is_dir())
    check('legacy shortcuts backed up', (profile / 'natsumi-shortcuts.json.noir-backup').is_file())


    # ---- Scenario 16: dev symlinks are handled (target must survive) ----
    print('\n[Scenario 16] symlinked dev install')
    repo_dir = ROOT / 'fake-repo'
    (repo_dir / 'noir' / 'scripts').mkdir(parents=True)
    (repo_dir / 'noir' / 'noir.css').write_text('/* skin */\n')
    (repo_dir / 'noir-config.css').write_text('/* cfg */\n')
    (repo_dir / 'userChrome.css').write_text(LOADER_CHROME)
    (repo_dir / 'userContent.css').write_text(LOADER_CONTENT)
    profile = ROOT / 'p-symlink'
    chrome = profile / 'chrome'
    chrome.mkdir(parents=True)
    os.symlink(repo_dir / 'noir', chrome / 'noir')
    os.symlink(repo_dir / 'noir-config.css', chrome / 'noir-config.css')
    os.symlink(repo_dir / 'userChrome.css', chrome / 'userChrome.css')
    os.symlink(repo_dir / 'userContent.css', chrome / 'userContent.css')
    proc = run(['--uninstall', '--profile', str(profile), '--yes'])
    check('symlink exit code 0', proc.returncode == 0)
    check('symlink to skin removed', not os.path.islink(chrome / 'noir'))
    check('symlink target survives', (repo_dir / 'noir' / 'noir.css').is_file())
    check('symlinked config removed', not os.path.islink(chrome / 'noir-config.css') and not (chrome / 'noir-config.css').exists())
    check('symlinked loaders removed', not (chrome / 'userChrome.css').exists() and not (chrome / 'userContent.css').exists())

    # ---- Scenario 17: Windows detection helpers ----
    print('\n[Scenario 17] Windows browser/profile detection')
    winroot = ROOT / 'windows'
    roaming = winroot / 'Roaming'
    firefox_root = roaming / 'Mozilla' / 'Firefox'
    profile = firefox_root / 'Profiles' / 'abc123.default-release'
    profile.mkdir(parents=True)
    (profile / 'prefs.js').write_text('// prefs\n')
    (firefox_root / 'profiles.ini').write_text(
        '[Profile0]\n'
        'Name=default-release\n'
        'IsRelative=1\n'
        'Path=Profiles/abc123.default-release\n'
        'Default=1\n'
        '\n'
        '[Profile1]\n'
        'Name=missing\n'
        'IsRelative=1\n'
        'Path=Profiles/does-not-exist\n')
    module = load_installer_module()

    with mock.patch.dict(os.environ, {'APPDATA': str(roaming)}):
        detected_root = module._get_windows_path(module.browsers[0])
        detected_profiles = module.get_profiles(detected_root)
    check('Windows Firefox profile root detected', detected_root == str(firefox_root))
    check('profiles.ini profile detected', detected_profiles == [str(profile)])
    check('direct profile path accepted', module.get_profiles(str(profile)) == [str(profile)])

    program_files = winroot / 'Program Files'
    install_dir = program_files / 'Mozilla Firefox'
    install_dir.mkdir(parents=True)
    (install_dir / 'firefox.exe').write_text('')
    with mock.patch.dict(os.environ, {
            'ProgramFiles': str(program_files),
            'ProgramFiles(x86)': '',
            'LOCALAPPDATA': str(winroot / 'LocalAppData')}):
        detected_install = module._get_windows_install_path(module.browsers[0])
    check('Windows install path detected', detected_install == str(install_dir))

    local_appdata = winroot / 'LocalAppData'
    floorp_dir = local_appdata / 'Programs' / 'Floorp'
    floorp_dir.mkdir(parents=True)
    (floorp_dir / 'floorp.exe').write_text('')
    with mock.patch.dict(os.environ, {
            'ProgramFiles': '',
            'ProgramFiles(x86)': '',
            'LOCALAPPDATA': str(local_appdata)}):
        detected_floorp = module._get_windows_install_path(module.browsers[1])
    check('Windows per-user install path detected', detected_floorp == str(floorp_dir))

    registry_install = winroot / 'Registry Firefox'
    registry_install.mkdir(parents=True)
    (registry_install / 'firefox.exe').write_text('')
    fake_registry = SimpleNamespace(
        HKEY_LOCAL_MACHINE=1,
        HKEY_CURRENT_USER=2,
        KEY_WOW64_64KEY=4,
        KEY_WOW64_32KEY=8,
        KEY_READ=16,
    )
    class FakeKey:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
    def fake_open_key(hive, key_path, reserved, access):
        if key_path == r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\firefox.exe':
            return FakeKey()
        raise OSError
    def fake_query_value(key, name):
        return (str(registry_install / 'firefox.exe'), 1)
    fake_registry.OpenKey = fake_open_key
    fake_registry.QueryValueEx = fake_query_value
    with mock.patch.dict(sys.modules, {'winreg': fake_registry}), \
         mock.patch.dict(os.environ, {
             'ProgramFiles': '',
             'ProgramFiles(x86)': '',
             'LOCALAPPDATA': ''}):
        detected_registry = module._get_windows_install_path(module.browsers[0])
    check('Windows registry install path detected', detected_registry == str(registry_install))

    waterfox_root = roaming / 'Waterfox'
    (waterfox_root / 'Profiles' / 'wolf.default').mkdir(parents=True)
    with mock.patch.dict(os.environ, {'APPDATA': str(roaming)}):
        detected_waterfox = module._get_windows_path(module.browsers[2])
    check('Windows Waterfox profile root detected', detected_waterfox == str(waterfox_root))

    with mock.patch.object(module.sys, 'platform', 'win32'), \
         mock.patch('ctypes.windll', create=True) as windll:
        windll.shell32.IsUserAnAdmin.return_value = 1
        check('Windows admin detection true', module.get_admin() is True)
        windll.shell32.IsUserAnAdmin.return_value = 0
        check('Windows admin detection false', module.get_admin() is False)

    with mock.patch.object(module.sys, 'platform', 'win32'), \
         mock.patch.object(module, '_get_windows_install_path', return_value=str(install_dir)), \
         mock.patch.object(module, '_get_windows_path', return_value=str(firefox_root)):
        detected_install, detected_profiles = module.detect_install_and_profiles(module.browsers[0])
    check('Windows detect install path', detected_install == str(install_dir))
    check('Windows detect profiles', detected_profiles == [str(profile)])

    # ---- Summary ----
    failed = [r for r in results if not r[1]]
    print(f"\n{'='*60}\n{len(results) - len(failed)}/{len(results)} checks passed")
    if failed:
        for name, _, detail in failed:
            print(f"  FAILED: {name} {detail}")
        sys.exit(1)

if __name__ == '__main__':
    main()
