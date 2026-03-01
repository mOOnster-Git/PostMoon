<?php
/**
 * PostMoon Rhymix API Bridge (Open Source Version)
 * * @version 1.6.3
 * @author PostMoon Project
 * @description Provides secure API endpoints for posting content to Rhymix/XE
 */

// ============================================================================
// CONFIGURATION SECTION (사용자 설정 영역)
// ============================================================================

// 1. 디버그 모드 (배포 시 false로 설정 권장)
// true: debug_log.txt에 로그 기록 (민감 정보 포함 가능)
define('ENABLE_DEBUG', false);

// 2. 허용할 파일 확장자 (보안을 위해 필요한 것만 최소한으로 허용)
// .php, .exe, .sh, .html 등 실행 가능한 파일은 절대 포함하지 마세요.
$ALLOWED_EXTENSIONS = [
    // 이미지
    'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg',
    // 문서
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'hwp',
    // 압축
    'zip', '7z', 'rar'
];

// 3. 파일 업로드 최대 크기 (바이트 단위, 예: 10MB = 10 * 1024 * 1024)
// 서버 설정(php.ini)보다 클 수 없습니다.
define('MAX_UPLOAD_SIZE', 20 * 1024 * 1024);

// 4. API 키 인증 방식 강제 (헤더만 허용할지 여부)
// true: 오직 HTTP Header (X-Api-Key, Authorization)만 허용 (권장)
// false: GET/POST 파라미터 'api_key'도 허용 (테스트 용도)
define('STRICT_AUTH_HEADER', true);

// ============================================================================
// CORE LOGIC (이 아래는 수정하지 마세요)
// ============================================================================

// Force JSON format
header('Content-Type: application/json; charset=UTF-8');
$_GET['format'] = 'json';
$_REQUEST['format'] = 'json';

// Disable default error display
ini_set('display_errors', 0);

// Define Rhymix Constants
define('__ZBXE__', true);
define('__XE__', true);

/**
 * Secure Debug Logger
 */
function debug_log($msg) {
    if (defined('ENABLE_DEBUG') && ENABLE_DEBUG) {
        $msg = preg_replace('/(api_key|password)=[^&]+/', '$1=***', $msg);
        file_put_contents(__DIR__ . '/debug_log.txt', date('Y-m-d H:i:s') . " " . $msg . "\n", FILE_APPEND);
    }
}

/**
 * Fatal Error Handler
 */
function api_shutdown_handler() {
    $error = error_get_last();
    if ($error && ($error['type'] === E_ERROR || $error['type'] === E_PARSE || $error['type'] === E_COMPILE_ERROR || $error['type'] === E_CORE_ERROR)) {
        while (ob_get_level()) ob_end_clean();
        header('Content-Type: application/json; charset=UTF-8');
        http_response_code(500);
        $msg = 'Fatal Error: ' . $error['message'];
        if (defined('ENABLE_DEBUG') && ENABLE_DEBUG) {
            $msg .= ' in ' . $error['file'] . ':' . $error['line'];
        }
        debug_log("FATAL: " . $msg);
        echo json_encode(['error' => -1, 'message' => $msg]);
        exit;
    }
}
register_shutdown_function('api_shutdown_handler');

debug_log("Script Started");
debug_log("Script Version: 1.6.1");

// --- 1. Bootstrap Rhymix ---
$possible_paths = [
    __DIR__ . '/common/autoload.php',
    __DIR__ . '/../common/autoload.php',
    __DIR__ . '/../../common/autoload.php',
    $_SERVER['DOCUMENT_ROOT'] . '/common/autoload.php',
    $_SERVER['DOCUMENT_ROOT'] . '/rhymix/common/autoload.php'
];

$autoload_path = null;
foreach ($possible_paths as $path) {
    if (file_exists($path)) {
        $autoload_path = $path;
        break;
    }
}

if (!$autoload_path) {
    http_response_code(500);
    echo json_encode(['error' => -1, 'message' => 'System Error: Rhymix autoload.php not found. Please check file location.']);
    exit;
}

$rhymix_root = dirname(dirname($autoload_path));
chdir($rhymix_root);

