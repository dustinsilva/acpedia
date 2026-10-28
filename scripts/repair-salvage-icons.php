<?php
/** Create explicit, attributed file redirects for verified salvage naming changes. */
$webroot = getenv('ACPEDIA_WEBROOT') ?: dirname(__DIR__) . '/public';
require_once $webroot . '/maintenance/Maintenance.php';
use MediaWiki\Maintenance\Maintenance;
use MediaWiki\CommentStore\CommentStoreComment;
use MediaWiki\Content\ContentHandler;
use MediaWiki\Revision\SlotRecord;
use MediaWiki\User\User;

class RepairACPediaSalvageIcons extends Maintenance {
    public function __construct() {
        parent::__construct();
        $this->addDescription('Preview/create missing salvage file aliases; never overwrite existing pages or files.');
        $this->addOption('apply', 'Create the missing file redirect pages');
    }
    public function execute() {
        $services = $this->getServiceContainer();
        $repo = $services->getRepoGroup()->getLocalRepo();
        $map = json_decode(file_get_contents(dirname(__DIR__) . '/config/salvage-icon-aliases.json'), true, 512, JSON_THROW_ON_ERROR);
        $user = $this->hasOption('apply')
            ? User::newSystemUser('ACPedia restoration repairs', ['steal'=>true])
            : User::newFromName('RestorationAdmin');
        $created = 0; $alreadyResolved = 0; $skipped = [];
        foreach ($map as $name => $destination) {
            $title = $services->getTitleFactory()->makeTitleSafe(NS_FILE, $name);
            $target = $services->getTitleFactory()->makeTitleSafe(NS_FILE, $destination);
            if (!$title || !$target || $title->equals($target)) { $skipped[$name] = 'invalid alias'; continue; }
            if ($repo->findFile($title)) { $alreadyResolved++; continue; }
            $file = $repo->findFile($target);
            if (!$file || !$repo->fileExists($file->getPath())) { $skipped[$name] = 'target image unavailable'; continue; }
            $page = $services->getWikiPageFactory()->newFromTitle($title);
            $updater = $page->newPageUpdater($user);
            // Protect existing descriptions and concurrent creation, even on reruns.
            if ($updater->grabParentRevision()) { $skipped[$name] = 'existing page requires review'; continue; }
            if ($this->hasOption('apply')) {
                $updater->setContent(SlotRecord::MAIN, ContentHandler::makeContent('#REDIRECT [[' . $target->getPrefixedText() . "]]\n", $title));
                $updater->saveRevision(CommentStoreComment::newUnsavedComment(
                    'Restore renamed salvage icon reference using existing ACPedia backup image; no new artwork or original upload history claimed'
                ), EDIT_NEW | EDIT_FORCE_BOT);
                if (!$updater->getStatus()->isOK()) { $skipped[$name] = 'edit conflict or save failure'; continue; }
            }
            $created++;
            $this->output(($this->hasOption('apply') ? 'Created: ' : 'Would create: ') . $name . ' -> ' . $destination . "\n");
        }
        $this->output(json_encode(['aliases'=>$created,'already_resolved'=>$alreadyResolved,'skipped'=>$skipped,'applied'=>$this->hasOption('apply')], JSON_PRETTY_PRINT) . "\n");
        if ($skipped) { $this->fatalError('Some aliases require review; existing content was preserved.'); }
    }
}
$maintClass = RepairACPediaSalvageIcons::class;
require_once RUN_MAINTENANCE_IF_MAIN;
