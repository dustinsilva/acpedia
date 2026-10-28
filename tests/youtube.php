<?php
class Html {
    public static function rawElement($tag,$attributes,$content) {
        $html='<' . $tag;
        foreach ($attributes as $name=>$value) {
            if ($value===true) { $html.=' '.$name; }
            elseif ($value!==false) { $html.=' '.$name.'="'.htmlspecialchars((string)$value,ENT_QUOTES).'"'; }
        }
        return $html.'>'.$content.'</'.$tag.'>';
    }
    public static function element($tag,$attributes,$content) { return self::rawElement($tag,$attributes,htmlspecialchars($content,ENT_QUOTES)); }
}
require __DIR__.'/../extensions/ACPediaArchive/Hooks.php';
function check($value,$message) { if (!$value) { throw new RuntimeException($message); } }
$parser=new class { public array $hooks=[]; public function setHook($tag,$callback) { $this->hooks[$tag]=$callback; } };
ACPediaArchiveHooks::onParserFirstCallInit($parser);
check(isset($parser->hooks['youtube']),'Legacy tag must be registered');
$html=ACPediaArchiveHooks::renderYouTube(" dTqDAFNPixM\n",['src'=>'https://evil.invalid','onload'=>'alert(1)'],null,null);
check(str_contains($html,'https://www.youtube-nocookie.com/embed/dTqDAFNPixM'),'Expected archived video embed');
check(str_contains($html,'https://www.youtube.com/watch?v=dTqDAFNPixM'),'Expected direct playback fallback');
check(str_contains($html,'referrerpolicy="strict-origin-when-cross-origin"'),'YouTube must receive the origin referrer');
check(!str_contains($html,'evil.invalid') && !str_contains($html,'onload'),'Tag attributes must not inject iframe settings');
foreach (['video id goes here','https://youtube.com/watch?v=dTqDAFNPixM','<script>alert(1)</script>','123456789012',''] as $bad) {
    $html=ACPediaArchiveHooks::renderYouTube($bad,[],null,null);
    check(!str_contains($html,'iframe') && !str_contains($html,$bad===''?'xyz-nonexistent':$bad),'Invalid ID must not produce an embed or echo markup');
}
echo "PASS: legacy YouTube tag, archived video, playback fallback, origin referrer and rejected injection\n";
