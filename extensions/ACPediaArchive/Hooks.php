<?php
use MediaWiki\MediaWikiServices;
class ACPediaArchiveHooks {
    public static function onSkinBuildSidebar($skin, &$bar) {
        $raw = wfMessage('menuSidebar')->inContentLanguage()->plain();
        if ($raw === '' || $raw === '⧼menusidebar⧽') { return; }
        $lines = preg_split('/\r?\n/', $raw);
        $tree = []; $stack = [];
        foreach ($lines as $line) {
            if (!preg_match('/^(\*+)\s*(.+)$/u', $line, $m)) { continue; }
            $level = strlen($m[1]); $value = trim($m[2]);
            if ($level === 1) { continue; }
            if (preg_match('/^\[\[([^\]|]+)(?:\|([^\]]+))?\]\]$/u', $value, $link)) {
                $target = $link[1]; $label = $link[2] ?? $target;
            } else { $target = $value; $label = $value; }
            $node = ['target'=>$target, 'label'=>$label, 'children'=>[]];
            $depth = $level - 2;
            if ($depth === 0 || !$stack) { $tree[] = $node; $stack = [&$tree[array_key_last($tree)]]; }
            else {
                $depth = min($depth, count($stack));
                $parent = &$stack[$depth - 1]; $parent['children'][] = $node;
                $stack = array_slice($stack, 0, $depth); $stack[] = &$parent['children'][array_key_last($parent['children'])];
                unset($parent);
            }
        }
        $bar['navigation'] = [['html'=>'<ul class="acpedia-menu">'.self::items($tree).'</ul>']];
    }
    private static function items($nodes) {
        $html = '';
        foreach ($nodes as $n) {
            $title = MediaWikiServices::getInstance()->getTitleFactory()->newFromText($n['target']);
            if (!$title) { continue; }
            $link = Html::element('a', ['href'=>$title->getLocalURL()], $n['label']);
            $children = $n['children'] ? '<ul>'.self::items($n['children']).'</ul>' : '';
            $html .= '<li'.($children ? ' class="has-submenu"' : '').'>'.$link.$children.'</li>';
        }
        return $html;
    }
    public static function onBeforePageDisplay($out, $skin) { $out->addModuleStyles('ext.acpedia.archive'); }
}
