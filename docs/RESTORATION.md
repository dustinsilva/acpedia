# Restoration status and known limits

The restoration uses the original ACPedia backup dated June 15, 2021, the February 17, 2018 base image archive and its supplement through January 14, 2024. It does not mix in newer Fandom text.

## Restored and checked

- All **53,964 archived page records** imported using MediaWiki's native XML importer.
- **57,886 unique image records** registered locally using native MediaWiki MIME/metadata/storage services. The source contains duplicate names/canonical spellings; raw source record count is not the unique record count.
- Original Vector layout, Common/Vector styling, logo, homepage banner, icon grid and nested navigation.
- Homepage: all **31 article-content images loaded** in a headless Edge browser; no JavaScript page errors.
- Holtburg Dungeon, Sword of Lost Light Quest and Olthoi Legionary render without detected expression/parser-function errors.
- Full-text search index rebuilt for the restored pages.
- Five archive safety and index-merge tests passed; checked PHP files passed syntax validation.
- Full historical import completed. The source contains 274,502 revision records. Local revision totals also include import/restoration records and are not an exact source-record count.
- Browser checks passed for historical revisions, full-text search, representative categories, a recovered dungeon map, and denial of private configuration/credential paths.

## Work still being verified

The corpus-wide category/backlink rebuild is running in isolated database snapshots. Completed ranges are merged with link target IDs remapped by namespace/title. `.data/links-rebuilt.ok` is written only after full coverage and a database integrity check. Representative categories already pass the browser check; this does not establish completion of the full-corpus rebuild.

## Differences from a perfect original-site copy

- Backup-era content is preserved. Changes made after the text backup are not reconstructed from guesses.
- The base archive did not preserve complete File-page/upload history. Media registered by the batch restorer have explicit restoration provenance, not invented upload credits or historical timestamps. The supplement's actual 37 File-page records are imported separately.
- Three original filenames contain characters Windows cannot represent (`"` or `?`). Their names are recorded in the ignored local image manifest. Linux staging preserves them. Do not claim a zero-missing-file Windows restoration.
- The original MenuSidebar dependency has been replaced by a small, tested compatibility extension that reads the original sidebar data. Unreviewed archived JavaScript and analytics are not enabled.
- Legacy forum/custom extension behavior, historical external links and external MobTracker services may require additional compatibility work. Original wide tables remain wide on phones, matching legacy Vector rather than applying an unrelated redesign.
- Public hosting is deferred: the owner confirmed it has not been provisioned yet. No hosting or DNS configuration was changed. The local preview works independently of the eventual host.

## Runtime and data

Source checksums, public backup IDs and extension commits are in `sources.lock.json`. The PHP/MediaWiki packages, SQLite database, original media and import logs are in ignored local directories. Run `python scripts/status.py` to inspect current local row counts. These generated data are not part of the Git repository and must be transferred or reconstructed separately on a host.
