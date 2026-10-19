#!/usr/bin/env bash
#
# Noir Browser - local development install.
#
# Symlinks the repo into a Firefox profile's chrome/ folder, so edits are picked
# up on the next browser restart without copying anything (and without root).
#
# Usage:
#   installer/dev-install.sh --profile <profile-dir>              # CSS-only dev setup
#   installer/dev-install.sh --profile <dir> --clean             # remove the symlinks
#   installer/dev-install.sh --profile <dir> --append <fx-autoconfig-dir>
#                                                                # + fx-autoconfig profile files
#
# CSS-only: restart Firefox and the skin is live. For the JS part (--append) you
# also need the fx-autoconfig program files in the browser install dir, which
# requires root - the script prints the exact commands.
#
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
PROFILE=""
APPEND=""
CLEAN=0

while [ $# -gt 0 ]; do
    case "$1" in
        --profile) PROFILE="${2:-}"; shift 2;;
        --append) APPEND="${2:-}"; shift 2;;
        --clean) CLEAN=1; shift;;
        -h|--help)
            sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
            exit 0;;
        *)
            echo "unknown option: $1" >&2
            exit 1;;
    esac
done

if [ -z "$PROFILE" ]; then
    echo "usage: $0 --profile <profile-dir> [--append <fx-autoconfig-dir>] [--clean]" >&2
    exit 1
fi
if [ ! -d "$PROFILE" ]; then
    echo "profile directory not found: $PROFILE" >&2
    exit 1
fi

CHROME="$PROFILE/chrome"
LINKS=(noir noir-config.css userChrome.css userContent.css)

if [ "$CLEAN" = 1 ]; then
    for item in "${LINKS[@]}"; do
        if [ -L "$CHROME/$item" ]; then
            rm "$CHROME/$item"
            echo "removed $CHROME/$item"
        fi
    done
    echo
    echo "Dev install removed. Restart Firefox to unload Noir."
    exit 0
fi

mkdir -p "$CHROME"
for item in "${LINKS[@]}"; do
    ln -sfn "$REPO/$item" "$CHROME/$item"
    echo "linked $CHROME/$item -> $REPO/$item"
done

if [ -n "$APPEND" ]; then
    if [ ! -d "$APPEND/profile/chrome/utils" ]; then
        echo "not a fx-autoconfig checkout: $APPEND" >&2
        exit 1
    fi
    for item in utils CSS resources; do
        rm -rf "${CHROME:?}/$item"
        cp -r "$APPEND/profile/chrome/$item" "$CHROME/$item"
        echo "copied fx-autoconfig/profile/chrome/$item"
    done
    cat > "$CHROME/utils/chrome.manifest" <<'EOF'
content userchromejs ./
content userscripts ../noir/scripts/
skin userstyles classic/1.0 ../CSS/
content userchrome ../resources/
content natsumi ../noir/
content natsumi-icons ../noir/icons/
EOF
    echo "wrote chrome/utils/chrome.manifest (noir mappings)"
    echo
    echo "Remaining steps for the JS part (needs root, and the browser closed):"
    echo "  sudo cp \"$APPEND/program/config.js\" /usr/lib/firefox/"
    echo "  sudo cp \"$APPEND/program/defaults/pref/config-prefs.js\" /usr/lib/firefox/defaults/pref/"
    echo "And in about:config set: userChromeJS.persistent_domcontent_callback = true"
fi

echo
echo "Done. Restart Firefox to load Noir. (chrome folder: $CHROME)"
echo
echo "Dev tip: once a release has been published, the auto-updater would replace the"
echo "noir/ symlink with a release copy. Set natsumi.updater.disabled = true in"
echo "about:config while developing."
