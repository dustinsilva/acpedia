# Live restoration audit and targeted repairs

Audit date: October 27, 2026 (Pacific time).

## Backup comparison

The SHA-256-verified June 2021 article dump, February 2018 image dump and
2018–2024 image supplement contain 57,904 unique raster-media names. The complete
live MediaWiki image inventory contains exactly the same names: no backup image
name is missing from the site's image registry. This establishes registration,
not a byte-for-byte comparison of every publicly served file.

The site's 1,398 wanted filenames are absent under those exact names from the
pinned backups. Of those, 112 have a unique same-stem raster image with a different
extension/capitalization in the backup and on the live site. Correct references
to those existing images rather than registering guessed aliases or uploading
unrelated replacement artwork. The 12,638 wanted non-file titles are absent from
the preserved article dump too; do not invent their original contents.

All 112 proposed replacement images were fetched from the live site and their
SHA-256 hashes match the corresponding image bytes in the pinned backups.

The preview built from current live revisions proposes 251 page edits:

- 144 filename-reference corrections on 118 pages, using the 112 existing images.
- Counter/numeric compatibility fixes on 133 pages: 9,401 old `AUTOINCREMENT`
  calls and 52 category-count expression operands.

These are pre-application counts, not a claim that the public site is repaired.

## Repair behavior

`repair_content.py` replaces the missing legacy counter with the already-installed
Variables parser functions, including a fresh counter at the start of each page.
Category totals used as the first numeric operand of `#expr` gain MediaWiki's raw
`|R` flag. Comments and literal-code blocks remain untouched. Repeated runs make
no further changes.

The compatibility extension renders missing `/Sold By` and `/Dungeon` links as
links to the existing subject page, with an explanatory tooltip. Existing
subpages, missing subjects, fragment links, editing links, and other namespaces
keep their normal behavior. This is navigation fallback, not reconstructed vendor
or spawn data. The original missing targets may remain in wanted-page reports.
An extension deployment expires old rendered pages through the cache epoch.

## Preview on the Ubuntu host

Run from the ACPedia checkout after pulling the repair commit. Existing downloads
are reused after their checksums are verified. No reinstall or full reimport is
required. The comparison itself and the default repair command are read-only
with respect to the wiki.

```bash
sudo python3 scripts/compare-backup.py
sudo python3 scripts/repair-wiki.py
```

The comparison is saved to `.data/repair-report/`. Each repair preview writes a
private `.data/repairs/<timestamp>.json` with original text, base revision IDs,
replacement text and the source-backup checksums. Inspect the plan before applying.

## Apply on the Ubuntu host

```bash
sudo python3 scripts/repair-wiki.py --apply
```

The script regenerates its plan from current live revisions, confirms that each
old image is missing and its replacement exists, and then invokes the local
MediaWiki maintenance writer. Each change creates a normal attributed repair
revision. Original revisions remain available. The writer uses compare-and-swap
protection and skips/reports pages edited since planning. An interrupted run can
be rerun; already-correct content is unchanged.

For a nonstandard web root, set `ACPEDIA_WEBROOT` to the installed MediaWiki
directory; `ACPEDIA_PHP` can select the PHP executable. Do not put database
passwords on the command line.

## Verification

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
php -l scripts/apply-repairs.php
php -l extensions/ACPediaArchive/Hooks.php
php tests/link_fallback.php
```

After application, check Dungeons and Mattekar for calculation errors; verify
the corrected dungeon maps and NPC portraits; check Blacksmith Bulidurg and
Renegade Garrison links; and rerun the public wanted-file inventory. Source gaps
outside the pinned backups remain unresolved and should remain distinguishable
from recovered material.

## Follow-up: existing portraits hidden by description-page checks

Aun Ralirea's `Aun Ralirea Live.jpg` is already registered and served. However,
`Template:Creature` used `#ifexist:File:...`, which checks for the missing file
description page rather than the image binary. The same issue occurs in 14
preserved shared templates (74 checks), including Creature, NPC, Live Image,
Pet, Spell and Spawn Map. The repair now changes those checks to `Media:` while
leaving the actual `[[File:...]]` image embeddings unchanged. Images that really
are missing still use their original fallback.

These templates are included automatically when an older comparison report is
reused; no archive re-download or full comparison is required. After pulling the
follow-up commit, run the repair preview/apply commands above. An already-repaired
site should propose 14 additional template revisions. A read-only live-parser
test confirms the old Creature portrait row renders `Live.jpg`, while the
corrected row renders `Aun Ralirea Live.jpg`. Both registered and genuinely missing
file checks were tested.

