<?php
/** Register recovered image metadata using MediaWiki's own MIME/metadata services.
 * No original file-description revisions or upload logs are invented.
 * Intended for the pinned MediaWiki 1.43 runtime; rerunnable and batch-committed.
 */
$webroot = getenv('ACPEDIA_WEBROOT') ?: dirname(__DIR__) . '/.runtime/mediawiki-1.43.11';
require_once $webroot . '/maintenance/Maintenance.php';
use MediaWiki\Maintenance\Maintenance;
use MediaWiki\User\User;
class RegisterACPediaImages extends Maintenance {
    public function __construct() {
        parent::__construct();
        $this->addDescription('Register source image binaries without inventing file-page histories.');
        $this->addOption('source', 'Directory of recovered media', true, true);
        $this->addOption('limit', 'Optional number of new records', false, true);
    }
    public function execute() {
        require_once __DIR__ . '/RecoveredFile.php';

        $services = $this->getServiceContainer(); $db = $this->getPrimaryDB();
        $repo = $services->getRepoGroup()->getLocalRepo();
        $user = User::newSystemUser('ACPedia archive restoration', ['steal'=>true]);
        $actor = $services->getActorNormalization()->acquireActorId($user, $db);
        $comment = $services->getCommentStore()->insert($db, 'img_description', 'Recovered from ACPedia image backup. Original uploader and upload time were not preserved.');
        $known = array_fill_keys($db->newSelectQueryBuilder()->select('img_name')->from('image')->caller(__METHOD__)->fetchFieldValues(), true);
        $propsReader = new MWFileProps($services->getMimeAnalyzer());
        $rows=[]; $new=0; $failures=[]; $start=microtime(true);
        foreach (new DirectoryIterator($this->getOption('source')) as $entry) {
            if (!$entry->isFile() || !preg_match('/\.(png|jpe?g|gif)$/i',$entry->getFilename())) { continue; }
            $title = $services->getTitleFactory()->makeTitleSafe(NS_FILE, $entry->getFilename());
            if (!$title) { $failures[]=$entry->getFilename(); continue; }
            $file = new ACPediaRecoveredFile($title, $repo); $name=$file->getName();
            if (isset($known[$name])) { continue; }
            $props=$propsReader->getPropsFromPath($entry->getPathname(),true);
            if (empty($props['fileExists']) || empty($props['mime'])) { $failures[]=$name; continue; }
            $status=$file->publish($entry->getPathname(),0,[]);
            if (!$status->isGood()) { $failures[]=$name; continue; }
            $file->setArchiveProperties($props);
            $rows[] = [
                'img_name'=>$name, 'img_size'=>$props['size'],
                'img_width'=>(int)($props['width']??0),'img_height'=>(int)($props['height']??0),
                'img_bits'=>(int)($props['bits']??0),'img_media_type'=>$props['media_type'],
                'img_major_mime'=>$props['major_mime'],'img_minor_mime'=>$props['minor_mime'],
                'img_timestamp'=>wfTimestampNow(),'img_metadata'=>$file->getMetadataForDb($db),
                'img_sha1'=>$props['sha1'],'img_actor'=>$actor,
            ] + $comment;
            $known[$name]=true; $new++;
            if (count($rows)>=100) { $this->flush($db,$rows); }
            if ($new%1000===0) { $this->output("Registered $new media files (".round($new/(microtime(true)-$start))."/sec)\n"); }
            if ($this->getOption('limit') && $new>=(int)$this->getOption('limit')) { break; }
        }
        $this->flush($db,$rows);
        $this->output(json_encode(['registered'=>$new,'failed'=>$failures],JSON_PRETTY_PRINT)."\n");
        if ($failures) { $this->fatalError('Some source files could not be registered.'); }
    }
    private function flush($db,&$rows) {
        if (!$rows) { return; }
        $db->newInsertQueryBuilder()->insertInto('image')->ignore()->rows($rows)->caller(__METHOD__)->execute();
        $this->getServiceContainer()->getDBLoadBalancerFactory()->commitPrimaryChanges(__METHOD__);
        $rows=[];
    }
}
$maintClass=RegisterACPediaImages::class;
require_once RUN_MAINTENANCE_IF_MAIN;
