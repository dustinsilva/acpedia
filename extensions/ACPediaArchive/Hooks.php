<?php
use MediaWiki\MediaWikiServices;
use MediaWiki\Title\Title;
class ACPediaArchiveHooks {
    public static function brandHtml() {
        return Html::rawElement('span', ['class'=>'acpedia-brand'],
            Html::element('a', ['href'=>Title::newFromText('Home')->getLocalURL()], 'ACPedia')
            . ' — ' . Html::element('a', ['href'=>'https://celestro.com/'], 'Revived by Celestro'));
    }
    public static function onSkinAddFooterLinks($skin, $key, &$items) {
        if ($key !== 'info') { return; }
        $items['acpedia-community'] = 'Original content by the ACPedia / AC Community Wiki community and credited creators. '
            . Html::element('a', ['href'=>Title::newFromText('Special:ACPediaCredits')->getLocalURL()], 'Credits & preservation')
            . ' · ' . Html::element('a', ['href'=>'https://celestro.com/'], 'Revived by Celestro');
    }
    public static function onParserFirstCallInit($parser) {
        $parser->setHook('youtube', [self::class, 'renderYouTube']);
    }
    public static function renderYouTube($input, $args, $parser, $frame) {
        $id = trim($input);
        if (!preg_match('/^[A-Za-z0-9_-]{11}$/D', $id)) {
            return Html::element('span', ['class'=>'error'], 'Invalid YouTube video ID.');
        }
        $player = Html::rawElement('iframe', [
            'src'=>'https://www.youtube-nocookie.com/embed/' . $id,
            'title'=>'YouTube tutorial video', 'width'=>560, 'height'=>315,
            'loading'=>'lazy', 'allow'=>'encrypted-media; picture-in-picture; fullscreen',
            'allowfullscreen'=>true, 'referrerpolicy'=>'strict-origin-when-cross-origin'
        ], '');
        $link = Html::element('a', [
            'href'=>'https://www.youtube.com/watch?v=' . $id,
            'target'=>'_blank', 'rel'=>'noopener'
        ], 'Watch on YouTube');
        return Html::rawElement('div', ['class'=>'acpedia-video'], $player . $link);
    }
    /** Legacy generated subpages were not preserved in the source dump.
     * Offer the existing subject page, while making the fallback explicit.
     * Never redirect existing subpages, edit links, file pages, or unknown subjects.
     */
    public static function onHtmlPageLinkRendererBegin($renderer, $target, &$text, &$attributes, &$query, &$ret) {
        if ($target->getNamespace() !== NS_MAIN || $query || $target->getFragment() !== '') { return; }
        $title = Title::newFromLinkTarget($target);
        if (!preg_match('~^(.+)/(Sold By|Dungeon)$~', $title->getText(), $match) || $title->exists()) { return; }
        $parent = Title::makeTitleSafe(NS_MAIN, $match[1]);
        if (!$parent || !$parent->exists()) { return; }
        $attributes['title'] = $parent->getPrefixedText() . ' (subject page; archived ' . $match[2] . ' subpage unavailable)';
        $attributes['class'] = trim(($attributes['class'] ?? '') . ' acpedia-archive-fallback');
        $ret = $renderer->makeLink($parent, $text ?? $title->getPrefixedText(), $attributes);
        return false;
    }
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
            if ($target === 'Home' && $label === 'ACCWiki') { $label = 'ACPedia'; }
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
    public static function onBeforePageDisplay($out, $skin) {
        $out->addSubtitle(self::brandHtml());
        $out->addModuleStyles('ext.acpedia.archive');
        $out->addModules('ext.acpedia.search');
    }
}
