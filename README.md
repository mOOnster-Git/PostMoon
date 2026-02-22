# PostMoon - AI Powered Rhymix Uploader

**PostMoon**은 구글 Gemini AI를 활용하여 게시글을 분석, 정리하고 라이믹스(Rhymix) 기반 웹사이트에 안전하게 업로드하는 통합 솔루션입니다.
본 패키지는 **사용자 PC용 프로그램(Client)**과 **서버 연동용 파일(Server)**로 구성되어 있습니다.

---

## 📦 PostMoon Client (v1.5.12)
- **설정 파일 위치 변경**: `config.json` 파일이 이제 `AppData/Local/PostMoon` 폴더에 저장됩니다. (바탕화면 오염 방지)
- **마우스 우클릭 지원**: 모든 입력창에서 마우스 우클릭 메뉴(복사/붙여넣기)를 지원합니다.
- **최적화된 화면**: 1200x800 해상도로 표준 모니터에 최적화되었습니다.
- **자동 업데이트**: GitHub 릴리즈를 통해 최신 버전을 자동으로 확인합니다.

## 🛠️ Server Scripts (v1.5.19)
- **보안 강화**: 디버그 로그가 기본적으로 비활성화됩니다. (`ENABLE_DEBUG = false`)
- **설치 간소화**: 폴더 업로드 방식 지원 (코어 파일과 섞이지 않음)
- **호환성**: Nginx/Apache 모두 지원, 상대 경로 자동 탐지.

## 📥 설치 방법 (Installation)

### 1. 서버 (Server)
1. `PostMoon` 폴더를 그대로 라이믹스 설치 경로(index.php가 있는 곳)에 업로드합니다.
   - 예: `https://mysite.com/PostMoon/`
2. 관리자 페이지에 접속하여 API 키를 생성합니다.
   - 접속 주소: `https://mysite.com/PostMoon/admin_api_keys.php`
3. 생성된 API 키를 복사해둡니다.

### 2. 클라이언트 (Client)
1. `PostMoon.exe`를 실행합니다.
2. 설정(Settings) 메뉴를 엽니다.
3. **API URL**: `https://mysite.com/PostMoon/secure_api.php` 입력
4. **API Key**: 발급받은 키 입력
5. **MID**: 게시판 모듈 ID 입력
6. 저장 후 사용합니다.

## ⚠️ 주의사항
- `secure_api.php`와 `admin_api_keys.php`는 `PostMoon` 폴더 내에 있어야 정상 작동합니다.
- 폴더명을 변경해도 작동하지만, 클라이언트 설정의 URL도 그에 맞게 변경해야 합니다.
