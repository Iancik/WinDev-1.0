<?php
/**
 * WinDev API — conversie KOS ZIP/RAR -> Deviz360 XLSX
 */
declare(strict_types=1);

require dirname(__DIR__) . '/config.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    jsonError('Metodă nepermisă.', 405);
}

if (!isset($_FILES['kos_zip']) || $_FILES['kos_zip']['error'] !== UPLOAD_ERR_OK) {
    jsonError('Încărcați o arhivă ZIP sau RAR validă.');
}

$upload = $_FILES['kos_zip'];
if ($upload['size'] > $MAX_UPLOAD_BYTES) {
    jsonError('Arhiva depășește 80 MB.');
}

$ext = strtolower(pathinfo($upload['name'], PATHINFO_EXTENSION));
if (!in_array($ext, ['zip', 'rar'], true)) {
    jsonError('Acceptăm doar arhive ZIP sau RAR cu folderul KOS.');
}

$stagingDir = sys_get_temp_dir() . DIRECTORY_SEPARATOR . 'windev_up_' . bin2hex(random_bytes(8));
$workDir = '';
$archivePath = $stagingDir . DIRECTORY_SEPARATOR . 'upload.' . $ext;

if (!mkdir($stagingDir, 0700, true) && !is_dir($stagingDir)) {
    jsonError('Nu s-a putut crea director temporar.');
}

try {
    if (!move_uploaded_file($upload['tmp_name'], $archivePath)) {
        throw new RuntimeException('Eroare la salvarea fișierului.');
    }

    $extractScript = $WINDEV_ROOT . DIRECTORY_SEPARATOR . 'extract_kos.py';
    $extractCmd = escapeshellarg($PYTHON) . ' ' . escapeshellarg($extractScript)
        . ' ' . escapeshellarg($archivePath)
        . ' ' . escapeshellarg($upload['name'])
        . ' --json 2>&1';

    $extractOutput = [];
    $extractCode = 0;
    exec($extractCmd, $extractOutput, $extractCode);
    $extractJson = json_decode(end($extractOutput) ?: '', true);

    if ($extractCode !== 0 || !is_array($extractJson) || empty($extractJson['ok'])) {
        $msg = is_array($extractJson) && !empty($extractJson['error'])
            ? $extractJson['error']
            : implode("\n", $extractOutput);
        throw new RuntimeException($msg ?: 'Extragerea arhivei a eșuat.');
    }

    $kosPath = $extractJson['kos_path'];
    $workDir = $extractJson['work_dir'];
    $outPath = $workDir . DIRECTORY_SEPARATOR . 'deviz360_export.xlsx';

    $script = $WINDEV_ROOT . DIRECTORY_SEPARATOR . 'convert_web.py';
    $cmd = escapeshellarg($PYTHON) . ' ' . escapeshellarg($script)
        . ' ' . escapeshellarg($kosPath)
        . ' ' . escapeshellarg($outPath)
        . ' --json 2>&1';

    $output = [];
    $code = 0;
    exec($cmd, $output, $code);
    $jsonLine = end($output) ?: '';
    $stats = json_decode($jsonLine, true);

    if ($code !== 0 || !is_array($stats) || empty($stats['ok'])) {
        $msg = is_array($stats) && !empty($stats['error']) ? $stats['error'] : implode("\n", $output);
        throw new RuntimeException($msg ?: 'Conversia a eșuat.');
    }

    if (!is_file($outPath)) {
        throw new RuntimeException('Fișierul de ieșire nu a fost generat.');
    }

    $base = pathinfo($upload['name'], PATHINFO_FILENAME);
    $base = preg_replace('/[^\w\-]+/u', '_', $base) ?: 'deviz360';
    $downloadName = $base . '_export.xlsx';

    header('Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
    header('Content-Disposition: attachment; filename="' . $downloadName . '"');
    header('Content-Length: ' . filesize($outPath));
    header('X-WinDev-Rows: ' . ($stats['rows'] ?? ''));
    header('X-WinDev-Norms: ' . ($stats['norms'] ?? ''));
    header('X-WinDev-Devizes: ' . ($stats['devizes'] ?? ''));
    header('X-WinDev-Object: ' . ($stats['obiect'] ?? ''));
    header('X-WinDev-Total: ' . ($stats['total'] ?? ''));

    readfile($outPath);
} catch (Throwable $e) {
    if ($workDir !== '') {
        cleanupDir($workDir);
    }
    cleanupDir($stagingDir);
    jsonError($e->getMessage());
}

if ($workDir !== '') {
    cleanupDir($workDir);
}
cleanupDir($stagingDir);
exit;

function cleanupDir(string $dir): void
{
    if (!is_dir($dir)) {
        return;
    }
    $items = new RecursiveIteratorIterator(
        new RecursiveDirectoryIterator($dir, FilesystemIterator::SKIP_DOTS),
        RecursiveIteratorIterator::CHILD_FIRST
    );
    foreach ($items as $item) {
        $item->isDir() ? rmdir($item->getPathname()) : unlink($item->getPathname());
    }
    rmdir($dir);
}

function jsonError(string $msg, int $code = 400): void
{
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(['ok' => false, 'error' => $msg], JSON_UNESCAPED_UNICODE);
    exit;
}
