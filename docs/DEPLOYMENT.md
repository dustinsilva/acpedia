# Deployment: acpedia.celestro.com

The local restoration runs real MediaWiki. It needs a PHP host and persistent database/media storage; it cannot run on GitHub Pages or a JavaScript-only static host.

## Domain observations

The public check on October 25, 2026 resolved the domain to Cloudflare addresses and returned HTTP **526**. Cloudflare documents this as failure to validate the origin server's SSL certificate: https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-526/ . Confirm the origin has a valid certificate covering `acpedia.celestro.com`, the complete certificate chain, and a working HTTPS virtual host. Retain strict certificate validation. We have not changed DNS, certificate settings, or hosting configuration.

The owner clarified that hosting for this subdomain is not in place yet. The provider/control panel, document root, server access method and PHP/database capabilities can be selected later; the earlier 526 was a pre-deployment observation, not a deployed-wiki error. Never commit hosting credentials or paste private keys into the repository.

## Host requirements

- A maintained PHP release supported by MediaWiki 1.43; the local verified runtime is PHP 8.3.36.
- PHP intl, mbstring, XML/DOM, fileinfo, openssl, JSON, session, GD and a supported database extension.
- Persistent media storage, CLI PHP for imports and maintenance jobs, sufficient disk for backups/database/media and a staged test import.
- MariaDB/MySQL is the usual production choice. The tested local restoration uses SQLite; an SQLite file is not a MySQL dump. A MariaDB deployment must import XML/media into that database or use a deliberate tested migration, rather than copying an SQLite file into MySQL.

## Setup on a PHP host

1. Take a snapshot of any existing site/database. Create a staging virtual host; do not overwrite unrelated existing files.
2. Download the pinned MediaWiki 1.43.11 distribution from the official URL in `sources.lock.json` and verify its hash. Install Variables and LabeledSectionTransclusion at the pinned commits and keep upstream license files.
3. Install MediaWiki for `https://acpedia.celestro.com`, using the host's database. Keep `LocalSettings.php` and database credentials out of Git. Copy the repository's `extensions/ACPediaArchive` into the installation and make the repository configuration readable to PHP.
4. Include `config/RestorationSettings.php` from the host's generated `LocalSettings.php`. Set `ACPEDIA_SERVER=https://acpedia.celestro.com` and `ACPEDIA_DATA` to a private persistent data directory. Place restored media in `ACPEDIA_DATA/images`. Adjust the compatibility-extension path if the source checkout is separate from the web root.
5. Import the ACPedia history XML from the pinned source backup with MediaWiki's `maintenance/run.php importDump --no-updates --username-prefix acpedia-archive`. The source is a tar.gz bundle; select its `*-history.xml` member, not the entire tar file. The local `scripts/import-history.py` demonstrates streaming it to the importer.
6. Stage the original base images and supplement using `scripts/prepare-images.py` (on Linux this also preserves three filenames Windows cannot represent). Set `ACPEDIA_WEBROOT` to the MediaWiki directory; run `php scripts/register-images.php --source /path/to/image-source`. The script uses MediaWiki 1.43's native MIME/metadata/storage services and batch inserts. It is an internal-API maintenance tool pinned to this runtime; validate before changing MediaWiki versions. Import the supplement's File-page XML separately.
7. Rebuild search (`rebuildtextindex`), links/categories (`refreshLinks`), and site statistics (`initSiteStats --update`). Drain necessary jobs using the host's CLI scheduler. Keep editing/upload permissions restricted until deliberately configured.
8. Route `/wiki/<title>` to `index.php?title=<title>`, serve `/images` from the persistent media directory, and serve `/restoration-assets/wiki.png` from `public/wiki.png`. Existing `index.php`, `api.php`, `load.php` and media resources must remain accessible. Serve only verified image/media types from uploads; never execute PHP or other scripts there. Do not expose `.data`, backups, databases or credentials.
9. Run the browser smoke checks against staging, verify a range of quests/dungeons/creatures/history/category pages and maps, then switch the virtual host/DNS deliberately. Confirm the public HTTPS certificate and HTTP responses afterward.

## Apache rewrite example

Inside the MediaWiki document root, with mod_rewrite enabled and the private data directory outside it:

```apache
RewriteEngine On
RewriteRule ^wiki/(.*)$ index.php?title=$1 [B,QSA,L]
```

Configure `/images` and `/restoration-assets` using the hosting panel or virtual-host aliases. Disable directory listings and PHP execution in media storage. Ensure `X-Content-Type-Options: nosniff`. Do not copy the development PHP server into production.

## What is not claimed

The Linux/hosting steps have not been exercised on the unknown production host. The Windows local runtime, original content imports and browser behavior are tested separately. The repo does not contain a working public deployment credential or claim that `acpedia.celestro.com` is already restored.
