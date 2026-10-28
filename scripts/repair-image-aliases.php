<?php
/** Restore only reviewed file aliases whose registered destination bytes still match the audit. */
$webroot = getenv('ACPEDIA_WEBROOT') ?: dirname(__DIR__) . '/public';
require_once $webroot . '/maintenance/Maintenance.php';
use MediaWiki\Maintenance\Maintenance;
use MediaWiki\CommentStore\CommentStoreComment;
use MediaWiki\Content\ContentHandler;
use MediaWiki\Revision\SlotRecord;
use MediaWiki\User\User;

class RepairACPediaImageAliases extends Maintenance {
    /* Preview is the default; an explicit apply flag enables attributed redirect creation. */
    public function __construct() {
        parent::__construct();
        $this->addDescription('Preview/apply checksum-pinned image aliases; preserve existing files and descriptions.');
        $this->addOption('apply', 'Create verified missing file redirects');
        $this->addOption('manifest', 'Reviewed JSON manifest (defaults to the shipped audited map)', false, true);
    }
    /* Revalidate title, physical bytes, and concurrent page state before each new redirect. */
    public function execute() {
        $path = $this->getOption('manifest', dirname(__DIR__) . '/config/audited-image-aliases.json');
        $manifest = json_decode(file_get_contents($path), true, 64, JSON_THROW_ON_ERROR);
        if (!is_array($manifest['aliases'] ?? null)) { $this->fatalError('Invalid alias manifest.'); }
        // Validate the entire record set before creating a system user or writing any page.
        $seen = [];
        foreach ($manifest['aliases'] as $row) {
            if (!is_string($row['source'] ?? null) || !is_string($row['target'] ?? null)
                || !preg_match('/^[a-f0-9]{40}$/D', $row['target_sha1'] ?? '')
                || !is_int($row['target_bytes'] ?? null) || $row['target_bytes'] < 1
                || isset($seen[$row['source']])) { $this->fatalError('Invalid or duplicate alias record.'); }
            $seen[$row['source']] = true;
        }
        $services = $this->getServiceContainer(); $repo = $services->getRepoGroup()->getLocalRepo();
        $user = $this->hasOption('apply')
            ? User::newSystemUser('ACPedia restoration repairs', ['steal'=>true])
            : User::newFromName('RestorationAdmin');
        $created = 0; $resolved = 0; $skipped = [];
        foreach ($manifest['aliases'] as $row) {
            $name = $row['source'];
            $title = $services->getTitleFactory()->makeTitleSafe(NS_FILE, $name);
            $target = $services->getTitleFactory()->makeTitleSafe(NS_FILE, $row['target']);
            if (!$title || !$target || $title->equals($target)) { $skipped[$name] = 'invalid title or self redirect'; continue; }
            if ($repo->findFile($title)) { $resolved++; continue; }
            $file = $repo->findFile($target);
            if (!$file || !$repo->fileExists($file->getPath())) { $skipped[$name] = 'target image unavailable'; continue; }
            $actual = @sha1_file($file->getPath());
            if ($actual === false || !hash_equals($row['target_sha1'], $actual) || @filesize($file->getPath()) !== $row['target_bytes']) {
                $skipped[$name] = 'target bytes changed or unreadable; review required'; continue;
            }
            $page = $services->getWikiPageFactory()->newFromTitle($title);
            $updater = $page->newPageUpdater($user);
            if ($updater->grabParentRevision()) { $skipped[$name] = 'existing file description preserved'; continue; }
            if ($this->hasOption('apply')) {
                $updater->setContent(SlotRecord::MAIN, ContentHandler::makeContent('#REDIRECT [[' . $target->getPrefixedText() . "]]\n", $title));
                $updater->saveRevision(CommentStoreComment::newUnsavedComment(
                    'Repair audited filename variant using checksum-verified ACPedia archive image; original artwork and contributor credit unchanged'
                ), EDIT_NEW | EDIT_FORCE_BOT);
                if (!$updater->getStatus()->isOK()) { $skipped[$name] = 'edit conflict or save failure'; continue; }
            }
            $created++;
            $this->output(($this->hasOption('apply') ? 'Created: ' : 'Would create: ') . $name . ' -> ' . $row['target'] . "\n");
        }
        $this->output(json_encode(['aliases'=>$created, 'already_resolved'=>$resolved, 'skipped'=>$skipped, 'applied'=>$this->hasOption('apply')], JSON_PRETTY_PRINT) . "\n");
        if ($skipped) { $this->fatalError('Some aliases require review; existing content was preserved.'); }
    }
}
$maintClass = RepairACPediaImageAliases::class;
require_once RUN_MAINTENANCE_IF_MAIN;
