# [SB] Rocky Linux 최신 버전 (M1 Mac 호환)
FROM rockylinux:9

# [SB] 환경변수 설정 - 한국어 로케일 및 시간대 설정
ENV LANG=ko_KR.UTF-8
ENV LC_ALL=ko_KR.UTF-8
ENV TZ=Asia/Seoul
ENV PYTHONUNBUFFERED=1

# [SB] 작업 디렉토리 설정 - Mac 공유 폴더와 동일한 경로
WORKDIR /app

# [SB] 시스템 업데이트 및 필수 패키지 설치
RUN dnf update -y && \
    dnf install -y epel-release && \
    dnf update -y && \
    dnf groupinstall "Development Tools" -y && \
    dnf install -y --allowerasing \
        python3 \
        python3-pip \
        python3-devel \
        curl \
        wget \
        git \
        glibc-langpack-ko \
        && dnf clean all

# [SB] 한글 폰트 설치를 위한 기본 도구 설치
RUN dnf install -y \
        langpacks-ko \
        fontconfig \
        && dnf clean all

# [SB] 한글 폰트 직접 다운로드 및 설치 (Rocky Linux 9 호환)
RUN mkdir -p /usr/share/fonts/truetype/noto && \
    curl -L -o /usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc \
    "https://github.com/googlefonts/noto-cjk/releases/download/Sans2.004/04_NotoSansCJK-Regular.ttc" && \
    fc-cache -fv

# [SB] Python 3.11 설치 및 기본 Python으로 설정 (crawl4ai 호환성)
RUN dnf install -y python3.11 python3.11-pip python3.11-devel && \
    alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 50 && \
    alternatives --install /usr/bin/pip3 pip3 /usr/bin/pip3.11 50 && \
    python3 --version

# [SB] pip 최신 버전으로 업그레이드
RUN python3 -m pip install --upgrade pip setuptools wheel

# [SB] Node.js 18 LTS 설치 (Playwright용)
RUN curl -fsSL https://rpm.nodesource.com/setup_18.x | bash - && \
    dnf install -y nodejs

# [SB] Playwright 의존성 설치 (Rocky Linux용)
RUN dnf install -y \
        libX11 \
        libXcomposite \
        libXcursor \
        libXdamage \
        libXext \
        libXi \
        libXtst \
        cups-libs \
        libXScrnSaver \
        libXrandr \
        alsa-lib \
        pango \
        atk \
        cairo-gobject \
        gtk3 \
        gdk-pixbuf2 \
        && dnf clean all

# [SB] Python 패키지 설치를 위한 requirements.txt 복사
COPY requirements.txt /tmp/requirements.txt

# [SB] Python 패키지 설치 - 모든 필요 패키지 설치
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

# [SB] Playwright 브라우저 설치
RUN python3 -m playwright install chromium

# [SB] 애플리케이션 파일 복사
COPY . /app/

# [SB] 웹앱 포트만 노출 - Ollama 포트 제거
EXPOSE 5000

# [SB] 헬스체크 설정 - 웹앱 상태만 확인
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# [SB] Flask 애플리케이션 시작 - Ollama는 호스트에서 실행
CMD ["python3", "app.py"]