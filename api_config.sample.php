<?php
/**
 * PostMoon Rhymix API Configuration (Sample)
 * 
 * [Optional] Use this file for simple file-based authentication instead of Database.
 * 
 * 1. Rename this file to `api_config.php`.
 * 2. Upload it to the SAME directory as `secure_api.php`.
 * 3. Define your API keys and map them to a Rhymix User ID.
 * 
 * SECURITY WARNING:
 * - This file contains sensitive keys.
 * - Ideally, place this file OUTSIDE the web root if possible and include it in secure_api.php.
 * - If placed in web root, ensure your web server blocks access to .php files that just return data,
 *   or rely on the fact that it returns a PHP array and doesn't print anything.
 */

return [
    // Format: 'YOUR_LONG_RANDOM_API_KEY' => 'RHYMIX_USER_ID'
    
    // Example 1: Key for the main administrator
    'rx_live_8f3a2b1c9d0e4f5g6h7i8j9k0l1m2n3o' => 'admin',
    
    // Example 2: Key for an editor
    'rx_live_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p' => 'editor_user',
];
