<?php
/** Read-only audit of indexed image references, physical storage and shared template checks. */
$webroot = getenv('ACPEDIA_WEBROOT') ?: dirname(__DIR__) . '/public';
require_once $webroot . '/maintenance/Maintenance.php';
use MediaWiki\Maintenance\Maintenance;
use MediaWiki\Revision\SlotRecord;
use MediaWiki\Title\Title;

class AuditACPediaImages extends Maintenance {
    public function __construct() {
        parent::__construct();
        $this->addDescription('Audit all indexed image references and every registered image binary without editing wiki content.');
        $this->addOption('output', 'Report directory (outside the web root)', false, true);
    }
    private function save($folder, $name, $data) {
        if (file_put_contents($folder . '/' . $name, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR)) === false) {
            $this->fatalError('Could not save ' . $name);
        }
    }
    public function execute() {
        $folder = $this->getOption('output', dirname(__DIR__) . '/.data/image-audit');
        if (!is_dir($folder) && !mkdir($folder, 0750, true)) { $this->fatalError('Could not create private report directory.'); }
        $services = $this->getServiceContainer(); $dbr = $this->getReplicaDB();
        $repo = $services->getRepoGroup()->getLocalRepo();
        $registered = 0; $storageMissing = []; $storageErrors = []; $batch = [];
        $flush = function () use (&$batch, &$storageMissing, &$storageErrors, $repo) {
            if (!$batch) { return; }
            foreach ($repo->fileExistsBatch($batch) as $name => $exists) {
                if ($exists === false) { $storageMissing[] = $name; }
                elseif ($exists !== true) { $storageErrors[] = $name; }
            }
            $batch = [];
        };
        $rows = $dbr->newSelectQueryBuilder()->select('img_name')->from('image')->caller(__METHOD__)->fetchResultSet();
        foreach ($rows as $row) {
            $file = $repo->newFile(Title::makeTitle(NS_FILE, $row->img_name));
            $batch[$row->img_name] = $file->getPath(); $registered++;
            if (count($batch) >= 500) { $flush(); }
        }
        $flush();
        $this->output("Checked $registered registered image files on storage.\n");

        // imagelinks records template-expanded references too. Rebuild it first
        // with refreshLinks for full coverage after template/import changes.
        $missing = []; $resolved = []; $referenceRows = 0;
        $rows = $dbr->newSelectQueryBuilder()
            ->select(['il_to','page_namespace','page_title'])
            ->from('imagelinks')->join('page', null, 'page_id = il_from')
            ->leftJoin('image', null, 'img_name = il_to')->where(['img_name'=>null])
            ->caller(__METHOD__)->fetchResultSet();
        foreach ($rows as $row) {
            $name = $row->il_to;
            if (!isset($missing[$name]) && !isset($resolved[$name])) {
                $file = $repo->findFile(Title::makeTitle(NS_FILE, $name));
                if ($file) { $resolved[$name] = ['file'=>$name,'resolved_to'=>$file->getName()]; }
                else { $missing[$name] = ['file'=>$name,'pages'=>[]]; }
            }
            if (isset($missing[$name])) {
                $missing[$name]['pages'][] = Title::makeTitle($row->page_namespace, $row->page_title)->getPrefixedText();
                $referenceRows++;
            }
        }
        foreach ($missing as &$item) { $item['pages'] = array_values(array_unique($item['pages'])); $item['page_count'] = count($item['pages']); }
        unset($item);
        uasort($missing, static fn($a,$b) => $b['page_count'] <=> $a['page_count']);

        $templateChecks = [];
        $rows = $dbr->newSelectQueryBuilder()->select(['page_title'])->from('page')->where(['page_namespace'=>NS_TEMPLATE])->caller(__METHOD__)->fetchResultSet();
        foreach ($rows as $row) {
            $title = Title::makeTitle(NS_TEMPLATE, $row->page_title);
            $revision = $services->getRevisionLookup()->getRevisionByTitle($title);
            $content = $revision ? $revision->getContent(SlotRecord::MAIN) : null;
            if (!$content || $content->getModel() !== CONTENT_MODEL_WIKITEXT) { continue; }
            $text = preg_replace('~<!--.*?-->|<(nowiki|pre|source|syntaxhighlight)\b[^>]*>.*?</\1\s*>~is', '', $content->serialize());
            if (preg_match_all('~\{\{\s*#ifexist\s*:\s*(?:File|Image)\s*:~i', $text, $matches)) {
                $templateChecks[] = ['template'=>$title->getPrefixedText(),'description_page_checks'=>count($matches[0])];
            }
        }
        $aliasMap = json_decode(file_get_contents(dirname(__DIR__) . '/config/salvage-icon-aliases.json'), true, 512, JSON_THROW_ON_ERROR);
        $salvageCandidates = [];
        foreach ($aliasMap as $name => $target) {
            if (isset($missing[str_replace(' ', '_', $name)])) { $salvageCandidates[$name] = $target; }
        }
        $summary = [
            'created_utc'=>gmdate('c'),'server'=>$this->getConfig()->get('Server'),
            'wiki_pages'=>(int)$dbr->newSelectQueryBuilder()->select('COUNT(*)')->from('page')->caller(__METHOD__)->fetchField(),
            'registered_images_checked'=>$registered,'registered_binaries_missing'=>count($storageMissing),
            'storage_errors'=>count($storageErrors),'missing_indexed_image_names'=>count($missing),
            'missing_indexed_image_references'=>$referenceRows,'resolved_file_aliases'=>count($resolved),
            'templates_with_description_page_checks'=>count($templateChecks),'salvage_alias_candidates'=>count($salvageCandidates),
            'scope'=>'All registered originals and all image references in the current imagelinks index, across all namespaces. Run refreshLinks first. Not an HTTP/thumbnail/browser-render audit.'
        ];
        $this->save($folder, 'summary.json', $summary);
        $this->save($folder, 'missing-image-references.json', array_values($missing));
        $this->save($folder, 'missing-storage-files.json', $storageMissing);
        $this->save($folder, 'storage-errors.json', $storageErrors);
        $this->save($folder, 'resolved-file-aliases.json', array_values($resolved));
        $this->save($folder, 'template-checks.json', $templateChecks);
        $this->save($folder, 'salvage-alias-candidates.json', $salvageCandidates);
        $this->output(json_encode($summary, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES) . "\nReports: $folder\n");
    }
}
$maintClass = AuditACPediaImages::class;
require_once RUN_MAINTENANCE_IF_MAIN;
