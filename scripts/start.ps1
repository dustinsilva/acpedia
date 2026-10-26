param([int]$Port = 8770)
$ErrorActionPreference = 'Stop'
$wikiRoot = Split-Path -Parent $PSScriptRoot
$wikiPhp = Join-Path $wikiRoot '.runtime/php/php.exe'
$wikiIni = Join-Path $wikiRoot '.runtime/php/php.ini'
$wikiWeb = Join-Path $wikiRoot '.runtime/mediawiki-1.43.11'
$env:ACPEDIA_SERVER = "http://127.0.0.1:$Port"
Write-Host "ACPedia: http://127.0.0.1:$Port/wiki/Home"
& $wikiPhp -c $wikiIni -S "127.0.0.1:$Port" -t $wikiWeb (Join-Path $PSScriptRoot 'router.php')
