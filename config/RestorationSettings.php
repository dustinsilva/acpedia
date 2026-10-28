<?php
// Archive content and its original appearance, on a maintained MediaWiki engine.
$wgDefaultSkin = 'vector';
$wgVectorDefaultSkinVersion = '1';
$wgArticlePath = '/wiki/$1';
$wgUsePathInfo = true;
$wgSitename = 'AC Community Wiki';
$wgMetaNamespace = 'AC_Community_Wiki';
$wgNamespaceAliases['ACCWiki'] = NS_PROJECT;
$wgExtraNamespaces[100] = 'AC2';
$wgExtraNamespaces[101] = 'AC2_talk';
$wgExtraNamespaces[110] = 'Forum';
$wgExtraNamespaces[111] = 'Forum_talk';
$wgUploadDirectory = (getenv('ACPEDIA_DATA') ?: dirname(__DIR__) . '/.data') . '/images';
$wgUploadPath = '/images';
$wgEnableUploads = false;
$wgUseImageMagick = false;
$wgFileExtensions = array_unique(array_merge($wgFileExtensions, ['gif','jpg','jpeg','png','svg','pdf','ogg','webm','mp3','wav','zip']));
$wgGroupPermissions['*']['edit'] = false;
$wgGroupPermissions['*']['createaccount'] = false;
$wgGroupPermissions['user']['edit'] = false;
$wgUseSiteJs = false; // Review archived JavaScript before enabling execution.
$wgAllowUserJs = false;
$wgAllowUserCss = false;
$wgEnableEmail = false;
$wgEnableUserEmail = false;
$wgJobRunRate = 0;
$wgShowExceptionDetails = false;
$wgMaxImageArea = 50000000;
$wgPFEnableStringFunctions = true;
foreach (['ParserFunctions','Cite','CategoryTree','ImageMap','InputBox','Variables','LabeledSectionTransclusion'] as $extension) {
    wfLoadExtension($extension);
}
$archiveExtension = dirname(__DIR__) . '/extensions/ACPediaArchive/extension.json';
if (!file_exists($archiveExtension)) { $archiveExtension = $IP . '/extensions/ACPediaArchive/extension.json'; }
wfLoadExtension('ACPediaArchive', $archiveExtension);
// Expire old rendered pages after deploying a compatibility-extension update.
// File times are stable between deployments; this is not a per-request epoch.
$archiveEpoch = gmdate('YmdHis', max(
    filemtime($archiveExtension),
    filemtime(dirname($archiveExtension) . '/Hooks.php')
));
if (empty($wgCacheEpoch) || strcmp($archiveEpoch, $wgCacheEpoch) > 0) {
    $wgCacheEpoch = $archiveEpoch;
}
// SQLite WAL supports concurrent reading during restoration; NORMAL retains transaction integrity.
if ($wgDBtype === 'sqlite') {
    $wgDBservers = [[
        'host' => '', 'user' => '', 'password' => '', 'dbname' => $wgDBname,
        'type' => 'sqlite', 'load' => 1,
        'connectionVariables' => ['synchronous'=>'NORMAL','cache_size'=>-65536],
    ]];
}
$wgLogos = ['1x'=>'/restoration-assets/wiki.png', 'icon'=>'/restoration-assets/wiki.png'];
$wgLogo = '/restoration-assets/wiki.png';
if (getenv('ACPEDIA_SERVER')) { $wgServer = getenv('ACPEDIA_SERVER'); $wgCanonicalServer = $wgServer; }
$wgGroupPermissions['sysop']['edit'] = true;
// Persistent local caches keep repeated template-heavy archive pages fast.
$wgMainCacheType = function_exists('apcu_fetch') ? CACHE_ACCEL : CACHE_DB;
$wgMessageCacheType = $wgMainCacheType;
$wgParserCacheType = CACHE_DB;
// Isolated index workers use private database snapshots while reading the same archive.
if (getenv('ACPEDIA_INDEX_DB')) {
    $wgSQLiteDataDir = getenv('ACPEDIA_INDEX_DB');
    $wgCachePrefix = 'acpedia-index-' . basename($wgSQLiteDataDir);
}
