#!/usr/bin/env sh
set -eu
: "${WISE_SITE:?Set WISE_SITE to your existing site folder name}"
case "$WISE_SITE" in -*|.*|*[!a-zA-Z0-9._-]*) echo 'Invalid site name' >&2; exit 2;; esac
cd /home/frappe/frappe-bench
bench --site "$WISE_SITE" execute "__import__('wise_bank_feed.deployment', fromlist=['ensure_installed']).ensure_installed()"
bench --site "$WISE_SITE" migrate
