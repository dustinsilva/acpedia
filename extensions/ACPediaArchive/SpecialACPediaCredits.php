<?php
use MediaWiki\SpecialPage\SpecialPage;
class SpecialACPediaCredits extends SpecialPage {
    public function __construct() { parent::__construct('ACPediaCredits'); }
    public function execute($subPage) {
        $this->setHeaders();
        $this->getOutput()->setPageTitle('ACPedia — Credits & preservation');
        $this->getOutput()->addHTML(self::creditsHtml());
    }
    public static function creditsHtml() {
        $community = 'ACPedia is the restored AC Community Wiki, built from the work of its original community contributors. '
            . 'Its articles, research, walkthroughs, templates, maps, images and original wiki logo retain their original creator and source credits wherever those records survive in the archives.';
        $restoration = Html::element('a', ['href'=>'https://celestro.com/'], 'Celestro')
            . ' revived this archive by restoring the site, repairing compatibility and navigation, and connecting it to new tools. '
            . '“Revived by Celestro” credits the restoration; it does not claim authorship of the original community content.';
        $history = 'See each article’s History tab for the contributor information retained in its imported revisions. '
            . 'Available page histories may be incomplete: earlier article revisions and some original image uploader records may be absent from this restoration. '
            . 'Some original upload and file-description records were not preserved in the available image archives; missing credits are not invented.';
        $sources = Html::element('a', ['href'=>'https://drive.google.com/drive/folders/1IhL4mYC3P6bojeB005XTuhcYR5ApLC4q'], 'Community-maintained wiki backup collection')
            . ': ACPedia text archive dated June 15, 2021; base image archive dated February 17, 2018; image supplement through January 14, 2024.';
        $rights = 'Recovered wiki content and artwork retain their existing rights and attribution. '
            . 'Restoration code licensing does not relicense the original articles, images, game assets, maps or logo. '
            . 'Asheron’s Call, its creators, and the individual artists and mapping authors retain their original credits.';
        $software = Html::element('a', ['href'=>'https://www.mediawiki.org/'], 'MediaWiki')
            . ' powers the site, together with its credited extensions. '
            . Html::element('a', ['href'=>'https://github.com/dustinsilva/acpedia'], 'Restoration source and detailed attribution') . '.';
        return Html::element('h2', [], 'Original community contributors') . Html::element('p', [], $community)
            . Html::element('h2', [], 'Revived by Celestro') . Html::rawElement('p', [], $restoration)
            . Html::element('h2', [], 'Contributor records and source archives') . Html::element('p', [], $history)
            . Html::rawElement('p', [], $sources)
            . Html::element('h2', [], 'Artwork, software and existing rights') . Html::element('p', [], $rights)
            . Html::rawElement('p', [], $software);
    }
}
