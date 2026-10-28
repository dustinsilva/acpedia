# ACPedia restoration

Restores the original **AC Community Wiki / ACPedia** into a supported MediaWiki runtime. Intended public address: **https://acpedia.celestro.com**.

Public branding: **ACPedia — Revived by Celestro**. The original community logo,
articles and surviving contributor records remain credited. Every page includes
a community-credit footer linking to `Special:ACPediaCredits`, which distinguishes
restoration work from original authorship and documents source/history limitations.

This repository is a restoration project, not the earlier Ultimate Wiki prototype. It uses the original ACPedia article text, templates, categories, Vector skin, shared styling, logo and navigation. It does not substitute Fandom content or rewrite the archived articles.

## Ubuntu + existing Apache/MySQL: quick start

From your server's checkout of this repository:

```bash
git checkout master
git pull --ff-only
sudo ./install.sh
```

Create an **empty MySQL database and database user** first. The installer prompts
for host, database, user and password; it creates the MediaWiki tables. It downloads
the pinned runtime and ACPedia backups, restores articles/images and rebuilds indexes.
The first run needs roughly **20 GB free** and can take a substantial amount of time.
Run it in `tmux` if your SSH session might disconnect. Rerun the same command after
an interruption; successful import stages are remembered.

**Apache DocumentRoot stays `<checkout>/public`.** The installer installs MediaWiki
there and enables a narrowly scoped Apache directory configuration for its rewrite
rules. Your existing domain, virtual host and TLS configuration stay in place.
Apache must already execute PHP for this site. Root/sudo access is needed for packages,
Apache directory settings and file permissions; MySQL server installation is not changed.

- Database credentials: **`.data/LocalSettings.php`**, with a protected link at
  `public/LocalSettings.php`. Edit the private file locally; it is ignored by Git.
- Wiki administrator: `RestorationAdmin`; generated password: `.data/admin-password.txt`.
- Articles use their latest archived revisions initially. Add `--full-history` to
  also import all original historical revisions (slower).
- Optional: `--server https://other.example`, `--skip-apache` for manually managed
  directory settings, or `--skip-content` to test an empty installation first.
- Backups, images and credentials remain in `.data/`, outside the web root.
- Downloads are checked against `sources.lock.json`. Existing unrelated
  `public/index.php` installations are refused rather than overwritten.

The Ubuntu installer has automated contract/safety tests. The full Ubuntu/MySQL
restoration must still be verified on the target server; the earlier measured
content restoration was on Windows/SQLite.

## Local preview

Once restored, run:

```powershell
./scripts/start.ps1
```

Open **http://127.0.0.1:8770/wiki/Home**. Keep the launcher running while browsing. It binds only to this computer. `-Port 8771` selects another port.

## Reproduce the restoration on Windows

Requirements: Python 3, Git, Windows x64 with the Microsoft Visual C++ 2015–2022 runtime. PHP is downloaded into this checkout; system PHP settings are not changed.

```powershell
python scripts/bootstrap.py
./scripts/start.ps1
```

The bootstrap downloads the pinned backups and runtime, imports ACPedia's pages and histories, registers recovered image binaries, imports the image supplement's File-page records, and rebuilds search/link indexes. Allow about 20 GB of free storage for the source archives, live media/database and temporary isolated index snapshots. The first import takes time. Interrupted steps can be resumed; existing image records are skipped. `--latest-only` deliberately skips older revisions for a faster first restoration. Check command exit codes and run the smoke test before calling an interrupted restoration complete.

Sources and runtime versions are recorded in `sources.lock.json`. The page backup contains **53,964 page records and 274,502 revision records**; the image base and supplement provide approximately **57,900 unique media files**. `docs/RESTORATION.md` records measured local results and remaining limits.

Downloads, database files, credentials, generated configuration and cache files live in ignored `.data/` and `.runtime/`. They are deliberately not pushed to GitHub. The initial administrator password is generated locally in `.data/admin-password.txt`; anonymous editing, account creation, uploads, email and archived site JavaScript are disabled by default. Reading, search, histories, categories and media remain available.

## Deployment

See `docs/DEPLOYMENT.md`. A GitHub repository or GitHub Pages alone cannot execute MediaWiki. This restoration requires a PHP/database host with persistent storage. The domain currently resolves through Cloudflare; the initial public check returned 526 (origin SSL certificate validation failed). The owner confirmed hosting has not been provisioned yet. Hosting can be connected after reviewing the local restoration. No live hosting or DNS settings have been modified by this project.

## Original appearance and compatibility

- MediaWiki **1.43.11 LTS** with legacy Vector and ACPedia's archived Common/Vector CSS.
- Original sidebar definition (`MediaWiki:MenuSidebar`) rendered by the included `ACPediaArchive` compatibility extension, including nested menus and keyboard focus.
- ParserFunctions, Variables, LabeledSectionTransclusion, Cite, CategoryTree, InputBox and ImageMap support the archived templates.
- Original content and image provenance are preserved. File-description history and original upload metadata were excluded from the old base export and cannot be invented. Most media are registered without creating synthetic file-description revisions. The 37 file descriptions supplied with the image supplement are imported separately.
- Obsolete analytics and unreviewed JavaScript are not executed. Historical external links/services may remain unavailable. This is an archival restoration from the selected backup, not a claim to recover every edit made after June 2021.

## Checks

```powershell
python -m unittest discover -s tests -p "test_*.py"
node tests/smoke.cjs
```

The browser check requires Playwright and an installed Chromium/Edge browser. Set `ACPEDIA_NODE_MODULES` to a directory containing Playwright if it is not installed locally; `ACPEDIA_BROWSER_CHANNEL` defaults to `msedge`. `ACPEDIA_URL` defaults to the local preview address. Runtime scripts are PHP/Python and have no frontend build dependency.

## Rights

Original restoration scripts and the sidebar compatibility extension are MIT licensed. MediaWiki and bundled/external extensions retain their upstream licenses. The restored wiki content, images and recovered logo retain their existing rights; this repository does not relicense them as MIT. Keep page history, source attribution and asset provenance when deploying. See `docs/ATTRIBUTION.md`.
