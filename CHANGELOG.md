# Change Log

All notable changes to this project will be documented in this file.

## [v1.6.3] - 2026-02-23
### Changed
- 게시판 목록: 기본으로 작성 가능한 게시판만 표시
- 디버그 UI 및 서버 디버그 응답 제거
- 설정 탭 버튼 간격 개선 및 프리셋 적용 버튼 제거
- 메뉴 불러오기 성공 팝업 제거
### Added
- 게시판 선택 시 분류 자동 불러오기
- 현재 타겟 라벨에 한글 게시판 이름 표시
- 결과 탭에 “선택된 파일 제거” 버튼 추가
- 프리셋 적용 상태 저장/복원 및 시작 시 자동 메뉴 불러오기/적용
- 본문 없이 이미지 첨부만으로도 게시글 작성 가능 (웹진/갤러리 대응)

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
