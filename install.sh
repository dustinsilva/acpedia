#!/usr/bin/env bash
# Ubuntu host installation; run from the checked-out repository.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ ${EUID} -ne 0 ]]; then
  exec sudo -- bash "$PWD/install.sh" "$@"
fi
command -v apt-get >/dev/null || { echo 'This installer targets Ubuntu/Debian with Apache and MySQL already available.' >&2; exit 1; }
packages=(python3 git ca-certificates php-cli php-mysql php-intl php-mbstring php-xml php-gd php-curl)
if ! command -v python3 >/dev/null || ! command -v git >/dev/null || ! command -v php >/dev/null || ! php -r 'exit(extension_loaded("mysqli") && extension_loaded("intl") && extension_loaded("mbstring") && extension_loaded("dom") && extension_loaded("gd") && extension_loaded("curl") ? 0 : 1);'; then
  apt-get update
  apt-get install -y "${packages[@]}"
fi
exec python3 scripts/install-ubuntu.py "$@"
