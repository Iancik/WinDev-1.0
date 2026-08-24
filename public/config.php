<?php
/**
 * Configurare WinDev — ajustați căile pentru serverul dvs.
 */
declare(strict_types=1);

// Rădăcina proiectului WinDev (folderul cu convert_web.py)
$WINDEV_ROOT = dirname(__DIR__);

// Calea către interpretul Python (exemplu Linux: /usr/bin/python3)
$PYTHON = 'python';

// Limită upload ZIP (bytes)
$MAX_UPLOAD_BYTES = 80 * 1024 * 1024;
