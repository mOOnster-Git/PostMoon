# Change Log

All notable changes to this project will be documented in this file.

## [v1.5.11 Client / v1.5.19 Server] - 2026-02-21
### Added
- **PostMoon Client (v1.5.11)**: Added right-click context menu (Cut, Copy, Paste, Select All) to all input fields.
- **PostMoon Client (v1.5.11)**: Optimized window size (1200x800) to fit standard monitors.
- **PostMoon Client (v1.5.11)**: Fixed layout issue where buttons were hidden when settings panel was open.

### Changed
- **Server Scripts (v1.5.19)**: Disabled debug logging by default in `secure_api.php` and `admin_api_keys.php` to prevent log file bloat.
- **Server Scripts (v1.5.19)**: Adjusted layout and UI elements for better usability.

## [v1.5.18] - 2026-02-21
### Fixed
- Fixed a bug in `secure_api.php` where valid API keys were rejected due to strict DB query checking.
- Improved database error logging for better troubleshooting.

## [v1.5.17] - 2026-02-21
### Changed
- **Breaking Change**: Removed file-based authentication (`api_config.php`). All API keys must now be managed via `admin_api_keys.php` and stored in the database.
- Improved `secure_api.php` and `admin_api_keys.php` to fully support running from a subfolder (e.g., `/PostMoon/`).
- Added automatic detection of Rhymix core files from subdirectories.

## [v1.5.16] - 2026-02-21
### Added
- `admin_api_keys.php`: Added automatic creation of `rx_api_keys` table if it doesn't exist.
- `admin_api_keys.php`: Added logic to fix Current Working Directory (CWD) for Rhymix compatibility.

## [v1.5.0] - 2026-02-20
### Initial Release
- Released PostMoon Client (Windows) and Server scripts.
- Features: AI-powered article formatting, Rhymix integration, Image attachment support.
