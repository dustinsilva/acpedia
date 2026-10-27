<?php
// Loopback development router. Production deployment uses the supplied container.
$root = dirname(__DIR__);
$web = $root . '/.runtime/mediawiki-1.43.11';
$path = rawurldecode(parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) ?: '/');
header('X-Content-Type-Options: nosniff');
if ($path === '/restoration-assets/wiki.png') {
    header('Content-Type: image/png'); readfile($root . '/public/wiki.png'); exit;
}
if (str_starts_with($path, '/images/')) {
    $base = realpath($root . '/.data/images');
    $file = realpath($root . '/.data' . $path);
    $allowed = ['png','jpg','jpeg','gif','svg','pdf','ogg','webm','mp3','wav','zip'];
    if (!$base || !$file || !str_starts_with($file, $base . DIRECTORY_SEPARATOR) || !is_file($file) || !in_array(strtolower(pathinfo($file, PATHINFO_EXTENSION)), $allowed)) { http_response_code(404); exit; }
    header('Content-Type: ' . (new finfo(FILEINFO_MIME_TYPE))->file($file));
    header('Cache-Control: public,max-age=86400');
    readfile($file); exit;
}
if ($path === '/' || str_starts_with($path, '/wiki/')) {
    if ($path !== '/') { $_GET['title'] = substr($path, 6); }
    $_SERVER['SCRIPT_NAME'] = '/index.php'; $_SERVER['PHP_SELF'] = '/index.php';
    require $web . '/index.php'; exit;
}
if (in_array($path, ['/index.php','/api.php','/load.php','/thumb.php','/rest.php'])) { return false; }
$file = realpath($web . $path);
if ($file && str_starts_with($file, realpath($web) . DIRECTORY_SEPARATOR) && is_file($file) && preg_match('/\.(css|js|png|jpg|jpeg|gif|svg|ico|woff2?|ttf|map)$/i',$file)) { return false; }
http_response_code(404); echo 'Not found';
