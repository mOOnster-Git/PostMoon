<?php
/**
 * PostMoon Rhymix API Bridge (Open Source Version)
 * * @version 1.6.1
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
        case 'create_document':
            $mid = Context::get('mid');
            $title = Context::get('title');
            $content = Context::get('content');

            if (!$mid || !$title || !$content) {
                throw new Exception('Missing required parameters: mid, title, content');
            }

            if (preg_match('/<script|<iframe|<object/i', $title)) {
                throw new Exception('Security Violation: Dangerous tags detected in title');
            }

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

            $oDocumentController = getController('document');
            $obj = Context::getRequestVars();
            $obj->module_srl = $module_srl;
            
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
            } else {
                $error_code = $doc_output->getError();
                $error_msg = $doc_output->getMessage();
                $debug_info = print_r($doc_output->getVariables(), true);
                
                throw new Exception("Rhymix Error ($error_code): $error_msg (Debug: $debug_info)");
            }
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