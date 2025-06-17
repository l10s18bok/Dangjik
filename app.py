# app.py
import asyncio
import json
import os
import sys
import threading
import time
import subprocess
import requests
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from dotenv import load_dotenv
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.mattermost import _get_mattermost_credentials, _create_mattermost_driver

# [SB] 환경 변수 로드
load_dotenv()

# [SB] Flask 앱 초기화 및 설정
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-change-this')

# [SB] 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# [SB] 전역 진행 상태 저장소
progress_store = {}

# [SB] Ollama 연결 상태 확인
def check_ollama_connection():
    """[SB] Ollama 서버 연결 상태 및 EEVE 모델 확인 (Docker → Mac 호스트)"""
    try:
        # host.docker.internal:11434는 Docker에서 호스트 머신에 접근하는 방법
        ollama_url = 'http://host.docker.internal:11434'
        
        print(f"[SB] Ollama 연결 시도: {ollama_url}")
        
        # [SB] 1단계: Ollama 서버 연결 확인
        response = requests.get(f"{ollama_url}/api/tags", timeout=10)
        if response.status_code != 200:
            return False, f"Mac Ollama 서버 응답 오류 (상태코드: {response.status_code})"
        
        # [SB] 2단계: 사용 가능한 모델 목록 확인
        models_data = response.json()
        available_models = [model['name'] for model in models_data.get('models', [])]
        
        print(f"[SB] 사용 가능한 모델: {available_models}")
        
        # [SB] 3단계: EEVE 모델 존재 확인 (대소문자 구분 없이)
        eeve_models = [model for model in available_models if 'EEVE' in model.upper() or 'eeve' in model.lower()]
        
        if not eeve_models:
            return False, f"EEVE 모델이 Local에 설치되지 않았습니다. 사용 가능한 모델: {', '.join(available_models[:3])}..."
        
        # [SB] 4단계: LLM 모델 응답 테스트 (간단한 요청)
        print(f"[SB] EEVE 모델 테스트: {eeve_models[0]}")
        test_payload = {
            "model": eeve_models[0],
            "prompt": "안녕하세요",
            "stream": False
        }
        
        test_response = requests.post(f"{ollama_url}/api/generate", json=test_payload, timeout=15)
        if test_response.status_code != 200:
            return False, f"Mac EEVE 모델 응답 테스트 실패 (상태코드: {test_response.status_code})"
        
        return True, f"Mac Ollama 연결 성공 (모델: {eeve_models[0]})"
        
    except requests.exceptions.ConnectionError:
        return False, "Mac Ollama 서버에 연결할 수 없습니다. Mac에서 'ollama serve' 명령어로 서버를 실행해주세요."
    except requests.exceptions.Timeout:
        return False, "Mac Ollama 서버 응답 시간 초과. 네트워크 상태를 확인해주세요."
    except Exception as e:
        return False, f"Mac Ollama 연결 확인 중 오류: {str(e)}"