Process queued template-cache updates after applying, and immediately invalidate
the reported example page:

```bash
sudo php public/maintenance/run.php runJobs --maxtime 120
sudo php public/maintenance/run.php purgeList --db-touch <<'EOF'
Aun Ralirea
EOF
```

The job runner is time-bounded; run it again if queued work remains. The purge
marks the named page stale so its next view uses the updated shared template.

## Full-site image inventory and salvage-name aliases

`audit-images.php` reads every registered image and tests its original storage
path through MediaWiki's backend. It also joins all namespaces' `imagelinks`
records against the image registry, resolves native file redirects, and records
every page using each unresolved filename. It scans all current wikitext
templates for the description-page existence checks that hid portraits. It
writes JSON reports to the private `.data/image-audit/` directory and does not
edit wiki content or indexes.

Rebuild the link index first so template-generated image names and recent repairs
are included. This pass parses the full wiki and can take substantial time; run
it in a persistent terminal session. Then run the audit:

```bash
sudo php public/maintenance/run.php refreshLinks
sudo php scripts/audit-images.php
sudo cat .data/image-audit/summary.json
```

The reports distinguish missing indexed filenames, registered files absent from
storage, storage read errors, resolved file aliases, and suspect template checks.
`missing-image-references.json` lists every affected page for each missing name.
This covers original storage and the rebuilt reference index; it does not claim
that every responsive thumbnail, external URL, CSS image or browser layout has
been tested. An empty suspect-template report is not proof of all possible
conditional rendering behavior.

For example, Tier 8 loot asks for `Emerald Salvage Icon.png`, but the preserved
image is `Salvaged Emerald Icon.png`. The material's article records the historical
rename from “Salvaged Type” to “Type Salvage”. There are 72 such existing images
under the old naming convention. The verified mapping is recorded in
`config/salvage-icon-aliases.json` and uses only the same material, icon type and
PNG format; quest-specific variants are not substituted.

Create native file redirects so shared templates and explicit file references
both resolve correctly, without rewriting item names, duplicating binaries or
claiming recovered artwork:

```bash
sudo php scripts/repair-salvage-icons.php
sudo php scripts/repair-salvage-icons.php --apply
sudo php public/maintenance/run.php runJobs --maxtime 120
sudo php public/maintenance/run.php purgeList --db-touch <<'EOF'
Loot/Tier 8
Salvage
Emerald Salvage
EOF
```

The first command only previews. Applying creates attributed repair revisions
only where the requested file and description page are absent and the exact
mapped target binary exists on storage. Existing pages/files, unavailable
targets and concurrent page creations are skipped and reported. Reruns do not
rewrite resolved aliases. Then rebuild the index and rerun the full audit above
to establish the remaining unresolved inventory.

Validation: all 72 old filenames were confirmed missing and all 72 target images
registered via the public API. `php tests/salvage_aliases.php` executes the writer
against an in-memory fixture and checks read-only preview, preservation of
existing pages/files, unavailable storage, concurrent edit failures, the Emerald
redirect and idempotent reruns. Full database/storage execution of the audit
requires running it on the Ubuntu host.

## YouTube and title suggestions

The compatibility extension now handles archived `<youtube>VIDEO_ID</youtube>`
markup. It accepts only an 11-character YouTube video ID, renders a responsive
privacy-enhanced iframe and provides a direct Watch on YouTube link. Tag
attributes cannot inject an arbitrary iframe URL or executable attributes.
Aetheria's preserved `dTqDAFNPixM` video is still available as “Asheron's Call
Spring Patch 2010: Aetheria”. Player availability remains subject to YouTube and
the video's embedding settings.

The website already has native title-prefix autocomplete. The extension now
supplements it with title-word prefix results, so `ralir` can suggest Aun Ralirea
and not just titles starting with “Ralir”. It retains native keyboard navigation,
deduplicates results, cancels stale requests and falls back to the prefix results
if the title search fails. A trailing `*`, such as `aeth*`, is supported by the
current SQL search backend; arbitrary leading/infix wildcard behavior is not
promised. No external search service or reindex is required for this UI update.

After pulling this update (once any currently running full-site maintenance is
finished), purge the named page if a cached copy still displays the literal tag:

```bash
sudo php public/maintenance/run.php purgeList --db-touch <<'EOF'
Aetheria
EOF
```

Use Special:UserLogin with username `RestorationAdmin`. Its generated password
is on the server in `.data/admin-password.txt`. The server administrator can
read that private file locally with `sudo cat`; do not copy credentials into
Git or public reports. Logged-in sysops can edit; public editing stays disabled.

