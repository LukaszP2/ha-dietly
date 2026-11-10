#!/bin/bash
set -e

if [ -z "$1" ]; then
    echo "Użycie: ./release.sh <wersja> [opis]"
    echo "Przykład: ./release.sh 0.1.0 'Pierwsze stabilne wydanie'"
    exit 1
fi

NEW_VER="$1"
MSG="${2:-Wydanie v${NEW_VER}}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST="${REPO_DIR}/custom_components/dietly/manifest.json"

python3 -c "
import json
with open('${MANIFEST}', 'r') as f:
    d = json.load(f)
d['version'] = '${NEW_VER}'
order = {'domain': 0, 'name': 1}
sorted_d = dict(sorted(d.items(), key=lambda x: (order.get(x[0], 2), x[0])))
with open('${MANIFEST}', 'w') as f:
    json.dump(sorted_d, f, indent=2, ensure_ascii=False)
    f.write('\n')
"

if [ -d "${REPO_DIR}/blueprints/automation/dietly" ]; then
    mkdir -p "${REPO_DIR}/custom_components/dietly/blueprints"
    for f in "${REPO_DIR}/blueprints/automation/dietly/"*.yaml; do
        target="${REPO_DIR}/custom_components/dietly/blueprints/$(basename "$f")"
        if [ ! -e "$target" ] || ! cmp -s "$f" "$target"; then
            cp --remove-destination -f "$f" "$target"
        fi
    done
fi

git -C "${REPO_DIR}" add .
git -C "${REPO_DIR}" commit -m "Bump version to ${NEW_VER}: ${MSG}" || true
git -C "${REPO_DIR}" tag -f -a "v${NEW_VER}" -m "${MSG}"
git -C "${REPO_DIR}" push origin HEAD --follow-tags
echo "Wydanie v${NEW_VER} zostało wysłane na GitHub!"