try {
    debug_log("Attempting to require autoload: " . $autoload_path);
    require_once $autoload_path;
    debug_log("Autoload success. Attempting Context::init()");
    
    Context::init();
    debug_log("Context::init() success. Setting ResponseMethod to JSON");
    
    Context::setResponseMethod('JSON');
    debug_log("ResponseMethod set to JSON");
    
} catch (Throwable $e) {
    debug_log("EXCEPTION in Init: " . $e->getMessage());
    http_response_code(500);
    echo json_encode(['error' => -1, 'message' => 'Rhymix Init Failed: ' . $e->getMessage()]);
    exit;
}

// --- 2. Authentication (Enhanced Security) ---

if (!function_exists('getallheaders')) {
    function getallheaders() {
        $headers = [];
        foreach ($_SERVER as $name => $value) {
            if (substr($name, 0, 5) == 'HTTP_') {
                $headers[str_replace(' ', '-', ucwords(strtolower(str_replace('_', ' ', substr($name, 5)))))] = $value;
            }
        }
        return $headers;
    }
}

$api_key = null;
$headers = getallheaders();

if (isset($headers['X-Api-Key'])) {
    $api_key = $headers['X-Api-Key'];
} elseif (isset($_SERVER['HTTP_X_API_KEY'])) {
    $api_key = $_SERVER['HTTP_X_API_KEY'];
}

if (!$api_key) {
    $auth_header = isset($headers['Authorization']) ? $headers['Authorization'] : (isset($_SERVER['HTTP_AUTHORIZATION']) ? $_SERVER['HTTP_AUTHORIZATION'] : '');
    if (preg_match('/Bearer\s+(.*)$/i', $auth_header, $matches)) {
        $api_key = trim($matches[1]);
    }
}

if (!$api_key && !STRICT_AUTH_HEADER) {
    $api_key = Context::get('api_key');
}

if (!$api_key) {
    debug_log("API Key Missing");
    http_response_code(401);
    echo json_encode(['error' => -1, 'message' => 'Authentication Failed: API Key Missing']);
    exit;
}

debug_log("API Key Found. Verifying against DB...");

$row = null;
try {
    $oDB = DB::getInstance();
    if (method_exists($oDB, 'escapeString')) {
        $safe_key = $oDB->escapeString($api_key);
    } else {
        $safe_key = addslashes($api_key);
    }

    $query = "SELECT * FROM rx_api_keys WHERE api_key = '$safe_key' AND status = 'Y'";
    $stmt = $oDB->query($query);
    
    if ($stmt) {
         $row = $oDB->fetch($stmt);
    } else {
         debug_log("DB Query Failed. Stmt is false or invalid.");
    }
} catch (Throwable $e) {
    debug_log("DB Check Exception: " . $e->getMessage());
    $row = null;
}

if (!$row) {
    debug_log("Key not found in DB.");
    http_response_code(403);
    echo json_encode([
        'error' => -1, 
        'message' => 'Authentication Failed: Invalid API Key. Please visit /PostMoon/admin_api_keys.php to issue a key.'
    ]);
    exit;
}

$member_srl = $row->member_srl;
$oMemberModel = getModel('member');
$member_info = $oMemberModel->getMemberInfo($member_srl);

if (!$member_info || !$member_info->member_srl) {
    http_response_code(500);
    echo json_encode(['error' => -1, 'message' => 'System Error: Associated user not found']);
    exit;
}

Context::set('is_logged', true);
Context::set('logged_info', $member_info);
if ($member_info->is_admin == 'Y') {
    Context::set('is_admin', true);
}
$_SESSION['is_logged'] = true;
$_SESSION['logged_info'] = $member_info;

debug_log("Authenticated as: " . $member_info->user_id);

// --- 3. Action Handling ---

$action = Context::get('action');
$output = ['error' => 0, 'message' => 'success'];

