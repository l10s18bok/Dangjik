# docker_start.sh
#!/bin/bash
# [SB] 대시보드 체커 웹 애플리케이션 실행 스크립트

echo "🚀 대시보드 체커 실행 스크립트 시작"
echo "======================================"

# [SB] 현재 디렉토리 확인
if [ ! -f "Dockerfile" ] || [ ! -f "docker-compose.yml" ]; then
    echo "❌ 오류: crawlai_new 디렉토리에서 실행해주세요."
    echo "   Dockerfile과 docker-compose.yml이 필요합니다."
    exit 1
fi

# [SB] Docker 데스크탑 실행 상태 확인
echo "🔍 Docker 상태 확인 중..."
if ! docker info >/dev/null 2>&1; then
    echo "❌ 오류: Docker가 실행되지 않았습니다."
    echo "   Docker Desktop을 실행한 후 다시 시도해주세요."
    exit 1
fi
echo "✅ Docker 실행 확인됨"

# [SB] docker-compose vs docker compose 명령어 확인
DOCKER_COMPOSE_CMD="docker compose"
if command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker-compose"
fi

# [SB] 기존 컨테이너 정리 (있는 경우)
echo "🧹 기존 컨테이너 정리 중..."
$DOCKER_COMPOSE_CMD down 2>/dev/null || true

# [SB] requirements.txt에 Flask 추가 확인
echo "📋 requirements.txt 확인 중..."
if ! grep -q "flask" requirements.txt; then
    echo "⚠️  requirements.txt에 flask 추가 중..."
    echo "flask" >> requirements.txt
fi

# [SB] templates 디렉토리 확인
if [ ! -d "templates" ]; then
    echo "📁 templates 디렉토리 생성 중..."
    mkdir -p templates
    echo "⚠️  templates 디렉토리에 HTML 파일들을 저장해주세요:"
    echo "   - base.html"
    echo "   - index.html" 
    echo "   - login.html"
    echo "   - progress.html"
    echo ""
    read -p "HTML 파일들을 저장했으면 Enter를 눌러주세요..."
fi

# [SB] Ollama 서버 상태 확인 (Mac 호스트)
echo "🤖 호스트 Ollama 서버 확인 중..."
if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "✅ Ollama 서버 실행 확인됨"
    
    # [SB] EEVE 모델 확인
    if curl -s http://localhost:11434/api/tags | grep -q "EEVE-Korean"; then
        echo "✅ EEVE-Korean 모델 확인됨"
    else
        echo "⚠️  EEVE-Korean 모델이 없습니다."
        echo "   다음 명령어로 모델을 다운로드하세요:"
        echo "   ollama pull EEVE-Korean-10.8B:latest"
    fi
else
    echo "❌ Ollama 서버가 실행되지 않았습니다."
    echo "   터미널에서 'ollama serve' 명령어를 실행해주세요."
    echo ""
    read -p "Ollama 서버를 실행했으면 Enter를 눌러주세요..."
fi

# [SB] Docker 이미지 존재 여부 확인 및 사용자 선택
echo "🔍 Docker 이미지 확인 중..."

# [SB] 프로젝트 이름 추출 (디렉토리 이름 기반)
PROJECT_NAME=$(basename "$(pwd)")

if docker images | grep -q "${PROJECT_NAME}"; then
    echo "✅ 기존 Docker 이미지가 발견되었습니다."
    echo ""
    read -p "기존 이미지를 사용하시겠습니까? (y: 기존 사용, n: 재빌드) [y/n]: " choice
    
    case $choice in
        [Yy]|[Yy][Ee][Ss]|"")
            echo "✅ 기존 이미지를 사용합니다."
            SKIP_BUILD=true
            ;;
        [Nn]|[Nn][Oo])
            echo "🔨 이미지를 재빌드합니다..."
            echo "   (5-10분 소요될 수 있습니다)"
            SKIP_BUILD=false
            ;;
        *)
            echo "⚠️  잘못된 입력입니다. 기존 이미지를 사용합니다."
            SKIP_BUILD=true
            ;;
    esac
else
    echo "🔨 Docker 이미지가 없습니다. 빌드를 시작합니다..."
    echo "   (최초 실행 시 5-10분 소요될 수 있습니다)"
    SKIP_BUILD=false
fi

# [SB] 빌드 실행 여부 결정
if [ "$SKIP_BUILD" != "true" ]; then
    $DOCKER_COMPOSE_CMD build
    
    if [ $? -ne 0 ]; then
        echo "❌ Docker 이미지 빌드 실패"
        exit 1
    fi
    
    echo "✅ Docker 이미지 빌드 완료"
else
    echo "⏩ 빌드를 건너뜁니다."
fi

# [SB] 컨테이너 시작
echo "🚀 웹 애플리케이션 시작 중..."
$DOCKER_COMPOSE_CMD up -d --remove-orphans

if [ $? -ne 0 ]; then
    echo "❌ 컨테이너 시작 실패"
    exit 1
fi

# [SB] 서비스 상태 확인
echo "⏳ 서비스 시작 대기 중..."
sleep 10

if curl -s http://localhost:5001/health >/dev/null 2>&1; then
    echo "✅ 웹 애플리케이션 시작 완료!"
    echo ""
    echo "🌐 웹 브라우저에서 접속하세요:"
    echo "   http://localhost:5001"
    echo ""
    echo "📝 로그 확인: $DOCKER_COMPOSE_CMD logs -f"
    echo "🛑 종료하기: $DOCKER_COMPOSE_CMD down"
else
    echo "⚠️  웹 애플리케이션이 아직 시작되지 않았습니다."
    echo "   잠시 후 http://localhost:5001 에 접속해보세요."
fi

echo ""
echo "======================================"
echo "🎉 대시보드 체커 실행 완료!"