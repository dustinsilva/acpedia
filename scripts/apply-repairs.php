<?php
/** Save new repair revisions with compare-and-swap protection. Original history stays intact. */
$webroot = getenv('ACPEDIA_WEBROOT') ?: dirname(__DIR__) . '/public';
require_once $webroot . '/maintenance/Maintenance.php';
use MediaWiki\Maintenance\Maintenance;
use MediaWiki\CommentStore\CommentStoreComment;
use MediaWiki\Content\ContentHandler;
use MediaWiki\Revision\SlotRecord;
use MediaWiki\User\User;

class ApplyACPediaRepairs extends Maintenance {
    public function __construct() {
        parent::__construct();
        $this->addDescription('Save targeted compatibility fixes, preserving source history and concurrent edits.');
        $this->addOption('plan', 'Private JSON plan containing current revision IDs and original text', true, true);
        $this->addOption('apply', 'Write the planned revisions; otherwise only validate');
    }
    public function execute() {
        $plan = json_decode(file_get_contents($this->getOption('plan')), true, 512, JSON_THROW_ON_ERROR);
        if (($plan['server'] ?? '') !== $this->getConfig()->get('Server')) {
            $this->fatalError('Repair plan belongs to a different wiki server.');
        }
        $user = $this->hasOption('apply')
            ? User::newSystemUser('ACPedia restoration repairs', ['steal'=>true])
            : User::newFromName('RestorationAdmin');
        $services = $this->getServiceContainer();
        $conflicts = []; $changed = 0;
        foreach ($plan['edits'] as $edit) {
            $title = $services->getTitleFactory()->newFromText($edit['title']);
            if (!$title) { $conflicts[] = $edit['title']; continue; }
            $page = $services->getWikiPageFactory()->newFromTitle($title);
            $updater = $page->newPageUpdater($user);
            // Starting the CAS bracket before checking content prevents a concurrent overwrite.
            $parent = $updater->grabParentRevision();
            $content = $parent ? $parent->getContent(SlotRecord::MAIN) : null;
            if (!$content || $content->getModel() !== CONTENT_MODEL_WIKITEXT) {
                $conflicts[] = $edit['title']; continue;
            }
            $before = $content->serialize();
            if ($before === $edit['after']) { continue; }
            if ($parent->getId() !== (int)$edit['base_revision'] || hash('sha256', $before) !== $edit['before_sha256']) {
                $conflicts[] = $edit['title']; continue;
            }
            if ($this->hasOption('apply')) {
                $updater->setContent(SlotRecord::MAIN, ContentHandler::makeContent($edit['after'], $title));
                $updater->saveRevision(CommentStoreComment::newUnsavedComment(
                    'Restore table counters/raw numeric operands and correct image filenames against pinned ACPedia backups; original history retained'
                ), EDIT_UPDATE | EDIT_FORCE_BOT);
                if (!$updater->getStatus()->isOK()) { $conflicts[] = $edit['title']; continue; }
            }
            $changed++;
            $this->output(($this->hasOption('apply') ? 'Repaired: ' : 'Validated: ') . $edit['title'] . "\n");
        }
        $this->output(json_encode(['pages'=>$changed,'conflicts'=>$conflicts,'applied'=>$this->hasOption('apply')], JSON_PRETTY_PRINT) . "\n");
        if ($conflicts) { $this->fatalError('Some pages changed or could not be repaired. Regenerate the plan before retrying.'); }
    }
}
$maintClass = ApplyACPediaRepairs::class;
require_once RUN_MAINTENANCE_IF_MAIN;
