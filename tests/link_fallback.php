<?php
// Small stand-ins exercise routing policy without a database or MediaWiki install.
namespace MediaWiki\Title {
    class Title {
        public static array $existing = [];
        public function __construct(private string $text, private int $ns=0, private string $fragment='') {}
        public static function newFromLinkTarget($target) { return $target; }
        public static function makeTitleSafe($ns, $text) { return new self($text, $ns); }
        public function getNamespace() { return $this->ns; }
        public function getFragment() { return $this->fragment; }
        public function getText() { return $this->text; }
        public function getPrefixedText() { return $this->text; }
        public function exists() { return in_array($this->text, self::$existing, true); }
    }
}
namespace {
    define('NS_MAIN', 0);
    require __DIR__ . '/../extensions/ACPediaArchive/Hooks.php';
    class TestRenderer {
        public function makeLink($title, $text, $attributes) {
            return json_encode(['target'=>$title->getText(),'text'=>$text,'attributes'=>$attributes]);
        }
    }
    function check($condition, $message) { if (!$condition) { throw new \RuntimeException($message); } }
    function render($name, $existing, $query=[], $ns=0, $fragment='') {
        \MediaWiki\Title\Title::$existing=$existing;
        $target=new \MediaWiki\Title\Title($name,$ns,$fragment);
        $text='Original label';$attributes=[];$ret=null;
        $handled=ACPediaArchiveHooks::onHtmlPageLinkRendererBegin(new TestRenderer(),$target,$text,$attributes,$query,$ret);
        return [$handled,$ret ? json_decode($ret,true) : null];
    }
    foreach (['Sold By','Dungeon'] as $suffix) {
        [$handled,$result]=render('Example/'.$suffix,['Example']);
        check($handled===false && $result['target']==='Example','Missing generated subpage should use existing parent');
        check($result['text']==='Original label','Original link label must survive');
        check(str_contains($result['attributes']['title'],'subpage unavailable'),'Fallback must explain the missing subpage');
        check(render('Example/'.$suffix,['Example','Example/'.$suffix])[0]!==false,'Existing subpage must survive');
    }
    check(render('Example/Sold By',[])[0]!==false,'Do not create a fallback to a missing parent');
    check(render('Example/Sold By',['Example'],['action'=>'edit'])[0]!==false,'Do not rewrite edit links');
    check(render('Example/Walkthrough',['Example'])[0]!==false,'Do not rewrite arbitrary subpages');
    check(render('Example/Dungeon',['Example'],[],6)[0]!==false,'Do not rewrite files or other namespaces');
    check(render('Example/Dungeon',['Example'],[],0,'section')[0]!==false,'Do not rewrite fragment links');
    echo "PASS: missing-subpage fallback, existing targets, labels, explanations, namespaces, queries and fragments\n";
}
