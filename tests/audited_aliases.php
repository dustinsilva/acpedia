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
        public function getOption($key,$default=null) { return self::$options[$key] ?? $default; }
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
    class AliasFile { public function __construct(public string $name) {} public function getPath() { return $GLOBALS['aliasPaths'][$this->name] ?? $this->name; } }
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

    $temp=sys_get_temp_dir().'/acpedia-audited-alias-test-'.getmypid();mkdir($temp.'/maintenance',0750,true);
    file_put_contents($temp.'/maintenance/Maintenance.php','<?php');file_put_contents($temp.'/noop.php','<?php');
    define('RUN_MAINTENANCE_IF_MAIN',$temp.'/noop.php');putenv('ACPEDIA_WEBROOT='.$temp);
    require __DIR__.'/../scripts/repair-image-aliases.php';
    $repo=new AliasRepo();$records=[];$aliasPaths=[];
    foreach (['one','two','existing','description','missing','changed','conflict','self'] as $name) {
        $target=$name.' target.png';$source=$name.' source.png';
        $file=$temp.'/'.$name.'.png';file_put_contents($file,'verified fixture '.$name);
        $aliasPaths[$target]=$file;$repo->files[$target]=true;
        $records[]=['source'=>$source,'target'=>$target,'target_sha1'=>sha1_file($file),'target_bytes'=>filesize($file)];
    }
    $repo->files['existing source.png']=true;
    $repo->pages['description source.png']='Original contributor description';
    $repo->unavailable[$aliasPaths['missing target.png']]=true;
    file_put_contents($aliasPaths['changed target.png'],'CHANGED fixture changed');
    $repo->conflicts['conflict source.png']=true;
    $records[7]['target']=$records[7]['source'];
    $manifest=$temp.'/manifest.json';file_put_contents($manifest,json_encode(['aliases'=>$records]));
    \MediaWiki\Maintenance\Maintenance::$services=$repo;
    \MediaWiki\Maintenance\Maintenance::$options=['manifest'=>$manifest];
    try { (new RepairACPediaImageAliases())->execute(); } catch (\RuntimeException $e) { check(str_contains($e->getMessage(),'require review'),'Unexpected preview error'); }
    check($repo->writes===0 && \MediaWiki\User\User::$created===0,'Preview mutated the wiki');
    \MediaWiki\Maintenance\Maintenance::$options['apply']=true;
    try { (new RepairACPediaImageAliases())->execute(); } catch (\RuntimeException $e) { check(str_contains($e->getMessage(),'require review'),'Unexpected apply error'); }
    check($repo->writes===2,'Only two verified eligible aliases should be created');
    check($repo->pages['one source.png']==="#REDIRECT [[File:one target.png]]\n",'Wrong redirect');
    check($repo->pages['description source.png']==='Original contributor description','Description overwritten');
    foreach (['missing','changed','conflict','self'] as $name) check(!isset($repo->pages[$name.' source.png']),'Unsafe alias was created: '.$name);
    try { (new RepairACPediaImageAliases())->execute(); } catch (\RuntimeException $e) {}
    check($repo->writes===2,'Rerun rewrote redirects');
    $users=\MediaWiki\User\User::$created;$records[]=$records[0];file_put_contents($manifest,json_encode(['aliases'=>$records]));
    try { (new RepairACPediaImageAliases())->execute(); throw new \RuntimeException('Invalid manifest accepted'); }
    catch (\RuntimeException $e) { check(str_contains($e->getMessage(),'duplicate'),'Unexpected validation error'); }
    check(\MediaWiki\User\User::$created===$users && $repo->writes===2,'Invalid manifest caused a write');
    foreach (glob($temp.'/*.png') as $file) unlink($file);
    unlink($manifest);unlink($temp.'/maintenance/Maintenance.php');unlink($temp.'/noop.php');rmdir($temp.'/maintenance');rmdir($temp);
    echo "PASS: preview isolation, checksum mismatch, missing files, existing descriptions, edit conflicts, self redirects, duplicate manifests and idempotency\n";
}
