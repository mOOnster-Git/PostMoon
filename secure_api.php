<?php
/**
 * PostMoon Rhymix API Bridge (Open Source Version)
 * 
 * @version 1.5.1
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
        // 민감 정보 마스킹 처리 (간단 예시)
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

// --- 1. Bootstrap Rhymix ---
// 상대 경로로 Rhymix 공통 파일 로드 (현재 파일 위치 기준)
// 일반적인 경로: ./common/autoload.php 또는 ../common/autoload.php
$possible_paths = [
    __DIR__ . '/common/autoload.php',
    __DIR__ . '/../common/autoload.php',
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

require_once $autoload_path;
Context::init();

// --- 2. Authentication (Enhanced Security) ---

$api_key = null;
$headers = getallheaders(); // Apache specific, needs polyfill for Nginx if strictly needed, but $_SERVER works too.

// Check X-Api-Key Header
if (isset($headers['X-Api-Key'])) {
    $api_key = $headers['X-Api-Key'];
} elseif (isset($_SERVER['HTTP_X_API_KEY'])) {
    $api_key = $_SERVER['HTTP_X_API_KEY'];
}

// Check Authorization: Bearer Header
if (!$api_key) {
    $auth_header = isset($headers['Authorization']) ? $headers['Authorization'] : (isset($_SERVER['HTTP_AUTHORIZATION']) ? $_SERVER['HTTP_AUTHORIZATION'] : '');
    if (preg_match('/Bearer\s+(.*)$/i', $auth_header, $matches)) {
        $api_key = trim($matches[1]);
    }
}

// Check GET/POST param (Only if STRICT_AUTH_HEADER is false)
if (!$api_key && !STRICT_AUTH_HEADER) {
    $api_key = Context::get('api_key');
}

if (!$api_key) {
    http_response_code(401);
    echo json_encode(['error' => -1, 'message' => 'Authentication Failed: API Key Missing']);
    exit;
}

// Validate Key against DB
// 테이블이 없다면 생성해야 합니다:
// CREATE TABLE rx_api_keys (
//   id INT AUTO_INCREMENT PRIMARY KEY,
//   api_key VARCHAR(255) NOT NULL UNIQUE,
//   member_srl INT NOT NULL,
//   user_id VARCHAR(100),
//   memo VARCHAR(255),
//   status CHAR(1) DEFAULT 'Y',
//   regdate DATETIME DEFAULT CURRENT_TIMESTAMP
// );

$oDB = DB::getInstance();
// Prepared Statement 사용으로 SQL Injection 방지
// Rhymix DB 클래스는 escapeString 메서드 제공하지만, 여기선 안전하게 처리
$safe_key = $oDB->escapeString($api_key); // Basic escaping provided by Rhymix DB class

// 쿼리 실행 (status = 'Y' 인 키만 허용)
$query = "SELECT * FROM rx_api_keys WHERE api_key = '$safe_key' AND status = 'Y'";
$stmt = $oDB->query($query);
$row = $oDB->fetch($stmt);

if (!$row) {
    // DB에 없으면 파일 설정 확인 (Legacy/Backup)
    // api_config.php가 존재하는 경우에만
    $config_file = __DIR__ . '/api_config.php';
    $is_valid_file_auth = false;
    
    if (file_exists($config_file)) {
        $api_keys = include $config_file;
        if (is_array($api_keys) && isset($api_keys[$api_key])) {
            $user_id = $api_keys[$api_key];
            $is_valid_file_auth = true;
            
            // 파일 인증 성공 시 member_info 조회
            $oMemberModel = getModel('member');
            $member_info = $oMemberModel->getMemberInfoByUserID($user_id);
        }
    }
    
    if (!$is_valid_file_auth) {
        http_response_code(403);
        debug_log("Auth Failed for key: " . substr($api_key, 0, 5) . "...");
        echo json_encode(['error' => -1, 'message' => 'Authentication Failed: Invalid API Key']);
        exit;
    }
} else {
    // DB 인증 성공
    $member_srl = $row->member_srl;
    $oMemberModel = getModel('member');
    $member_info = $oMemberModel->getMemberInfo($member_srl);
}

if (!$member_info || !$member_info->member_srl) {
    http_response_code(500);
    echo json_encode(['error' => -1, 'message' => 'System Error: Associated user not found']);
    exit;
}

// Login Session Context 설정
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
        case 'create_document':
            // Input Validation
            $mid = Context::get('mid');
            $title = Context::get('title');
            $content = Context::get('content');

            if (!$mid || !$title || !$content) {
                throw new Exception('Missing required parameters: mid, title, content');
            }

            // XSS Prevention (Basic)
            // Rhymix handles XSS, but we can double check for dangerous tags in title
            if (preg_match('/<script|<iframe|<object/i', $title)) {
                throw new Exception('Security Violation: Dangerous tags detected in title');
            }

            // Verify Module
            $module_info = ModuleModel::getModuleInfoByMid($mid);
            if (!$module_info || !$module_info->module_srl) {
                throw new Exception('Module not found: ' . $mid);
            }
            $module_srl = $module_info->module_srl;

            // --- Secure File Upload Handling ---
            $file_srls = [];
            $upload_target_srl = 0;
            $content_to_append = "";

            if (!empty($_FILES['file']['name'])) {
                $oFileController = getController('file');
                $upload_target_srl = getNextSequence();

                // Normalize file array
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

                    // 1. Check File Size
                    if ($file_info['size'] > MAX_UPLOAD_SIZE) {
                        debug_log("File too large: " . $file_info['name']);
                        continue;
                    }

                    // 2. Check Extension (Whitelist)
                    $ext = strtolower(pathinfo($file_info['name'], PATHINFO_EXTENSION));
                    if (!in_array($ext, $ALLOWED_EXTENSIONS)) {
                        debug_log("Security blocked extension: " . $ext);
                        continue; // Skip dangerous files
                    }

                    // 3. Double Extension Check (e.g. shell.php.jpg) - Optional but good practice
                    // If filename contains .php., block it
                    if (preg_match('/\.php/i', $file_info['name'])) {
                        debug_log("Security blocked double extension: " . $file_info['name']);
                        continue;
                    }

                    // Insert File via Rhymix
                    $file_output = $oFileController->insertFile($file_info, $module_srl, $upload_target_srl, 0, true);
                    
                    if ($file_output->toBool()) {
                        $file_srl = $file_output->get('file_srl');
                        $file_srls[] = $file_srl;
                        
                        // Append Image to Content
                        $uploaded_filename = $file_output->get('uploaded_filename');
                        $base_url = rtrim(Context::getDefaultUrl(), '/');
                        
                        // Path normalization
                        if (substr($uploaded_filename, 0, 2) === './') {
                            $image_url = $base_url . substr($uploaded_filename, 1);
                        } else {
                            $image_url = $base_url . '/' . ltrim($uploaded_filename, '/');
                        }

                        // Check if it's an image
                        if (in_array($ext, ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg'])) {
                            $content_to_append .= sprintf('<p><img src="%s" alt="%s" style="max-width:100%%;" /></p>', $image_url, htmlspecialchars($file_info['name']));
                        }
                        
                        // Link file to target
                        if (method_exists($oFileController, 'setUploadTarget')) {
                            $oFileController->setUploadTarget($upload_target_srl, $file_srl);
                        }
                    }
                }
            }

            // Create Document
            $oDocumentController = getController('document');
            $obj = Context::getRequestVars();
            $obj->module_srl = $module_srl;
            
            // Append images
            if (!empty($content_to_append)) {
                $obj->content = (isset($obj->content) ? $obj->content : '') . $content_to_append;
            }

            // Set Author Info
            $obj->member_srl = $member_info->member_srl;
            $obj->user_id = $member_info->user_id;
            $obj->user_name = $member_info->user_name;
            $obj->nick_name = $member_info->nick_name;
            $obj->email_address = $member_info->email_address;
            $obj->allow_html = 'Y';

            // Link Files
            if ($upload_target_srl) {
                $obj->document_srl = $upload_target_srl;
            }

            // Insert
            $doc_output = $oDocumentController->insertDocument($obj, true);

            if ($doc_output->toBool()) {
                $document_srl = $doc_output->get('document_srl');
                $output['message'] = 'Document created successfully';
                $output['document_srl'] = $document_srl;

                // Validate Files
                if (!empty($file_srls) && $upload_target_srl) {
                    $oFileController->setFilesValid($document_srl);
                    $oDocumentController->updateUploadedCount($document_srl);
                }
            } else {
                throw new Exception($doc_output->getMessage());
            }
            break;

        case 'list_modules':
            // Simple module listing
            $oModuleModel = getModel('module');
            $args = new stdClass();
            $args->site_srl = 0; // Default site
            $output['modules'] = $oModuleModel->getMidList($args);
            break;

        default:
            throw new Exception('Invalid action requested');
    }

} catch (Exception $e) {
    http_response_code(400); // Bad Request or Internal Error
    $output['error'] = -1;
    $output['message'] = $e->getMessage();
    debug_log("Error: " . $e->getMessage());
}

echo json_encode($output);
