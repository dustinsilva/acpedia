# Restoration status and known limits

The restoration uses the original ACPedia backup dated June 15, 2021, the February 17, 2018 base image archive and its supplement through January 14, 2024. It does not mix in newer Fandom text.

## Restored and checked

- All **53,964 archived page records** imported using MediaWiki's native XML importer.
- **57,886 unique image records** registered locally using native MediaWiki MIME/metadata/storage services. The source contains duplicate names/canonical spellings; raw source record count is not the unique record count.
- Original Vector layout, Common/Vector styling, logo, homepage banner, icon grid and nested navigation.
- Homepage: all **31 article-content images loaded** in a headless Edge browser; no JavaScript page errors.
- Holtburg Dungeon, Sword of Lost Light Quest and Olthoi Legionary render without detected expression/parser-function errors.
- Full-text search index rebuilt for the restored pages.
- Three archive traversal/checksum safety tests passed, and the PHP files checked so far passed syntax validation.

## Work still being verified

The full 274,502-revision history import and corpus-wide category/backlink rebuild are long-running maintenance operations. Their completion and the final smoke test will be recorded here after they finish. Do not treat an earlier rendered homepage as proof that every maintenance operation has completed.

## Differences from a perfect original-site copy

- Backup-era content is preserved. Changes made after the text backup are not reconstructed from guesses.
- The base archive did not preserve complete File-page/upload history. Media registered by the batch restorer have explicit restoration provenance, not invented upload credits or historical timestamps. The supplement's actual 37 File-page records are imported separately.
- Three original filenames contain characters Windows cannot represent (`"` or `?`). Their names are recorded in the ignored local image manifest. Linux staging preserves them. Do not claim a zero-missing-file Windows restoration.
- The original MenuSidebar dependency has been replaced by a small, tested compatibility extension that reads the original sidebar data. Unreviewed archived JavaScript and analytics are not enabled.
- Legacy forum/custom extension behavior, historical external links and external MobTracker services may require additional compatibility work. Original wide tables remain wide on phones, matching legacy Vector rather than applying an unrelated redesign.
- The public domain initially returned Cloudflare error 526. No origin-host access or deployment was completed at that point; the production provider and credentials must be supplied through an appropriate access method.

## Runtime and data

Source checksums, public backup IDs and extension commits are in `sources.lock.json`. The PHP/MediaWiki packages, SQLite database, original media and import logs are in ignored local directories. Run `python scripts/status.py` to inspect current local row counts. These generated data are not part of the Git repository and must be transferred or reconstructed separately on a host.
