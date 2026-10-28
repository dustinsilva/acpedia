<?php
// Execute the real maintenance writer with a small in-memory wiki. No database writes.
namespace MediaWiki\Maintenance {
    class Maintenance {
        public function __construct() {}
        public static array $options=[];
        public static $services;
        public static string $output='';
        public function addDescription($v) {}
        public function addOption(...$v) {}
        public function hasOption($key) { return !empty(self::$options[$key]); }
        public function getServiceContainer() { return self::$services; }
        public function output($v) { self::$output.=$v; }
        public function fatalError($v) { throw new \RuntimeException($v); }
    }
}
namespace MediaWiki\User {
    class User {
        public static int $created=0;
        public static function newSystemUser(...$args) { self::$created++; return new self(); }
        public static function newFromName($name) { return new self(); }
    }
}
namespace MediaWiki\CommentStore {
    class CommentStoreComment { public static function newUnsavedComment($text) { return $text; } }
}
namespace MediaWiki\Content {
    class ContentHandler { public static function makeContent($text,$title) { return $text; } }
}
namespace MediaWiki\Revision { class SlotRecord { const MAIN='main'; } }
namespace {
    define('NS_FILE',6);define('EDIT_NEW',1);define('EDIT_FORCE_BOT',2);
    class AliasTitle {
        public function __construct(public string $name) {}
        public function equals($other) { return $this->name===$other->name; }
        public function getPrefixedText() { return 'File:'.$this->name; }
    }
    class AliasFile { public function __construct(public string $name) {} public function getPath() { return $this->name; } }
    class AliasRepo {
        public array $files=[];public array $pages=[];public array $unavailable=[];public array $conflicts=[];public int $writes=0;
        public function getLocalRepo() { return $this; }
        public function findFile($title) {
            if (isset($this->files[$title->name])) { return new AliasFile($title->name); }
            $text=$this->pages[$title->name]??'';
            if (preg_match('/^#REDIRECT \[\[File:(.+)\]\]/',$text,$m) && isset($this->files[$m[1]])) { return new AliasFile($m[1]); }
            return false;
        }
        public function fileExists($path) { return !isset($this->unavailable[$path]); }
        public function makeTitleSafe($ns,$name) { return new AliasTitle($name); }
        public function newFromTitle($title) { return new AliasPage($this,$title); }
        public function getRepoGroup() { return $this; }
        public function getTitleFactory() { return $this; }
        public function getWikiPageFactory() { return $this; }
    }
    class AliasPage {
        public function __construct(private $repo,private $title) {}
        public function newPageUpdater($user) { return new AliasUpdater($this->repo,$this->title); }
    }
    class AliasUpdater {
        private bool $started=false;private bool $ok=false;private string $text='';
        public function __construct(private $repo,private $title) {}
        public function grabParentRevision() { $this->started=true;return isset($this->repo->pages[$this->title->name])?(object)[]:null; }
        public function setContent($slot,$text) { $this->text=$text; }
        public function saveRevision($comment,$flags) {
            if (!$this->started || !($flags&EDIT_NEW)) { throw new \RuntimeException('Creation must start a CAS bracket and require a new page'); }
            if (isset($this->repo->conflicts[$this->title->name])) { return; }
            if (isset($this->repo->pages[$this->title->name])) { throw new \RuntimeException('Existing page overwrite'); }
            $this->repo->pages[$this->title->name]=$this->text;$this->repo->writes++;$this->ok=true;
        }
        public function getStatus() { return $this; }
        public function isOK() { return $this->ok; }
    }
    function check($value,$message) { if (!$value) { throw new \RuntimeException($message); } }
    $temp=sys_get_temp_dir().'/acpedia-alias-test-'.getmypid();mkdir($temp.'/maintenance',0750,true);
    file_put_contents($temp.'/maintenance/Maintenance.php','<?php');file_put_contents($temp.'/noop.php','<?php');
    define('RUN_MAINTENANCE_IF_MAIN',$temp.'/noop.php');putenv('ACPEDIA_WEBROOT='.$temp);
    require __DIR__.'/../scripts/repair-salvage-icons.php';
    $map=json_decode(file_get_contents(__DIR__.'/../config/salvage-icon-aliases.json'),true);
    $repo=new AliasRepo();foreach ($map as $target) { $repo->files[$target]=true; }
    $names=array_keys($map);$repo->files[$names[0]]=true;
    $repo->pages[$names[1]]='Existing description; preserve me';
    $repo->unavailable[$map[$names[2]]]=true;$repo->conflicts[$names[3]]=true;
    \MediaWiki\Maintenance\Maintenance::$services=$repo;
    try { (new RepairACPediaSalvageIcons())->execute(); } catch (\RuntimeException $e) { check(str_contains($e->getMessage(),'require review'),'Unexpected preview error'); }
    check($repo->writes===0 && \MediaWiki\User\User::$created===0,'Preview must not save content or create users');
    \MediaWiki\Maintenance\Maintenance::$options=['apply'=>true];
    try { (new RepairACPediaSalvageIcons())->execute(); } catch (\RuntimeException $e) { check(str_contains($e->getMessage(),'require review'),'Unexpected apply error'); }
    check($repo->writes===count($map)-4,'Create only eligible aliases');
    check($repo->pages[$names[1]]==='Existing description; preserve me','Existing description changed');
    check(!isset($repo->pages[$names[2]]) && !isset($repo->pages[$names[3]]),'Missing target or conflict must not be saved');
    check($repo->pages['Emerald Salvage Icon.png']==="#REDIRECT [[File:Salvaged Emerald Icon.png]]\n",'Emerald alias target is incorrect');
    $writes=$repo->writes;
    try { (new RepairACPediaSalvageIcons())->execute(); } catch (\RuntimeException $e) {}
    check($repo->writes===$writes,'Repeated application must not rewrite aliases');
    unlink($temp.'/maintenance/Maintenance.php');unlink($temp.'/noop.php');rmdir($temp.'/maintenance');rmdir($temp);
    echo "PASS: read-only preview, existing files/descriptions, missing storage, concurrent conflicts, Emerald redirect and idempotent reruns\n";
}
