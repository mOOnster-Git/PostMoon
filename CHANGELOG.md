# Change Log

All notable changes to this project will be documented in this file.

## [v2.0.0] - 2026-03-01
### Changed
- 팝업 타이틀바 제거: 타이틀이 팝업 본문 상단(h2)에 통합되어 콘텐츠와 자연스럽게 어우러짐
- 탭 버튼 전면 개선: 둥근 모서리(radius=10), 높이 46px, 테두리, 선택 시 파란색 강조
- 모든 입력 필드 밝은 배경(흰색/다크모드 별도) 및 테두리 추가로 가시성 향상
- 팝업 날짜 기본값 → 빈값(제한없음) 처리
- 앱 재시작 시 팝업 등록 활성화 체크박스 항상 해제 상태로 시작
### Added
- AI 분석 완료 후 자동으로 "📝 게시글 편집" 탭으로 전환
- popup_manager.js: 실제 CMS 팝업에서 타이틀바 숨김 (관리자 목록에서만 표시)

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
