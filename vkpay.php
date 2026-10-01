<?php
/**
 * Обработчик платёжных уведомлений ВКонтакте для игры «Звездопад» (app 54698105).
 *
 * Установка:
 * 1. Залить этот файл на хостинг (например, в корень сайта).
 * 2. При желании вставить защищённый ключ в $secret_key ниже
 *    (dev.vk.com → Приложения → Звездопад → Разработка → Ключи доступа → Защищённый ключ).
 *    Пока ключ не вставлен, проверка подписи пропускается — платежи работают,
 *    но добавить ключ рекомендуется.
 * 3. В кабинете: Монетизация → Платежи → URL для платёжных уведомлений ВКонтакте —
 *    указать полный адрес этого файла, напр. http://landoc.online/vkpay.php
 *
 * Документация: https://vk.com/dev/payments_callbacks
 */

header('Content-Type: application/json; charset=utf-8');

$secret_key = ''; // <-- вставить защищённый ключ приложения сюда

// ---------- Каталог товаров (цены в голосах, как в магазине игры) ----------
$items = [
    'skin_ember'    => ['item_id' => 101, 'title' => 'Скин «Угли» — Звездопад',      'price' => 15],
    'skin_tide'     => ['item_id' => 102, 'title' => 'Скин «Прилив» — Звездопад',    'price' => 25],
    'skin_orchard'  => ['item_id' => 103, 'title' => 'Скин «Сад» — Звездопад',       'price' => 40],
    'skin_royal'    => ['item_id' => 104, 'title' => 'Скин «Регалия» — Звездопад',   'price' => 60],
    'skin_mono'     => ['item_id' => 105, 'title' => 'Скин «Монохром» — Звездопад',  'price' => 90],
    'skin_comet'    => ['item_id' => 106, 'title' => 'Скин «Комета» — Звездопад',    'price' => 120],
    'no_ads_forever'=> ['item_id' => 201, 'title' => 'Отключение рекламы навсегда — Звездопад', 'price' => 299],
    // Галерея постеров (2.1): покупка открывает все 20 фрагментов постера
    'poster_neb'     => ['item_id' => 301, 'title' => 'Постер «Туманность Ориона» — Звездопад',     'price' => 10],
    'poster_ring'    => ['item_id' => 302, 'title' => 'Постер «Кольцевая гиганта» — Звездопад',     'price' => 10],
    'poster_spiral'  => ['item_id' => 303, 'title' => 'Постер «Галактика» — Звездопад',             'price' => 15],
    'poster_comet'   => ['item_id' => 304, 'title' => 'Постер «Комета» — Звездопад',                'price' => 15],
    'poster_aurora'  => ['item_id' => 305, 'title' => 'Постер «Полярное сияние» — Звездопад',       'price' => 20],
    'poster_eclipse' => ['item_id' => 306, 'title' => 'Постер «Затмение» — Звездопад',              'price' => 20],
    'poster_hole'    => ['item_id' => 307, 'title' => 'Постер «Чёрная дыра» — Звездопад',           'price' => 25],
    'poster_cluster' => ['item_id' => 308, 'title' => 'Постер «Скопление Плеяд» — Звездопад',       'price' => 25],
    'poster_station' => ['item_id' => 309, 'title' => 'Постер «Орбитальная станция» — Звездопад',   'price' => 30],
    'poster_sunset'  => ['item_id' => 310, 'title' => 'Постер «Закат на Титане» — Звездопад',       'price' => 30],
    'poster_meteor'  => ['item_id' => 311, 'title' => 'Постер «Метеорный поток» — Звездопад',       'price' => 40],
    'poster_earth'   => ['item_id' => 312, 'title' => 'Постер «Земля из иллюминатора» — Звездопад', 'price' => 50],
];

// Проверка, что скрипт доступен (открыть файл в браузере)
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Access-Control-Allow-Origin: *');
    // ?check=USER_ID — игра спрашивает, какие товары оплачены этим пользователем.
    // Нужно для гарантированной выдачи: даже если клиент не получил ответ от VK,
    // сервер уже подтвердил заказ — товар будет выдан при следующей проверке.
    if (isset($_GET['check'])) {
        $uid = preg_replace('/\D/', '', $_GET['check']);
        $owned = [];
        $log = @file_get_contents(__DIR__ . '/vkpay_log.txt');
        if ($log !== false && $uid !== '') {
            foreach (explode("\n", $log) as $line) {
                if (strpos($line, 'order_status_change') === false) continue;
                $j = json_decode(mb_substr($line, strpos($line, '{')), true);
                if (!$j) continue;
                if (isset($j['status']) && $j['status'] === 'chargeable'
                    && isset($j['user_id']) && $j['user_id'] === $uid
                    && !empty($j['item'])) {
                    $owned[$j['item']] = true;
                }
            }
        }
        echo json_encode(['ok' => true, 'items' => array_keys($owned)], JSON_UNESCAPED_UNICODE);
        exit;
    }
    echo json_encode(['ok' => true, 'service' => 'starfall-vk-payments', 'time' => date('c')]);
    exit;
}

$input = $_POST;
$response = [];

// ---------- Проверка подписи (если задан секрет) ----------
if ($secret_key !== '') {
    $sig = isset($input['sig']) ? $input['sig'] : '';
    $check = $input;
    unset($check['sig']);
    ksort($check);
    $str = '';
    foreach ($check as $k => $v) { $str .= $k . '=' . $v; }
    if ($sig !== md5($str . $secret_key)) {
        echo json_encode(['error' => [
            'error_code' => 10,
            'error_msg'  => 'Calculated and passed signatures are not the same',
            'critical'   => true,
        ]]);
        exit;
    }
}

$type = isset($input['notification_type']) ? $input['notification_type'] : '';

switch ($type) {
    // ---------- Информация о товаре (боевой и тестовый режим) ----------
    case 'get_item':
    case 'get_item_test':
        $item = isset($input['item']) ? $input['item'] : '';
        if (isset($items[$item])) {
            $p = $items[$item];
            if ($type === 'get_item_test') { $p['title'] .= ' (тест)'; }
            $response['response'] = $p;
        } else {
            $response['error'] = [
                'error_code' => 20,
                'error_msg'  => 'Product does not exist: ' . $item,
                'critical'   => true,
            ];
        }
        break;

    // ---------- Изменение статуса заказа ----------
    case 'order_status_change':
    case 'order_status_change_test':
        if (isset($input['status']) && $input['status'] === 'chargeable') {
            // Товар выдаётся на клиенте после успешного ответа VK Bridge,
            // поэтому здесь просто подтверждаем заказ.
            $response['response'] = [
                'order_id'     => intval($input['order_id']),
                'app_order_id' => 1,
            ];
        } else {
            $response['error'] = [
                'error_code' => 100,
                'error_msg'  => 'Incorrect chargeable.',
                'critical'   => true,
            ];
        }
        break;

    default:
        $response['error'] = [
            'error_code' => 11,
            'error_msg'  => 'Unknown or missing notification_type',
            'critical'   => true,
        ];
}

// ---------- Лог для отладки (можно удалить) ----------
@file_put_contents(__DIR__ . '/vkpay_log.txt',
    date('c') . ' ' . $type . ' ' . json_encode($input, JSON_UNESCAPED_UNICODE) . "\n",
    FILE_APPEND);

echo json_encode($response, JSON_UNESCAPED_UNICODE);
