# Dangjik - 당직 대시보드 모니터링 시스템

Python 기반의 웹 크롤링 AI 애플리케이션으로 대시보드를 자동으로 모니터링하고 Excel 보고서를 생성하여 Mattermost로 전송합니다.

## 주요 기능

- 🤖 **AI 기반 분석**: Ollama EEVE 모델을 사용한 대시보드 상태 분석
- 📊 **자동 보고서 생성**: Excel 형태의 대시보드 현황 보고서 자동 생성
- 💬 **Mattermost 연동**: 실시간 보고서 전송 및 알림
- 🌐 **웹 인터페이스**: Flask 기반의 직관적인 웹 UI
- 🐳 **Docker 지원**: 컨테이너화된 배포 환경
- 📸 **스크린샷 첨부**: 대시보드 캡처 이미지가 포함된 상세 보고서

## 시스템 요구사항

- Python 3.11+
- Node.js 18+ (Playwright용)
- Docker & Docker Compose
- Ollama (EEVE 모델)
- Mattermost 서버

## 빠른 시작

### 1. 저장소 클론
```bash
git clone https://github.com/l10s18bok/Dangjik.git
cd Dangjik
```

### 2. 환경 변수 설정
`.env` 파일을 생성하고 다음 내용을 설정하세요:

```env
# 대시보드 설정
DASHBOARD_URL=https://your-dashboard-url.com
DASHBOARD_USERNAME=your_username
DASHBOARD_PASSWORD=your_password

# 모니터링 링크들
FRONTEND_LINK=https://your-frontend.com
PARKING_LINK=https://your-parking.com
URL_LINK=https://your-url.com
FURL_LINK=https://your-furl.com

# Mattermost 설정
MATTERMOST_URL=https://your-mattermost.com
MATTERMOST_TEAM_INNOGS=your_team_name
MATTERMOST_CHANNEL=당직체크

# Flask 설정
FLASK_SECRET_KEY=your-secret-key-here
```

### 3. Ollama 설정
Mac에서 Ollama 서버 실행:
```bash
# Ollama 설치 (Mac)
brew install ollama

# EEVE 모델 다운로드
ollama pull EEVE-Korean-Instruct-10.8B-v1.0:latest

# Ollama 서버 시작
ollama serve
```

### 4. Docker로 실행
```bash
# 컨테이너 빌드 및 실행
docker-compose up --build

# 백그라운드 실행
docker-compose up -d
```

### 5. 웹 인터페이스 접근
브라우저에서 `http://localhost:5001`로 접속하여 Mattermost 계정으로 로그인

## 사용법

1. **웹 접속**: `http://localhost:5001`
2. **로그인**: Mattermost 사용자명/비밀번호 입력
3. **자동 실행**: 로그인 성공 시 자동으로 대시보드 모니터링 시작
4. **진행 상황**: 실시간 진행률과 단계별 상태 확인
5. **보고서 수신**: 완료 후 Mattermost로 Excel 보고서 자동 전송

## 프로젝트 구조

```
crawlai_new/
├── main.py                 # 메인 크롤링 로직
├── app.py                  # Flask 웹 애플리케이션
├── requirements.txt        # Python 의존성
├── Dockerfile             # Docker 설정
├── docker-compose.yml     # Docker Compose 설정
├── utils/                  # 유틸리티 모듈
│   ├── xlsx.py            # Excel 보고서 생성
│   ├── fields.py          # 데이터 필드 추출
│   ├── llm.py             # AI 분석 로직
│   └── mattermost.py      # Mattermost 연동
├── templates/             # HTML 템플릿
├── logs/                  # 로그 파일
└── screenshot/            # 스크린샷 저장
```

## 특징

### AI 분석 기능
- Ollama EEVE 모델을 사용한 자연어 처리
- 대시보드 상태의 자동 해석 및 분석
- 예치금, 서비스 상태, 링크 유효성 검증

### 자동화된 보고서
- Excel 형식의 상세한 현황 보고서
- 대시보드 스크린샷 자동 첨부
- 시간별 추이 및 상태 변화 추적

### 실시간 모니터링
- 웹 인터페이스를 통한 실시간 진행 상황 확인
- 단계별 상태 업데이트 및 진행률 표시
- 오류 발생 시 즉시 알림

## 개발 환경

### 로컬 개발
```bash
# 가상환경 생성
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# Playwright 브라우저 설치
playwright install chromium

# 개발 서버 실행
python app.py
```

### 로그 확인
```bash
# Docker 로그 확인
docker-compose logs -f web-app

# 로컬 로그 파일
tail -f logs/crawler.log
```

## 문제 해결

### 일반적인 문제
1. **Ollama 연결 실패**: Mac에서 `ollama serve` 명령어로 서버 실행 확인
2. **모델 없음**: `ollama pull EEVE-Korean-Instruct-10.8B-v1.0:latest` 실행
3. **포트 충돌**: `docker-compose.yml`에서 포트 번호 변경
4. **권한 오류**: `chmod +x docker_start.sh` 실행

### 환경변수 확인
```bash
# 시스템 상태 API로 확인
curl http://localhost:5001/api/status
```

## 기여

버그 리포트나 기능 제안은 GitHub Issues를 통해 제출해주세요.