Validation: YouTube hook tests cover the preserved video ID, malformed IDs,
injected attributes and the fallback link. Browser tests inject the new search
module into the live page without saving content and exercise title-word
suggestions (`ralir`), wildcard input (`aeth*`) and changing queries without stale
results. Server-side parser registration still needs post-deployment verification.

## ACPedia — Revived by Celestro

The site display name is ACPedia. A subtitle below each page heading reads
“ACPedia — Revived by Celestro” and links to the wiki home and Celestro.com.
The footer visibly credits original ACPedia/AC Community Wiki contributors and
links to `Special:ACPediaCredits`. That page identifies Celestro's restoration
role, the community backup sources, surviving contributor records, artwork and
software credits, and the limits of latest-only imports and missing image metadata.

The original logo, article text, existing footer notices and project namespace
routes are preserved. Branding uses output/skin hooks and configuration; it does
not edit imported articles or run a database migration. Pulling the branding
commit on the server activates it without rerunning the installer or image audit.

## Full image-audit follow-up — 2026-10-28

The supplied all-namespace audit checked 57,904 registered image binaries with
zero missing originals and zero storage errors. Its 2,778 unresolved names account
for 4,568 indexed page references; this is not a thumbnail/browser audit.

The checksum-verified backups contain the same 57,904 unique image names. None of
the requested missing names has an exact filename match. Reviewed alternatives
are now recorded in `config/audited-image-aliases.json`:

- 116 aliases follow conservative filename spelling/extension matches. Five
  multi-spelling cases were accepted only when all candidate binaries had the
  same live image hash; differing images and generic unknown icons were excluded.
- 65 additional aliases follow explicit image fields on the canonical item or
  creature page. Each records the source page and revision, not just a fuzzy
  filename guess. This includes the documented Gearcrafting → Item Tinkering
  Armature rename.
- The 181 aliases cover 642 references in the supplied audit. Every old name was
  verified unresolved and every target verified registered with real image bytes.
- `Name.png` (501 references) and `File.jpg` (80) are placeholder links already
  present in the 2021 text archive. They were not invented by this restoration.
  This change leaves those historical articles untouched and does not fabricate
  maps or photos. The reference counts span all namespaces and can overlap pages.
- After these candidate repairs, 2,597 reported names / 3,926 references remain;
  those figures include the two placeholders. Do not interpret the remainder as
  proven permanently lost: a differently named source or later backup may exist.

The audit comparison and live verification evidence are kept privately under
`.data/image-audit-analysis/` in the analysis workspace. A repeatable offline
filename comparison is available on the server:

```bash
cd /var/www/celestro.com/acpedia
sudo python3 scripts/analyze-image-audit.py
```

The offline comparison only produces candidates. It never edits the wiki or
turns an ambiguous match into an automatic repair.

After merging/pulling this repair, preview and apply the reviewed aliases:

```bash
cd /var/www/celestro.com/acpedia
sudo php public/maintenance/run.php ./scripts/repair-image-aliases.php
sudo php public/maintenance/run.php ./scripts/repair-image-aliases.php --apply
```

The writer rechecks physical target size and SHA-1 before each redirect, never
replaces existing media or file descriptions, and uses MediaWiki's new-page edit
conflict protection. Each alias creates an attributed repair revision; original
article text and original contributor credit remain unchanged. Reruns skip
resolved names. Any changed target, unreadable file, existing description, or
concurrent creation is reported and preserved for review. The command may apply
eligible records and report skipped records with a nonzero exit status; inspect
its summary before proceeding.

Refresh the link index and rerun the full audit afterward:

```bash
sudo php public/maintenance/run.php refreshLinks
sudo php public/maintenance/run.php ./scripts/audit-images.php
sudo cat .data/image-audit/summary.json
```

Using `run.php` with `./scripts/...` resolves paths from the current working
directory and avoids the deprecated direct-script invocation. See the
[MediaWiki runner documentation](https://www.mediawiki.org/wiki/Manual:Run.php).
Do not change ownership or permissions of the entire `.data` directory to share
a report; copy only the report to a user-readable private location.

Validation: 27 Python tests pass; PHP tests cover read-only preview, preserved
files/descriptions, missing storage, changed bytes, edit conflicts, self redirects,
duplicate manifests, and idempotent reruns. Existing salvage alias, link fallback,
and YouTube regression checks pass. Actual MediaWiki/database application still
requires running the maintenance command on the Ubuntu server.
