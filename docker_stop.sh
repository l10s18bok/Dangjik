# docker_stop.sh
#!/bin/bash
# [SB] 대시보드 체커 종료 스크립트

echo "🛑 대시보드 체커 종료 스크립트 시작"
echo "======================================"

# [SB] docker-compose vs docker compose 명령어 확인
DOCKER_COMPOSE_CMD="docker compose"
if command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker-compose"
fi

# [SB] 실행 중인 컨테이너 확인
echo "🔍 실행 중인 컨테이너 확인..."
RUNNING_CONTAINERS=$($DOCKER_COMPOSE_CMD ps -q 2>/dev/null)

if [ -z "$RUNNING_CONTAINERS" ]; then
    echo "ℹ️  실행 중인 컨테이너가 없습니다."
else
    echo "📋 실행 중인 컨테이너:"
    $DOCKER_COMPOSE_CMD ps
    echo ""
    
    # [SB] 컨테이너 종료
    echo "🛑 컨테이너 종료 중..."
    $DOCKER_COMPOSE_CMD down
    
    if [ $? -eq 0 ]; then
        echo "✅ 컨테이너 종료 완료"
    else
        echo "❌ 컨테이너 종료 실패"
    fi
fi

# [SB] 5000번 포트 사용 프로세스 확인 및 종료
echo ""
echo "🔍 포트 5000 사용 프로세스 확인..."
PORT_PROCESS=$(lsof -ti:5000 2>/dev/null)

if [ -n "$PORT_PROCESS" ]; then
    echo "⚠️  포트 5000을 사용하는 프로세스 발견: PID $PORT_PROCESS"
    echo "📋 프로세스 정보:"
    ps -p $PORT_PROCESS 2>/dev/null || echo "   프로세스 정보를 가져올 수 없습니다."
    
    read -p "이 프로세스를 종료하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🛑 프로세스 종료 중..."
        kill -9 $PORT_PROCESS 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "✅ 프로세스 종료 완료"
        else
            echo "❌ 프로세스 종료 실패"
        fi
    else
        echo "ℹ️  프로세스를 유지합니다."
    fi
else
    echo "✅ 포트 5000이 사용 가능합니다."
fi

# [SB] Docker 이미지 정리 (선택사항)
echo ""
read -p "Docker 이미지도 삭제하시겠습니까? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🧹 Docker 이미지 정리 중..."
    
    # [SB] 프로젝트 관련 이미지만 삭제
    PROJECT_IMAGES=$(docker images | grep "crawlai_new" | awk '{print $3}')
    if [ -n "$PROJECT_IMAGES" ]; then
        echo "$PROJECT_IMAGES" | xargs docker rmi -f
        echo "✅ 프로젝트 이미지 삭제 완료"
    else
        echo "ℹ️  삭제할 프로젝트 이미지가 없습니다."
    fi
    
    # [SB] 사용하지 않는 이미지 정리
    echo "🧹 사용하지 않는 이미지 정리 중..."
    docker image prune -f
    echo "✅ 이미지 정리 완료"
fi

echo ""
echo "======================================"
echo "🎉 대시보드 체커 종료 완료!"
echo ""
echo "💡 팁:"
echo "   - 다시 시작: ./start.sh"
echo "   - 포트 확인: lsof -ti:5000"
echo "   - Docker 상태: docker ps"