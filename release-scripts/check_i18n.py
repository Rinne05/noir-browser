#!/usr/bin/env python3
"""Check the Chinese translations against the preferences scripts.

Reports:
  - candidate strings that look like user-visible English but have no
    dictionary entry (possible missing translations)
  - dictionary keys that no longer appear in any source file (stale keys,
    e.g. typos or strings that were reworded upstream)

Usage: python3 release-scripts/check_i18n.py
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DICT = ROOT / 'noir/scripts/i18n-zh.sys.mjs'
SOURCES = [
    ROOT / 'noir/scripts/preferences.uc.mjs',
    ROOT / 'noir/scripts/preferences-about.uc.mjs',
    ROOT / 'noir/scripts/preferences-shortcuts.uc.mjs',
    ROOT / 'noir/scripts/preferences-sidebar.uc.mjs',
]

# Strings that are intentionally kept in English (brands, key names, ...).
KEEP_ENGLISH = {
    'Acorn', 'Alt', 'Alt (Option)', 'Backspace', 'Control', 'Ctrl', 'Del', 'Discord',
    'Enter', 'Esc', 'Fluent', 'LGBTQ+', 'Lucide', 'Meta', 'Meta (Super/Command)',
    'Noir Browser', 'Noir Stardust', 'Transgender', 'Shift', 'Blade', 'Bubble',
    'Clicky', 'Curve', 'Fusion', 'Haze', 'Material', 'Neutron', 'Origin', 'OLED',
    'Lucid', 'Tinted Haze', 'Mica', 'Mica Alt', 'Floorp Hub', 'Starlight Design 2',
    'Aero', 'Frutiger Aero', 'Borealis', 'Combines', 'Glimpse', 'Miniplayer',
    'Nova',
    'Kawaii',
    'Pride',
    'Stardust',
}

QUOTED = re.compile(r'"([^"\\\n]{2,400})"')
SPAN = re.compile(r'>([^<>{}]+)<', re.DOTALL)
IDENT = re.compile(r'^[a-z][A-Za-z0-9_.-]*$')
CSSVAL = re.compile(r'^[a-z]+(-[a-z]+)*$')
EXCLUDE = ('://', '.css', '.mjs', '.svg', '.ogg', '.png', 'url(', 'px', 'var(',
           '{', '}', '#', '</', '<', '=', ';', '\\', 'paneNatsumi', 'category-',
           'new MCChoice', 'NodeString =', 'highestPos', 'oklch(')

def looks_display(text):
    text = text.strip()
    if not text or len(text) < 2 or len(text) > 400:
        return False
    if any(fragment in text for fragment in EXCLUDE):
        return False
    if IDENT.match(text) or CSSVAL.match(text):
        return False
    if sum(c.isalpha() for c in text) < 3:
        return False
    return any(c.isupper() for c in text)

def dictionary_keys():
    text = DICT.read_text(encoding='utf-8')
    body = text[text.index('export const strings = {'):]
    keys = re.findall(r'^\s{4}"((?:[^"\\]|\\.)*)":', body, re.M)
    return {k.replace('\\"', '"').replace('\\u200d', '\u200d') for k in keys}

def candidate_strings():
    found = set()
    for path in SOURCES:
        lines = path.read_text(encoding='utf-8').split('\n')
        body = '\n'.join(lines[30:])
        for match in QUOTED.finditer(body):
            if looks_display(match.group(1)):
                found.add(match.group(1).strip())
        for match in SPAN.finditer(body):
            text = ' '.join(match.group(1).split())
            if '${' in text or not looks_display(text):
                continue
            found.add(text)
    return found

def main():
    keys = dictionary_keys()
    candidates = candidate_strings()
    missing = sorted(candidates - keys - KEEP_ENGLISH, key=str.lower)
    stale = sorted(keys - candidates - KEEP_ENGLISH, key=str.lower)

    print(f'dictionary entries: {len(keys)}')
    print(f'candidate strings:  {len(candidates)}')
    print(f'missing translations ({len(missing)}):')
    for item in missing:
        print(f'  {item!r}')
    print(f'stale dictionary keys ({len(stale)}):')
    for item in stale:
        print(f'  {item!r}')
    return 0

if __name__ == '__main__':
    sys.exit(main())
