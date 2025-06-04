# DangJik AI 웹 크롤링 및 데이터 분석 시스템

DangJik은 AI 기반 웹 크롤링 및 대시보드 데이터 분석 시스템입니다. Flask 웹 애플리케이션과 AI 모델을 활용하여 자동화된 보고서를 생성합니다.

## 🚀 주요 기능

- **AI 기반 웹 크롤링**: crawl4ai를 이용한 지능형 웹 크롤링
- **자동 대시보드 분석**: AI가 대시보드 상태를 자동 분석
- **Excel 보고서 생성**: 분석 결과를 Excel 형태로 자동 생성
- **Mattermost 연동**: 보고서를 Mattermost로 자동 전송
- **Docker 기반 배포**: Rocky Linux 9 기반 컨테이너화
- **실시간 진행 상태**: 웹 UI를 통한 실시간 작업 진행 상황 확인

## 🛠 기술 스택

- **Backend**: Python 3.11, Flask, FastAPI
- **AI/ML**: Ollama (EEVE 모델)
- **웹 크롤링**: crawl4ai, Playwright, BeautifulSoup4
- **데이터 처리**: pandas, openpyxl
- **통신**: Mattermost API
- **컨테이너화**: Docker, Docker Compose
- **OS**: Rocky Linux 9 (M1 Mac 호환)

## 📋 설치 및 실행

### 1. 사전 요구사항

- Docker & Docker Compose
- Ollama (호스트 시스템에 설치)
- Python 3.11+ (개발 환경)

### 2. 환경 설정

`.env` 파일을 생성하고 다음 변수들을 설정하세요:

```env
# 대시보드 설정
DASHBOARD_URL=your_dashboard_url
DASHBOARD_USERNAME=your_username
DASHBOARD_PASSWORD=your_password

# 링크 확인 URL들
FRONTEND_LINK=your_frontend_url
PARKING_LINK=your_parking_url
URL_LINK=your_url_link
FURL_LINK=your_furl_link

# Mattermost 설정
MATTERMOST_URL=your_mattermost_url
MATTERMOST_TEAM_INNOGS=your_team_name
MATTERMOST_CHANNEL=your_channel_name

# Flask 설정
FLASK_SECRET_KEY=your_secret_key
```

### 3. Docker로 실행

```bash
# 저장소 클론
git clone https://github.com/l10s18bok/Dangjik.git
cd Dangjik

# Docker Compose로 실행
docker-compose up -d

# 웹 애플리케이션 접속
open http://localhost:5001
```

## 📁 프로젝트 구조

```
Dangjik/
├── main.py              # 메인 크롤링 로직
├── app.py               # Flask 웹 애플리케이션
├── requirements.txt     # Python 패키지 의존성
├── Dockerfile          # Docker 이미지 빌드 설정
├── docker-compose.yml  # Docker Compose 설정
├── utils/              # 유틸리티 모듈들
├── templates/          # Flask 템플릿
├── logs/              # 로그 파일들
└── screenshot/        # 스크린샷 저장소
```

## 🔧 사용법

1. 웹 애플리케이션에 접속 (`http://localhost:5001`)
2. Mattermost 계정으로 로그인
3. 자동으로 대시보드 크롤링 및 AI 분석 시작
4. 실시간 진행 상황 확인
5. 완료 후 Mattermost로 보고서 자동 전송

---

**주의사항**: 이 시스템은 내부 대시보드 모니터링을 위해 설계되었습니다.
