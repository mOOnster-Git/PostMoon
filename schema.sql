-- PostMoon Rhymix API Key Schema
-- 
-- Run this SQL query in your Rhymix database (usually via phpMyAdmin or admin_api_keys.php auto-setup).
--
-- Table: rx_api_keys
-- Description: Stores API keys for secure authentication.

CREATE TABLE `rx_api_keys` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `api_key` varchar(100) NOT NULL,
  `member_srl` bigint(11) NOT NULL,
  `user_id` varchar(100) NOT NULL,
  `nick_name` varchar(100) NOT NULL,
  `status` char(1) DEFAULT 'Y' COMMENT 'Y: Active, N: Inactive',
  `created_at` datetime DEFAULT NULL,
  UNIQUE KEY `idx_api_key` (`api_key`),
  KEY `idx_member_srl` (`member_srl`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='PostMoon API Keys';