def run_main_process(user_id, mattermost_username, mattermost_password):
    """[SB] main.py의 크롤링 로직을 별도 스레드에서 실행하는 함수"""
    try:
        # [SB] 진행 상태 초기화
        progress_store[user_id] = {
            'status': 'running',
            'progress': 0,
            'step': 1,
            'message': '환경 설정 중...'
        }
        
        # [SB] 환경 변수 임시 설정
        original_mm_username = os.environ.get('MATTERMOST_USERNAME')
        original_mm_password = os.environ.get('MATTERMOST_PASSWORD')
        
        os.environ['MATTERMOST_USERNAME'] = mattermost_username
        os.environ['MATTERMOST_PASSWORD'] = mattermost_password
        
        # [SB] 1단계: 환경 설정 완료 (10%)
        progress_store[user_id].update({
            'progress': 10,
            'step': 1,
            'message': '환경 설정 완료, 대시보드 접속 시작...'
        })
        time.sleep(0.5)
        
        # [SB] 2단계: 대시보드 로그인 시작 (20%)
        progress_store[user_id].update({
            'progress': 20,
            'step': 2,
            'message': '대시보드에 로그인 중...'
        })
        time.sleep(1)
        
        # [SB] 3단계: 크롤링 진행 (30%)
        progress_store[user_id].update({
            'progress': 30,
            'step': 3,
            'message': '대시보드 데이터 수집 중...'
        })
        
        # [SB] subprocess로 main.py 실행 (환경변수가 자동으로 전달됨)
        try:
            # [SB] 실시간 진행률 업데이트를 위한 Popen 사용
            process = subprocess.Popen([
                sys.executable, 'main.py'
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            env=os.environ.copy()
            )
            
            # [SB] 프로세스 실행 중 진행률 시뮬레이션
            start_time = time.time()
            ai_analysis_started = False
            
            while process.poll() is None:  # 프로세스가 실행 중인 동안
                elapsed = time.time() - start_time
                
                if elapsed < 10:  # 처음 10초: 크롤링 단계 (30% → 45%)
                    progress = min(45, 30 + (elapsed / 10) * 15)
                    message = '대시보드 크롤링 진행 중...'
                elif elapsed < 15:  # 10-15초: 크롤링 완료 단계 (45% → 50%)
                    progress = min(50, 45 + ((elapsed - 10) / 5) * 5)
                    message = '데이터 추출 완료, AI 분석 준비 중...'
                elif elapsed < 45:  # 15-45초: AI 분석 단계 (50% → 85%)
                    if not ai_analysis_started:
                        progress_store[user_id].update({
                            'progress': 50,
                            'step': 4,
                            'message': '🤖 AI 분석 시작...'
                        })
                        ai_analysis_started = True
                    
                    # AI 분석 진행률을 세분화
                    ai_progress = (elapsed - 15) / 30  # 0 → 1 over 30 seconds
                    progress = 50 + (ai_progress * 35)  # 50% → 85%
                    
                    if ai_progress < 0.3:
                        message = '🤖 AI가 대시보드 상태를 분석하고 있습니다...'
                    elif ai_progress < 0.6:
                        message = '🤖 예치금 및 서비스 상태를 검증 중...'
                    elif ai_progress < 0.9:
                        message = '🤖 링크 상태 및 시스템 점검 중...'
                    else:
                        message = '🤖 AI 분석 완료, 보고서 생성 중...'
                else:  # 45초 이후: 보고서 생성 및 전송 (85% → 95%)
                    progress = min(95, 85 + ((elapsed - 45) / 10) * 10)
                    message = '📊 Excel 보고서 생성 중...'
                
                progress_store[user_id].update({
                    'progress': int(progress),
                    'message': message
                })
                
                time.sleep(1)  # 1초마다 업데이트
                
                # [SB] 타임아웃 체크 (5분)
                if elapsed > 300:
                    process.terminate()
                    raise Exception("처리 시간 초과 (5분)")
            
            # [SB] 프로세스 완료 후 결과 확인
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.strip() if stderr else "알 수 없는 오류"
                logger.error(f"main.py stderr: {error_msg}")
                logger.error(f"main.py stdout: {stdout}")
                raise Exception(f"대시보드 처리 실패: {error_msg}")
            
            # [SB] 실제 결과 기반 최종 메시지 결정
            if "성공적으로 전송되었습니다" in stdout:
                final_message = '🎉 Mattermost 전송 완료!'
                final_progress = 100
            elif "전송 실패" in stdout:
                final_message = '⚠️ Excel 생성 완료 (Mattermost 전송 실패)'
                final_progress = 95
            else:
                final_message = '📄 Excel 생성 완료'
                final_progress = 95
            
            # [SB] 최종 완료 상태
            progress_store[user_id] = {
                'status': 'completed',
                'progress': final_progress,
                'step': 5,
                'message': final_message,
                'result': {
                    'success': final_progress == 100,
                    'timestamp': datetime.now().isoformat(),
                    'auto_logout': True,
                    'stdout': stdout[-1000:] if stdout else "",
                }
            }
            
        except subprocess.TimeoutExpired:
            raise Exception("처리 시간 초과 (5분) - 네트워크나 서버 상태를 확인해주세요")
        except Exception as e:
            raise Exception(f"대시보드 처리 중 오류: {str(e)}")
            
    except Exception as e:
        logger.error(f"메인 프로세스 실행 오류: {e}")
        progress_store[user_id] = {
            'status': 'error',
            'progress': 0,
            'step': 0,
            'message': f'❌ 오류 발생: {str(e)}',
            'error': str(e),
            'auto_logout': True
        }
        
    finally:
        # [SB] 환경 변수 복원
        if original_mm_username:
            os.environ['MATTERMOST_USERNAME'] = original_mm_username
        else:
            os.environ.pop('MATTERMOST_USERNAME', None)
            
        if original_mm_password:
            os.environ['MATTERMOST_PASSWORD'] = original_mm_password
        else:
            os.environ.pop('MATTERMOST_PASSWORD', None)

def check_main_py_status():
    """[SB] main.py 파일 상태 및 필수 환경변수 확인"""
    try:
        # [SB] main.py 파일 존재 확인
        main_py_path = Path('main.py')
        if not main_py_path.exists():
            return False, "main.py 파일이 존재하지 않습니다"
        
        # [SB] 필수 환경변수 확인
        required_env = [
            'DASHBOARD_URL', 'DASHBOARD_USERNAME', 'DASHBOARD_PASSWORD',
            'FRONTEND_LINK', 'PARKING_LINK', 'URL_LINK', 'FURL_LINK',
            'MATTERMOST_URL'
        ]
        
        missing_env = [env for env in required_env if not os.getenv(env)]
        if missing_env:
            return False, f"필수 환경변수 누락: {', '.join(missing_env)}"
        
        # [SB] main.py 구문 검사 (간단한 체크)
        with open('main.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # [SB] 기본 구문 체크
        try:
            compile(content, 'main.py', 'exec')
        except SyntaxError as e:
            return False, f"main.py 구문 오류: {e}"
            
        return True, "main.py 상태 정상"
        
    except Exception as e:
        return False, f"main.py 확인 중 오류: {e}"

@app.route('/')
def index():
    """[SB] 홈페이지 - 세션 확인 후 로그인 페이지로 리다이렉트"""
    # [SB] 기존 세션 정리 (새로 시작할 때마다 깨끗하게)
    session.clear()
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """[SB] 로그인 페이지 - Mattermost 인증 및 즉시 실행"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('사용자ID와 비밀번호를 모두 입력해주세요.', 'error')
            return render_template('login.html')
        
        # [SB] main.py 및 환경변수 사전 체크
        status_ok, status_message = check_main_py_status()
        if not status_ok:
            flash(f'시스템 설정 오류: {status_message}', 'error')
            return render_template('login.html')
        
        # [SB] Ollama 연결 상태 확인
        ollama_ok, ollama_message = check_ollama_connection()
        if not ollama_ok:
            flash(f'❌ AI 연결을 확인해주세요: {ollama_message}', 'error')
            logger.error(f"Ollama 연결 실패: {ollama_message}")
            return render_template('login.html')
        else:
            logger.info(f"Ollama 연결 성공: {ollama_message}")
        
        # [SB] Mattermost 인증 시도 (사용자가 입력한 정보로)
        try:
            mattermost_url = os.getenv('MATTERMOST_URL')
            driver, success = _create_mattermost_driver(mattermost_url, username, password)
            if not success:
                flash('로그인 실패: Mattermost 서버 연결 오류', 'error')
                return render_template('login.html')
            
            driver.login()
            user = driver.users.get_user('me')
            driver.logout()
            
            # [SB] 세션에 사용자 정보 저장
            session['user_id'] = user['id']
            session['username'] = user.get('username', username)
            session['display_name'] = user.get('nickname') or f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or username
            
            # [SB] 백그라운드에서 main.py 실행 시작 (사용자 입력 정보 전달)
            thread = threading.Thread(
                target=run_main_process,
                args=(user['id'], username, password)
            )
            thread.daemon = True
            thread.start()
            
            flash('✅ 로그인 성공! 대시보드 체크를 시작합니다.', 'success')
            return redirect(url_for('progress'))
            
        except Exception as e:
            logger.error(f"로그인 오류: {e}")
            flash('❌ 로그인 실패: 사용자명 또는 비밀번호를 확인해주세요.', 'error')
    
    return render_template('login.html')

@app.route('/progress')
def progress():
    """[SB] 진행 상태 페이지"""
    if 'user_id' not in session:
        flash('로그인이 필요합니다.', 'warning')
        return redirect(url_for('login'))
    
    return render_template('progress.html', user=session)

@app.route('/logout')
def logout():
    """[SB] 로그아웃 처리"""
    user_id = session.get('user_id')
    if user_id and user_id in progress_store:
        del progress_store[user_id]  # 진행 상태 정리
    
    session.clear()
    flash('로그아웃되었습니다.', 'info')
    return redirect(url_for('index'))

@app.route('/api/progress')
def api_progress():
    """[SB] 진행 상태 API - AJAX로 실시간 상태 확인"""
    if 'user_id' not in session:
        return jsonify({'error': '인증 필요', 'redirect': '/login'}), 401
    
    user_id = session['user_id']
    
    # [SB] 진행 상태 반환
    if user_id in progress_store:
        progress_data = progress_store[user_id]
        
        # [SB] 완료 또는 오류 시 자동 로그아웃 처리
        if progress_data.get('auto_logout') and progress_data['status'] in ['completed', 'error']:
            # [SB] 5초 후 자동 로그아웃 설정
            progress_data['logout_countdown'] = 5
            
        return jsonify(progress_data)
    else:
        # [SB] 진행 상태가 없으면 초기화
        return jsonify({
            'status': 'running',
            'progress': 0,
            'step': 1,
            'message': '시작 준비 중...'
        })

@app.route('/api/logout')
def api_logout():
    """[SB] API를 통한 로그아웃 처리"""
    user_id = session.get('user_id')
    if user_id and user_id in progress_store:
        del progress_store[user_id]  # 진행 상태 정리
    
    session.clear()
    return jsonify({'success': True, 'redirect': '/login'})

@app.route('/health')
def health():
    """[SB] 헬스체크 엔드포인트 - Docker 컨테이너 상태 확인용"""
    # [SB] main.py 상태도 함께 체크
    main_ok, main_message = check_main_py_status()
    # [SB] Ollama 상태도 함께 체크
    ollama_ok, ollama_message = check_ollama_connection()
    
    overall_status = 'healthy' if (main_ok and ollama_ok) else 'warning'
    
    return jsonify({
        'status': overall_status,
        'timestamp': datetime.now().isoformat(),
        'main_py_status': main_message,
        'ollama_status': ollama_message,
        'active_sessions': len(progress_store)
    })

@app.route('/api/status')
def api_status():
    """[SB] 시스템 상태 확인 API"""
    main_ok, main_message = check_main_py_status()
    ollama_ok, ollama_message = check_ollama_connection()
    
    return jsonify({
        'main_py_ok': main_ok,
        'main_py_message': main_message,
        'ollama_ok': ollama_ok,
        'ollama_message': ollama_message,
        'active_sessions': len(progress_store),
        'env_check': {
            'dashboard_configured': bool(os.getenv('DASHBOARD_URL')),
            'mattermost_configured': bool(os.getenv('MATTERMOST_URL')),
            'links_configured': all([
                os.getenv('FRONTEND_LINK'),
                os.getenv('PARKING_LINK'), 
                os.getenv('URL_LINK'),
                os.getenv('FURL_LINK')
            ])
        }
    })

if __name__ == '__main__':
    # [SB] 시작 시 상태 체크
    status_ok, status_message = check_main_py_status()
    if status_ok:
        logger.info(f"✅ 시작 시 검사 통과: {status_message}")
    else:
        logger.error(f"❌ 시작 시 검사 실패: {status_message}")
    
    # [SB] Ollama 연결 상태 체크
    ollama_ok, ollama_message = check_ollama_connection()
    if ollama_ok:
        logger.info(f"✅ Ollama 연결 확인: {ollama_message}")
    else:
        logger.warning(f"⚠️ Ollama 연결 문제: {ollama_message}")
        
    # [SB] 개발 서버 실행 - 프로덕션에서는 gunicorn 등 사용
    app.run(host='0.0.0.0', port=5000, debug=True)