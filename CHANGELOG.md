# PostMoon 릴리즈 노트

## v1.5.1 (폴더 통째 업로드 방식 도입)
- 서버 배포 방식을 단일 파일 업로드에서 **PostMoon 폴더 통째 업로드**로 변경
- 관리자 페이지(admin_api_keys.php)에서 **Rhymix 설정 경로 자동 탐지**, 내부 링크 상대 경로 수정
- 서버 브릿지(secure_api.php) **버전 1.5.1**로 갱신
- README 설치 가이드 업데이트: 엔드포인트를 `/PostMoon/secure_api.php`로 명시

### 변경 사항 요약
- 엔드포인트: `https://도메인/PostMoon/secure_api.php`
- 키 발급 페이지: `https://도메인/PostMoon/admin_api_keys.php`
- 기존 루트 업로드 방식은 사용하지 않음. 루트에 섞여 올리던 파일은 제거 권장

### 보안 권장
- 필요 시 **파일명/폴더명 난수화**로 URL 추측 방어 강화
- 키 발급 후 `admin_api_keys.php`는 삭제 또는 이름 변경
- STRICT_AUTH_HEADER 유지(헤더 인증만 허용), 디렉터리 인덱싱 비활성화

### 업그레이드 가이드
1. 서버에 Rhymix 루트로 **PostMoon 폴더 전체 업로드**
2. 브라우저에서 `https://도메인/PostMoon/admin_api_keys.php` 접속 후 키 발급/확인
3. 클라이언트(PostMoon 프로그램)에서 **API URL**을 `https://도메인/PostMoon/secure_api.php`로 변경
4. 테스트 업로드로 정상 동작 확인

### 호환성
- 클라이언트 실행 파일 **재빌드 불필요**: 서버 경로만 변경되었으며, 프로그램의 API URL만 새 경로로 설정하면 동작