try {
    switch ($action) {
        case 'get_menu_list':
            $oDB = DB::getInstance();
            
            // Rhymix DB 테이블 접두사를 동적으로 가져와 안전하게 쿼리 작성
            $prefix = Context::getDBInfo()->master_db['db_table_prefix'];
            $writable_only = Context::get('writable_only');
            
            // 사이트 메뉴에 등록된 항목(이름과 url)을 가져옵니다.
            $query = "SELECT m.title AS menu_title, i.name AS item_name, i.url AS mid, mo.module AS module 
                      FROM {$prefix}menu_item i 
                      LEFT JOIN {$prefix}menu m ON i.menu_srl = m.menu_srl 
                      LEFT JOIN {$prefix}modules mo ON mo.mid = i.url 
                      WHERE i.url <> '' 
                        AND i.url NOT LIKE 'http%' 
                        AND (i.is_shortcut IS NULL OR i.is_shortcut = 'N')
                        AND mo.module = 'board'
                      ORDER BY m.menu_srl ASC, i.list_order ASC";
                      
            $stmt = $oDB->query($query);
            $data = is_array($stmt->data) ? $stmt->data : ($stmt->data ? [$stmt->data] : []);
            
            $menu_list = [];
            foreach ($data as $row) {
                if(!empty($row->mid)) {
                    $module_info = ModuleModel::getModuleInfoByMid($row->mid);
                    $can_write = false;
                    $is_manager = false;
                    if ($module_info && $module_info->module === 'board') {
                        $grant = ModuleModel::getGrant($module_info, $member_info);
                        $can_write = ($grant && $grant->can('write_document'));
                        $is_manager = ($grant && $grant->manager) ? true : false;
                    }
                    if ($writable_only) {
                        if (!$can_write && !$is_manager) {
                            continue;
                        }
                    }
                    // 메뉴 항목 이름 언어 처리 (serialize 된 name 대응)
                    $item_name = $row->item_name;
                    $lang_code = Context::getLangType();
                    $decoded_name = null;
                    if (is_string($item_name)) {
                        $tmp = @unserialize($item_name);
                        if ($tmp && is_array($tmp)) {
                            $decoded_name = isset($tmp[$lang_code]) ? $tmp[$lang_code] : (reset($tmp) ?: '');
                        }
                    }
                    if ($decoded_name === null || $decoded_name === '') {
                        $decoded_name = $item_name; // 원본 그대로 사용 (이미 문자열인 경우)
                    }
                    $menu_list[] = [
                        'menu_title' => Context::replaceUserLang($row->menu_title),
                        'item_name'  => Context::replaceUserLang($decoded_name),
                        'mid'        => $row->mid
                    ];
                }
            }
            if (empty($menu_list)) {
                try {
                    $oModuleModel = getModel('module');
                    $args = new stdClass();
                    $args->site_srl = 0;
                    $mid_list = $oModuleModel->getMidList($args);
                    if (is_array($mid_list)) {
                        foreach ($mid_list as $mod) {
                            if (!empty($mod->mid) && $mod->module === 'board') {
                                $module_info2 = ModuleModel::getModuleInfoByMid($mod->mid);
                                $can_write2 = false;
                                $is_manager2 = false;
                                if ($module_info2 && $module_info2->module === 'board') {
                                    $grant2 = ModuleModel::getGrant($module_info2, $member_info);
                                    $can_write2 = ($grant2 && $grant2->can('write_document'));
                                    $is_manager2 = ($grant2 && $grant2->manager) ? true : false;
                                }
                                if ($writable_only && !$can_write2 && !$is_manager2) {
                                    continue;
                                }
                                $menu_list[] = [
                                    'menu_title' => 'Modules',
                                    'item_name'  => $mod->browser_title ?: $mod->mid,
                                    'mid'        => $mod->mid
                                ];
                            }
                        }
                    }
                } catch (Throwable $e) {
                }
            }
            $output['menu_list'] = $menu_list;

            $index_page = ['module_srl' => 0, 'mid' => '', 'title' => ''];
            try {
                $default_mid_info = ModuleModel::getDefaultMid();
                if ($default_mid_info && !empty($default_mid_info->module_srl)) {
                    $index_page['module_srl'] = intval($default_mid_info->module_srl);
                    $index_page['mid'] = strval($default_mid_info->mid ?? '');
                    $index_page['title'] = strval($default_mid_info->browser_title ?? ($default_mid_info->mid ?? 'index'));
                }
            } catch (Throwable $e) {
            }
            $output['index_page'] = $index_page;
            break;

        case 'create_document':
            $mid = Context::get('mid');
            $title = Context::get('title');
            $content = Context::get('content');
            $category_srl = Context::get('category_srl');

            $create_popup_param = Context::get('create_popup');
            if ($create_popup_param === null || $create_popup_param === '') {
                $create_popup_param = $_REQUEST['create_popup'] ?? '';
            }
            $create_popup_raw = strtolower(trim((string) $create_popup_param));
            $should_create_popup = in_array($create_popup_raw, ['y', 'yes', '1', 'true'], true);

            $popup_scope_param = Context::get('popup_scope');
            if ($popup_scope_param === null || $popup_scope_param === '') {
                $popup_scope_param = $_REQUEST['popup_scope'] ?? 'current';
            }
            $popup_scope_raw = strtolower(trim((string) $popup_scope_param));
            $popup_scope = in_array($popup_scope_raw, ['all', 'global', 'site']) ? 'all' : 'current';

            $popup_target_mode_param = Context::get('popup_target_mode');
            if ($popup_target_mode_param === null || $popup_target_mode_param === '') {
                $popup_target_mode_param = $_REQUEST['popup_target_mode'] ?? '';
            }
            $popup_target_mode_raw = strtolower(trim((string) $popup_target_mode_param));
            if ($popup_target_mode_raw === '') {
                $popup_target_mode_raw = $popup_scope;
            }
            if (!in_array($popup_target_mode_raw, ['all', 'current', 'index'], true)) {
                $popup_target_mode_raw = 'current';
            }
            $popup_target_mode = $popup_target_mode_raw;

            $popup_target_module_srl_param = Context::get('popup_target_module_srl');
            if ($popup_target_module_srl_param === null || $popup_target_module_srl_param === '') {
                $popup_target_module_srl_param = $_REQUEST['popup_target_module_srl'] ?? 0;
            }
            $popup_target_module_srl = intval($popup_target_module_srl_param);

            $popup_start_date_param = Context::get('popup_start_date');
            if ($popup_start_date_param === null || $popup_start_date_param === '') {
                $popup_start_date_param = $_REQUEST['popup_start_date'] ?? '';
            }
            $popup_start_date_input = trim((string) $popup_start_date_param);

            $popup_end_date_param = Context::get('popup_end_date');
            if ($popup_end_date_param === null || $popup_end_date_param === '') {
                $popup_end_date_param = $_REQUEST['popup_end_date'] ?? '';
            }
            $popup_end_date_input = trim((string) $popup_end_date_param);

            $popup_cookie_days_param = Context::get('popup_cookie_days');
            if ($popup_cookie_days_param === null || $popup_cookie_days_param === '') {
                $popup_cookie_days_param = $_REQUEST['popup_cookie_days'] ?? '1';
            }
            $popup_cookie_days = intval($popup_cookie_days_param);
            if ($popup_cookie_days < 1) $popup_cookie_days = 1;
            if ($popup_cookie_days > 365) $popup_cookie_days = 365;

            $popup_width_param = Context::get('popup_width');
            if ($popup_width_param === null || $popup_width_param === '') {
                $popup_width_param = $_REQUEST['popup_width'] ?? '560';
            }
            $popup_width = intval($popup_width_param);
            if ($popup_width < 280) $popup_width = 560;
            if ($popup_width > 1200) $popup_width = 1200;

            $popup_content_param = Context::get('popup_content');
            if ($popup_content_param === null || $popup_content_param === '') {
                $popup_content_param = $_REQUEST['popup_content'] ?? '';
            }
            $popup_content_input = trim((string) $popup_content_param);

            if (!$mid || !$title) {
                throw new Exception('Missing required parameters: mid, title');
            }

            if (preg_match('/<script|<iframe|<object/i', $title)) {
                throw new Exception('Security Violation: Dangerous tags detected in title');
            }

            $module_info = ModuleModel::getModuleInfoByMid($mid);
            if (!$module_info || !$module_info->module_srl) {
                throw new Exception('Module not found: ' . $mid);
            }
            $module_srl = $module_info->module_srl;
            if ($module_info->module !== 'board') {
                throw new Exception('Only board modules are allowed');
            }

            $grant = ModuleModel::getGrant($module_info, $member_info);
            if (!$grant || !$grant->can('write_document')) {
                throw new Exception('Permission denied: write_document not allowed for this board');
            }

            // --- Secure File Upload Handling ---
            $file_srls = [];
            $upload_target_srl = 0;
            $content_to_append = "";

            if (!empty($_FILES['file']['name'])) {
                $oFileController = getController('file');
                $upload_target_srl = getNextSequence();

                $files = [];
                if (is_array($_FILES['file']['name'])) {
                    $count = count($_FILES['file']['name']);
                    for ($i = 0; $i < $count; $i++) {
                        $files[] = [
                            'name' => $_FILES['file']['name'][$i],
                            'type' => $_FILES['file']['type'][$i],
                            'tmp_name' => $_FILES['file']['tmp_name'][$i],
                            'error' => $_FILES['file']['error'][$i],
                            'size' => $_FILES['file']['size'][$i]
                        ];
                    }
                } else {
                    $files[] = $_FILES['file'];
                }

                foreach ($files as $file_info) {
                    if ($file_info['error'] !== UPLOAD_ERR_OK) continue;

                    if ($file_info['size'] > MAX_UPLOAD_SIZE) {
                        debug_log("File too large: " . $file_info['name']);
                        continue;
                    }

                    $ext = strtolower(pathinfo($file_info['name'], PATHINFO_EXTENSION));
                    if (!in_array($ext, $ALLOWED_EXTENSIONS)) {
                        debug_log("Security blocked extension: " . $ext);
                        continue;
                    }

                    if (preg_match('/\.php/i', $file_info['name'])) {
                        debug_log("Security blocked double extension: " . $file_info['name']);
                        continue;
                    }

                    $file_output = $oFileController->insertFile($file_info, $module_srl, $upload_target_srl, 0, true);
                    
                    if ($file_output->toBool()) {
                        $file_srl = $file_output->get('file_srl');
                        $file_srls[] = $file_srl;
                        
                        $uploaded_filename = $file_output->get('uploaded_filename');
                        $base_url = rtrim(Context::getDefaultUrl(), '/');
                        
                        if (substr($uploaded_filename, 0, 2) === './') {
                            $image_url = $base_url . substr($uploaded_filename, 1);
                        } else {
                            $image_url = $base_url . '/' . ltrim($uploaded_filename, '/');
                        }

                        // [핵심 수정] 라이믹스 스킨에서 어떤 CSS를 쓰더라도 무조건 중앙에 배치되도록
                        // img 태그 자체에 강제로 'display: block; margin: 0 auto;'를 부여합니다.
                        if (in_array($ext, ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg'])) {
                            $img_tag = sprintf('<img src="%s" alt="%s" style="display: block; margin: 0 auto; max-width: 100%%; height: auto;" />', $image_url, htmlspecialchars($file_info['name']));
                            $content_to_append .= '<div style="text-align: center; margin: 0 auto 30px auto; width: 100%; clear: both;">' . $img_tag . '</div>';
                        }
                        
                        if (method_exists($oFileController, 'setUploadTarget')) {
                            $oFileController->setUploadTarget($upload_target_srl, $file_srl);
                        }
                    }
                }
            }

            // If there is no content and no images to append, block to prevent empty posts
            if ((!isset($content) || trim(strval($content)) === '') && trim($content_to_append) === '') {
                throw new Exception('Missing content: provide body text or attach at least one image file');
            }

            $oDocumentController = getController('document');
            $obj = Context::getRequestVars();
            $obj->module_srl = $module_srl;
            if ($category_srl) {
                $obj->category_srl = intval($category_srl);
            }
            
            // Append images (본문 상단에 배치)
            if (!empty($content_to_append)) {
                $obj->content = $content_to_append . (isset($obj->content) ? $obj->content : '');
            }

            $obj->member_srl = $member_info->member_srl;
            $obj->user_id = $member_info->user_id;
            $obj->user_name = $member_info->user_name;
            $obj->nick_name = $member_info->nick_name;
            $obj->email_address = $member_info->email_address;
            $obj->allow_html = 'Y';

            if ($upload_target_srl) {
                $obj->document_srl = $upload_target_srl;
            }

            $doc_output = $oDocumentController->insertDocument($obj, true);

            if ($doc_output->toBool()) {
                $document_srl = $doc_output->get('document_srl');
                $output['message'] = 'Document created successfully';
                $output['document_srl'] = $document_srl;

                if (!empty($file_srls) && $upload_target_srl) {
                    $oFileController->setFilesValid($document_srl);
                    $oDocumentController->updateUploadedCount($document_srl);
                }

                if ($should_create_popup) {
                    $output['popup_requested'] = true;
                    $output['popup_created'] = false;
                    $output['popup_error'] = 'Unknown popup creation failure';
                    $output['popup_scope'] = $popup_scope;
                    $output['popup_target_mode'] = $popup_target_mode;

                    $base_url = rtrim(Context::getDefaultUrl(), '/');
                    $document_url = $base_url . '/index.php?mid=' . rawurlencode($mid) . '&document_srl=' . intval($document_srl);
                    // 버튼문구 자동추론: 제목 키워드 기반
                    $title_lower = mb_strtolower($title ?? '', 'UTF-8');
                    if (mb_strpos($title_lower, '모집') !== false || mb_strpos($title_lower, '신청') !== false || mb_strpos($title_lower, '접수') !== false) {
                        $popup_btn_text = '신청 / 지원하러 가기 >';
                    } elseif (mb_strpos($title_lower, '행사') !== false || mb_strpos($title_lower, '대회') !== false || mb_strpos($title_lower, '경기') !== false) {
                        $popup_btn_text = '행사 상세 보기 >';
                    } elseif (mb_strpos($title_lower, '결과') !== false || mb_strpos($title_lower, '순위') !== false) {
                        $popup_btn_text = '결과 확인하러 가기 >';
                    } elseif (mb_strpos($title_lower, '일정') !== false || mb_strpos($title_lower, '스케줄') !== false) {
                        $popup_btn_text = '일정 확인하러 가기 >';
                    } else {
                        $popup_btn_text = '자세히 보기 >';
                    }
                    $detail_button_html = "<div style='text-align:center; margin-top:16px;'><a href='" . htmlspecialchars($document_url, ENT_QUOTES, 'UTF-8') . "' style='display:inline-block; background:#3b5bdb; color:#fff; text-decoration:none; padding:11px 28px; border-radius:999px; font-size:14px; font-weight:700;'>" . htmlspecialchars($popup_btn_text, ENT_QUOTES, 'UTF-8') . "</a></div>";

                    try {
                        $oPopupModel = getModel('popup_manager_moonster');
                        if (!$oPopupModel) {
                            throw new Exception('popup_manager_moonster module not available');
                        }
                        if (!method_exists($oPopupModel, 'checkGrant') || !$oPopupModel->checkGrant($member_info)) {
                            throw new Exception('Permission denied: popup_manager_moonster grant required');
                        }

                        $popup_start_ts = time();
                        if ($popup_start_date_input !== '') {
                            $tmp_start = strtotime($popup_start_date_input);
                            if (!$tmp_start) {
                                throw new Exception('Invalid popup_start_date format');
                            }
                            $popup_start_ts = $tmp_start;
                        }

                        $popup_end_ts = null;
                        if ($popup_end_date_input !== '') {
                            $tmp_end = strtotime($popup_end_date_input);
                            if (!$tmp_end) {
                                throw new Exception('Invalid popup_end_date format');
                            }
                            $popup_end_ts = $tmp_end;
                            if ($popup_end_ts < $popup_start_ts) {
                                throw new Exception('popup_end_date cannot be earlier than popup_start_date');
                            }
                        }

                        $popup_target_for_insert = 0;
                        if ($popup_target_mode === 'current') {
                            $popup_target_for_insert = intval($module_srl);
                        } elseif ($popup_target_mode === 'index') {
                            if ($popup_target_module_srl > 0) {
                                $popup_target_for_insert = $popup_target_module_srl;
                            } else {
                                $default_mid_info2 = ModuleModel::getDefaultMid();
                                if ($default_mid_info2 && !empty($default_mid_info2->module_srl)) {
                                    $popup_target_for_insert = intval($default_mid_info2->module_srl);
                                }
                            }
                            if ($popup_target_for_insert <= 0) {
                                throw new Exception('Index page module is not available');
                            }
                        }

                        $popup_args = new stdClass();
                        $popup_args->popup_srl = getNextSequence();
                        $popup_args->module_srl = $popup_target_for_insert;
                        $popup_args->popup_type = 'html';
                        $popup_args->title = $title;
                        $popup_body_content = $popup_content_input !== '' ? $popup_content_input : (isset($obj->content) ? $obj->content : '');
                        // <a href= 태그가 없는 경우에만 버튼 자동추가
                        if (strpos($popup_body_content, '<a href=') === false) {
                            $popup_body_content .= $detail_button_html;
                        }
                        $popup_args->content = $popup_body_content;
                        $popup_args->is_enabled = 'Y';
                        $popup_args->cookie_days = $popup_cookie_days;
                        $popup_args->display_order = 0;
                        $popup_args->position_top = 100;
                        $popup_args->position_left = 100;
                        $popup_args->width = $popup_width;
                        $popup_args->height = 0;
                        $popup_args->start_date = date('YmdHis', $popup_start_ts);
                        $popup_args->end_date = $popup_end_ts ? date('YmdHis', $popup_end_ts) : '';
                        $popup_args->member_srl = $member_info->member_srl;

                        $popup_insert = executeQuery('popup_manager_moonster.insertPopup', $popup_args);
                        if (!$popup_insert || !$popup_insert->toBool()) {
                            $popup_err_msg = '';
                            if ($popup_insert) {
                                $popup_err_msg = trim((string) $popup_insert->getMessage());
                            }
                            throw new Exception('Failed to insert popup' . ($popup_err_msg ? (': ' . $popup_err_msg) : ''));
                        }

                        if ($popup_target_mode !== 'all') {
                            $target_args = new stdClass();
                            $target_args->popup_srl = $popup_args->popup_srl;
                            $target_args->module_srl = $popup_target_for_insert;
                            $target_output = executeQuery('popup_manager_moonster.insertTargetModule', $target_args);
                            if (!$target_output || !$target_output->toBool()) {
                                $target_err_msg = '';
                                if ($target_output) {
                                    $target_err_msg = trim((string) $target_output->getMessage());
                                }
                                throw new Exception('Failed to map popup target module' . ($target_err_msg ? (': ' . $target_err_msg) : ''));
                            }
                        }

                        $output['popup_created'] = true;
                        $output['popup_error'] = '';
                        $output['popup_srl'] = $popup_args->popup_srl;
                    } catch (Throwable $popup_error) {
                        $popup_message = trim((string) $popup_error->getMessage());
                        $output['popup_error'] = $popup_message !== '' ? $popup_message : 'Popup creation failed without message';
                        debug_log('Popup create failed: ' . $popup_error->getMessage());
                    }
                }
            } else {
                $error_code = $doc_output->getError();
                $error_msg = $doc_output->getMessage();
                $debug_info = print_r($doc_output->getVariables(), true);
                
                throw new Exception("Rhymix Error ($error_code): $error_msg (Debug: $debug_info)");
            }
            break;

        case 'get_board_categories':
            $mid = Context::get('mid');
            if (!$mid) {
                throw new Exception('Missing required parameter: mid');
            }
            $module_info = ModuleModel::getModuleInfoByMid($mid);
            if (!$module_info || $module_info->module !== 'board') {
                throw new Exception('Target module is not a board');
            }
            $list = DocumentModel::getCategoryList($module_info->module_srl);
            $categories = [];
            foreach ($list as $cat) {
                $categories[] = [
                    'category_srl' => $cat->category_srl,
                    'title' => $cat->title,
                    'depth' => $cat->depth
                ];
            }
            $output['categories'] = $categories;
            break;

        case 'list_modules':
            $oModuleModel = getModel('module');
            $args = new stdClass();
            $args->site_srl = 0; 
            $output['modules'] = $oModuleModel->getMidList($args);
            break;

        default:
            throw new Exception('Invalid action requested');
    }

} catch (Exception $e) {
    http_response_code(400); 
    $output['error'] = -1;
    $output['message'] = $e->getMessage();
    debug_log("Error: " . $e->getMessage());
}

echo json_encode($output);
