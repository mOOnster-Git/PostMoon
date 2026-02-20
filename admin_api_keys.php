<?php
/**
 * Rhymix API Key Manager (Admin Only)
 * 
 * Features:
 * - Create/Revoke API Keys for members
 * - List active keys
 * - Auto-creates 'rx_api_keys' table
 */

define('__ZBXE__', true);
require_once './config/config.inc.php';

// Debug Logging
function debug_log($msg) {
    file_put_contents(__DIR__ . '/admin_debug_log.txt', date('Y-m-d H:i:s') . " " . $msg . "\n", FILE_APPEND);
}

// Initialize Rhymix Context
$oContext = Context::getInstance();
$oContext->init();

// 1. Security Check: Admin Access Only
$logged_info = Context::get('logged_info');
if (!$logged_info || $logged_info->is_admin != 'Y') {
    header('HTTP/1.1 403 Forbidden');
    die('<h1>Access Denied</h1><p>관리자만 접근할 수 있습니다. <a href="./index.php?act=dispMemberLoginForm">로그인</a></p>');
}

$oDB = DB::getInstance();

// 2. Auto-setup Table
$table_check = $oDB->query("SHOW TABLES LIKE 'rx_api_keys'");
if (!$oDB->fetch($table_check)) {
    $create_sql = "
    CREATE TABLE `rx_api_keys` (
      `api_key` varchar(100) NOT NULL,
      `member_srl` bigint(11) NOT NULL,
      `user_id` varchar(100) NOT NULL,
      `nick_name` varchar(100) NOT NULL,
      `status` char(1) DEFAULT 'Y',
      `created_at` datetime DEFAULT NULL,
      PRIMARY KEY (`api_key`),
      KEY `idx_member_srl` (`member_srl`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8;
    ";
    $oDB->query($create_sql);
    $msg = "DB 테이블(rx_api_keys)이 생성되었습니다.";
}

// 3. Handle Actions
$action = Context::get('action');
if ($action) {
    debug_log("Action received: " . $action);
    debug_log("POST data: " . print_r($_POST, true));
}

$msg = Context::get('msg'); // Get message from redirect

if ($action == 'create') {
    $target_user_id = Context::get('user_id');
    $oMemberModel = getModel('member');
    $member_info = $oMemberModel->getMemberInfoByUserID($target_user_id);
    
    if ($member_info) {
        // Generate Secure Key
        $new_key = 'rx_live_' . bin2hex(random_bytes(16));
        
        // Insert using sprintf to ensure values are properly embedded
        // (Rhymix DB::query binding support can be inconsistent depending on environment)
        $args = new stdClass();
        $args->api_key = $new_key;
        $args->member_srl = $member_info->member_srl;
        $args->user_id = $member_info->user_id;
        $args->nick_name = $member_info->nick_name;
        $args->status = 'Y';
        $args->created_at = date('Y-m-d H:i:s');
        
        // Escape strings for safety since we are manually building query
        $safe_user_id = str_replace("'", "''", $args->user_id);
        $safe_nick_name = str_replace("'", "''", $args->nick_name);
        
        // Use %s for member_srl as well to avoid 32-bit integer overflow issues
        $query = sprintf(
            "INSERT INTO rx_api_keys (api_key, member_srl, user_id, nick_name, status, created_at) VALUES ('%s', '%s', '%s', '%s', '%s', '%s')",
            $args->api_key,
            $args->member_srl,
            $safe_user_id,
            $safe_nick_name,
            $args->status,
            $args->created_at
        );
        
        $stmt = $oDB->query($query);
        
        if ($stmt) {
            $msg = "API 키가 생성되었습니다: " . $member_info->nick_name;
        } else {
            $msg = "오류: 키 생성 실패. DB 쿼리 오류가 발생했습니다.";
            // Try to log error if possible
        }
    } else {
        $msg = "오류: 회원을 찾을 수 없습니다 (" . htmlspecialchars($target_user_id) . ")";
    }
    
    // Redirect to prevent form resubmission
    header("Location: " . $_SERVER['PHP_SELF'] . "?msg=" . urlencode($msg));
    exit;

} elseif ($action == 'delete') {
    $target_key = Context::get('key');
    $target_srl = Context::get('member_srl');
    
    debug_log("Attempting delete. Key: [$target_key], SRL: [$target_srl]");

    if ($target_key) {
        // Safe delete
        $safe_key = str_replace("'", "''", $target_key);
        $query = "DELETE FROM rx_api_keys WHERE api_key = '$safe_key'";
        debug_log("Delete Query: " . $query);
        $result = $oDB->query($query);
        debug_log("Delete Result: " . ($result ? "Success" : "Fail"));
        $msg = "API 키가 삭제되었습니다.";
    } elseif (empty($target_key) && (empty($target_srl) || $target_srl == 0)) {
        // Handle broken records with empty key and member_srl 0
        $query = "DELETE FROM rx_api_keys WHERE (member_srl = 0 OR member_srl IS NULL) AND (api_key = '' OR api_key IS NULL)";
        debug_log("Empty Key Cleanup Query: " . $query);
        $result = $oDB->query($query);
        debug_log("Empty Key Cleanup Result: " . ($result ? "Success" : "Fail"));
        $msg = "오류 데이터(키 없음)가 삭제되었습니다.";
    } elseif (isset($target_srl) && ($target_srl == 0 || $target_srl == '0')) {
        // Handle broken records with empty key and member_srl 0
        $query = "DELETE FROM rx_api_keys WHERE member_srl = 0 AND (api_key = '' OR api_key IS NULL)";
        debug_log("Cleanup Query (SRL=0): " . $query);
        $result = $oDB->query($query);
        debug_log("Cleanup Result: " . ($result ? "Success" : "Fail"));
        $msg = "오류 데이터(키 없음)가 삭제되었습니다.";
    } else {
        debug_log("Delete failed: No valid target key or SRL=0 condition met.");
    }
    
    // Redirect to prevent form resubmission
    header("Location: " . $_SERVER['PHP_SELF'] . "?msg=" . urlencode($msg));
    exit;

} elseif ($action == 'cleanup') {
    // 1. Delete empty keys or member_srl 0
    $query1 = "DELETE FROM rx_api_keys WHERE api_key = '' OR api_key IS NULL OR member_srl = 0";
    $oDB->query($query1);
    
    // 2. Delete entries with nick_name '0' or empty
    $query2 = "DELETE FROM rx_api_keys WHERE nick_name = '0' OR nick_name = ''";
    $oDB->query($query2);

    // 3. Delete entries that have whitespace only
    $query3 = "DELETE FROM rx_api_keys WHERE TRIM(api_key) = ''";
    $oDB->query($query3);
    
    debug_log("Full Cleanup Executed.");
    $msg = "유효하지 않은 키 데이터를 정리했습니다.";
    
    // Redirect to prevent form resubmission
    header("Location: " . $_SERVER['PHP_SELF'] . "?msg=" . urlencode($msg));
    exit;
}

// 4. List Keys
$query = "SELECT * FROM rx_api_keys ORDER BY created_at DESC";
$stmt = $oDB->query($query);
$result = $oDB->fetch($stmt);

$keys = [];
if (is_array($result)) {
    $keys = $result;
} elseif (is_object($result)) {
    $keys[] = $result;
}

debug_log("Fetched Keys Count: " . count($keys));

?>
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rhymix API Key Manager</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body { padding: 20px; background: #f8f9fa; }
        .container { max-width: 900px; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .key-code { font-family: monospace; background: #eee; padding: 2px 5px; border-radius: 3px; color: #d63384; }
    </style>
</head>
<body>
    <div class="container">
        <h2 class="mb-4">🔑 API 키 관리 (Rhymix)</h2>
        
        <?php if($msg): ?>
            <div class="alert alert-info"><?php echo $msg; ?></div>
        <?php endif; ?>

        <!-- Create Form -->
        <div class="card mb-4">
            <div class="card-header bg-primary text-white">새 API 키 발급</div>
            <div class="card-body">
                <form method="POST" class="row g-3">
                    <input type="hidden" name="action" value="create">
                    <div class="col-auto">
                        <label for="user_id" class="visually-hidden">아이디</label>
                        <input type="text" class="form-control" id="user_id" name="user_id" placeholder="회원 아이디 (ID)" required>
                    </div>
                    <div class="col-auto">
                        <button type="submit" class="btn btn-primary mb-3">키 생성</button>
                    </div>
                    <div class="col-auto">
                        <span class="form-text text-muted">해당 회원의 아이디를 입력하면 키가 자동 생성됩니다.</span>
                    </div>
                </form>
            </div>
        </div>

        <!-- Cleanup -->
        <div class="mb-3 text-end">
             <form method="POST" style="display:inline;" onsubmit="return confirm('유효하지 않은 키 데이터를 정리하시겠습니까?');">
                 <input type="hidden" name="action" value="cleanup">
                 <button type="submit" class="btn btn-warning btn-sm">오류 데이터 정리</button>
             </form>
        </div>

        <!-- List -->
        <h4 class="mb-3">발급된 키 목록</h4>
        <table class="table table-hover table-bordered">
            <thead class="table-light">
                <tr>
                    <th>닉네임 (ID)</th>
                    <th>API Key</th>
                    <th>발급일</th>
                    <th>관리</th>
                </tr>
            </thead>
            <tbody>
                <?php if(empty($keys)): ?>
                <tr>
                    <td colspan="4" class="text-center">발급된 키가 없습니다.</td>
                </tr>
                <?php else: ?>
                    <?php foreach($keys as $k): ?>
                    <tr>
                        <td>
                            <strong><?php echo htmlspecialchars($k->nick_name); ?></strong><br>
                            <small class="text-muted">(<?php echo htmlspecialchars($k->user_id); ?>)</small>
                        </td>
                        <td>
                            <span class="key-code" onclick="navigator.clipboard.writeText(this.innerText); alert('복사되었습니다!')" style="cursor:pointer" title="클릭하여 복사">
                                <?php echo htmlspecialchars($k->api_key); ?>
                            </span>
                        </td>
                        <td><?php echo $k->created_at; ?></td>
                        <td>
                            <form method="POST" onsubmit="return confirm('정말 삭제하시겠습니까?');">
                                <input type="hidden" name="action" value="delete">
                                <input type="hidden" name="key" value="<?php echo htmlspecialchars($k->api_key); ?>">
                                <input type="hidden" name="member_srl" value="<?php echo htmlspecialchars($k->member_srl); ?>">
                                <button type="submit" class="btn btn-sm btn-danger">삭제</button>
                            </form>
                        </td>
                    </tr>
                    <?php endforeach; ?>
                <?php endif; ?>
            </tbody>
        </table>
        
        <div class="mt-4 text-end">
            <a href="./" class="btn btn-secondary">메인으로 돌아가기</a>
        </div>
    </div>
</body>
</html>
