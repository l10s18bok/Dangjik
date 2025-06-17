# utils/mattermost.py
from mattermostdriver import Driver
from pathlib import Path
import os
import logging
from dotenv import load_dotenv
from datetime import datetime
import io

logger = logging.getLogger(__name__)

# .env 파일 로드
load_dotenv()

def _parse_mattermost_url(url):
    """
    Mattermost URL을 파싱하여 scheme, domain, port를 반환하는 헬퍼 함수
    
    Args:
        url (str): Mattermost 서버 URL
    
    Returns:
        tuple: (scheme, domain, port)
    """
    domain = url
    scheme = 'https'  # 기본 스키마는 https
    port = 443  # 기본 포트는 443
    
    # URL에서 scheme 추출 (https://, http:// 등)
    if '://' in domain:
        scheme, domain = domain.split('://', 1)
    
    # 포트 추출 - 안전하게 처리
    if ':' in domain:
        parts = domain.split(':', 1)
        if len(parts) == 2:
            domain = parts[0]
            # 추가 경로가 있는 경우 제거
            port_str = parts[1]
            if '/' in port_str:
                port_str = port_str.split('/', 1)[0]
                
            # 빈 문자열이 아닌 경우에만 정수 변환 시도
            if port_str.strip():
                try:
                    port = int(port_str)
                except ValueError:
                    print(f"[Mattermost] 포트 번호 변환 실패. 기본값 443 사용: {port_str}")
                    port = 443
    
    # 도메인에서 추가 경로 제거
    if '/' in domain:
        domain = domain.split('/', 1)[0]
    
    logger.debug(f"파싱된 URL 정보 - Scheme: {scheme}, Domain: {domain}, Port: {port}")
    
    return scheme, domain, port

def _get_mattermost_credentials():
    """
    Mattermost 연결에 필요한 환경 변수를 확인하고 반환하는 헬퍼 함수
    
    Returns:
        tuple: (url, login_id, password, 성공 여부)
    """
    url = os.getenv("MATTERMOST_URL")
    login_id = os.getenv("MATTERMOST_USERNAME")
    password = os.getenv("MATTERMOST_PASSWORD")
    
    # 환경 변수 확인
    if not all([url, login_id, password]):
        print("[Mattermost] 환경 변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
        return None, None, None, False
    
    return url, login_id, password, True

def _create_mattermost_driver(url, login_id, password):
    """
    Mattermost 드라이버를 생성하고 반환하는 헬퍼 함수
    
    Args:
        url (str): Mattermost 서버 URL
        login_id (str): 로그인 ID
        password (str): 비밀번호
    
    Returns:
        tuple: (driver, 성공 여부)
    """
    try:
        # URL 파싱
        scheme, domain, port = _parse_mattermost_url(url)
        
        # Mattermost 드라이버 초기화
        driver = Driver({
            'scheme': scheme,
            'url': domain,
            'port': port,
            'basepath': '/api/v4',
            'login_id': login_id,
            'password': password,
            'timeout': 60,
            'verify': False,
        })
        
        return driver, True
    except Exception as e:
        print(f"[Mattermost] 드라이버 생성 실패: {str(e)}")
        return None, False

def _send_excel_to_mattermost(excel_file, channel_id, message=None):
    """
    Mattermost의 특정 채널에 엑셀 파일을 전송하는 내부 함수
    
    Args:
        excel_file (str or BytesIO): 보낼 엑셀 파일 경로 또는 메모리 객체
        channel_id (str): 메시지를 보낼 채널 ID
        message (str, optional): 파일과 함께 보낼 메시지 (사용되지 않음)
        
    Returns:
        tuple: (성공 여부, 파일 이름)
    """
    # 환경 변수 가져오기
    url, login_id, password, success = _get_mattermost_credentials()
    if not success:
        return False, None
    
    # 파일이 문자열(경로)인지 메모리 객체인지 확인
    is_memory_file = isinstance(excel_file, io.BytesIO)
    
    # 파일 경로인 경우 파일 존재 여부 확인
    if not is_memory_file:
        excel_path = Path(excel_file)
        if not excel_path.exists():
            print(f"[Mattermost] 엑셀 파일을 찾을 수 없습니다: {excel_path}")
            return False, None
    elif not hasattr(excel_file, 'name'):
        # 메모리 객체지만 이름이 없는 경우 이름 설정
        excel_file.name = f"report_{datetime.now().strftime('%Y%m%d')}.xlsx"
    
    try:
        # Mattermost 드라이버 생성
        driver, success = _create_mattermost_driver(url, login_id, password)
        if not success:
            return False, None
        
        # 로그인
        driver.login()
        
        # 파일 업로드
        if is_memory_file:
            # 메모리 객체인 경우
            excel_file.seek(0)  # 파일 포인터를 시작으로 되돌림
            files = {
                'files': (getattr(excel_file, 'name', 'report.xlsx'), excel_file, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            }
            file_name = getattr(excel_file, 'name', 'report.xlsx')
        else:
            # 파일 경로인 경우
            files = {
                'files': (excel_path.name, open(excel_path, 'rb'), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            }
            file_name = excel_path.name
        
        file_upload = driver.files.upload_file(channel_id=channel_id, files=files)
        file_ids = [file_info['id'] for file_info in file_upload['file_infos']]
        
        # 현재 날짜를 가져와서 메시지 생성 (통일된 메시지 사용)
        today = datetime.now().strftime("%Y년 %m월 %d일")
        default_message = f"{today} 당직체크리스트입니다"
        post_data = {
            'channel_id': channel_id,
            'message': default_message,
            'file_ids': file_ids
        }
        
        driver.posts.create_post(post_data)
        
        # 로그아웃
        driver.logout()
        return True, file_name
        
    except Exception as e:
        print(f"[Mattermost] 오류 발생: {str(e)}")
        return False, None

def send_excel_to_self(excel_file):
    """
    자신에게 엑셀 파일을 보내는 함수
    
    Args:
        excel_file (str or BytesIO): 보낼 엑셀 파일 경로 또는 메모리 객체
        
    Returns:
        bool: 성공 여부
    """
    # 환경 변수 가져오기
    url, login_id, password, success = _get_mattermost_credentials()
    if not success:
        return False
    
    try:
        # Mattermost 드라이버 생성
        driver, success = _create_mattermost_driver(url, login_id, password)
        if not success:
            return False
        
        # 로그인
        driver.login()
        user_id = driver.users.get_user('me')['id']
        my_username = driver.users.get_user('me')['username']
        
        print(f"[Mattermost] {url}에 연결되었습니다. 사용자: {my_username}")
        
        # 자신과의 DM 채널 생성/조회
        dm_channel = driver.channels.create_direct_message_channel([user_id, user_id])
        channel_id = dm_channel['id']
        
        # 로그아웃
        driver.logout()
        
        # 공통 함수를 통해 파일 전송
        success, file_name = _send_excel_to_mattermost(excel_file, channel_id)
        
        if success:
            print(f"[Mattermost] 파일이 성공적으로 전송되었습니다: {file_name}")
            return True
        return False
        
    except Exception as e:
        print(f"[Mattermost] 오류 발생: {str(e)}")
        return False

def send_excel_to_team_channel(excel_file, team_key="INNOGS"):
    """
    특정 팀의 특정 채널에 엑셀 파일을 보내는 함수
    
    Args:
        excel_file (str or BytesIO): 보낼 엑셀 파일 경로 또는 메모리 객체
        team_key (str): 사용할 팀 키 ("INNOGS" 또는 "SECURITYNET")
        
    Returns:
        bool: 성공 여부
    """
    # 환경 변수 가져오기
    url, login_id, password, success = _get_mattermost_credentials()
    if not success:
        return False
    
    channel_name = os.getenv("MATTERMOST_CHANNEL")
    
    # 팀 이름 결정
    team_env_var = f"MATTERMOST_TEAM_{team_key.upper()}"
    team_name = os.getenv(team_env_var)
    
    # 환경 변수 확인
    if not all([team_name, channel_name]):
        print(f"[Mattermost] 환경 변수가 설정되지 않았습니다. .env 파일에서 {team_env_var} 또는 MATTERMOST_CHANNEL을 확인하세요.")
        return False
    
    try:
        # Mattermost 드라이버 생성
        driver, success = _create_mattermost_driver(url, login_id, password)
        if not success:
            return False
        
        # 로그인
        driver.login()
        user_id = driver.users.get_user('me')['id']
        
        print(f"[Mattermost] {url}에 연결되었습니다.")
        
        # 사용자의 팀 목록 가져오기
        my_teams = driver.teams.get_user_teams(user_id)
        
        # 팀 ID 찾기
        team_id = None
        found_team = None
        
        # 팀 이름 일치 확인 (정확히 일치)
        for team in my_teams:
            if team['name'].lower() == team_name.lower() or team['display_name'].lower() == team_name.lower():
                team_id = team['id']
                found_team = team
                print(f"[Mattermost] 팀을 찾았습니다: {team_name} (ID: {team_id})")
                break
        
        # 부분 일치로 다시 시도
        if not team_id:
            for team in my_teams:
                if team_name.lower() in team['name'].lower() or team_name.lower() in team['display_name'].lower():
                    team_id = team['id']
                    found_team = team
                    print(f"[Mattermost] 팀을 부분 일치로 찾았습니다: {team_name} -> {team['name']} (ID: {team_id})")
                    break
        
        # 팀이 여전히 없으면 첫 번째 팀 사용 (사용자가 최소 하나의 팀에 속해 있을 경우)
        if not team_id and len(my_teams) > 0:
            team_id = my_teams[0]['id']
            found_team = my_teams[0]
            print(f"[Mattermost] 팀을 찾을 수 없어 첫 번째 팀을 사용합니다: {found_team['name']} (ID: {team_id})")
        
        if not team_id:
            print(f"[Mattermost] 팀을 찾을 수 없습니다: {team_name}")
            driver.logout()
            return False
        
        # 채널 ID 찾기
        channels = driver.channels.get_channels_for_user(user_id, team_id)
        channel_id = None
        
        # 정확한 이름 또는 표시명으로 채널 찾기
        for channel in channels:
            if channel['name'].lower() == channel_name.lower():
                channel_id = channel['id']
                print(f"[Mattermost] 채널을 찾았습니다: {channel_name} (ID: {channel_id})")
                break
            if 'display_name' in channel and channel['display_name'].lower() == channel_name.lower():
                channel_id = channel['id']
                print(f"[Mattermost] 채널을 표시명으로 찾았습니다: {channel_name} (ID: {channel_id})")
                break
        
        # 부분 일치로 다시 시도
        if not channel_id:
            for channel in channels:
                if channel_name.lower() in channel['name'].lower():
                    channel_id = channel['id']
                    print(f"[Mattermost] 채널을 부분 일치로 찾았습니다: {channel_name} -> {channel['name']} (ID: {channel_id})")
                    break
                if 'display_name' in channel and channel_name.lower() in channel['display_name'].lower():
                    channel_id = channel['id']
                    print(f"[Mattermost] 채널을 표시명 부분 일치로 찾았습니다: {channel_name} -> {channel['display_name']} (ID: {channel_id})")
                    break
        
        if not channel_id:
            print(f"[Mattermost] 채널을 찾을 수 없습니다: {channel_name}")
            driver.logout()
            return False
        
        # 로그아웃
        driver.logout()
        
        # 공통 함수를 통해 파일 전송 (주석 처리)
        # success, file_name = _send_excel_to_mattermost(excel_file, channel_id)
        
        # 파일 전송 없이 팀과 채널을 찾았음을 성공으로 처리
        team_display = found_team.get('display_name', found_team['name']) if found_team else team_name
        print(f"[Mattermost] 팀 '{team_display}'의 채널 '{channel_name}'을 성공적으로 찾았습니다.")
        print(f"[Mattermost] 실제 파일 전송은 수행되지 않았습니다. (테스트 모드)")
        return True
        
    except Exception as e:
        print(f"[Mattermost] 오류 발생: {str(e)}")
        return False

def verify_mattermost_env():
    """
    Mattermost 환경 변수가 올바르게 설정되어 있는지 확인하는 함수
    
    Returns:
        dict: 환경 변수 상태를 담은 딕셔너리
    """
    # [SB] MATTERMOST_USERNAME, MATTERMOST_PASSWORD는 더 이상 필수가 아님 (웹에서 입력받음)
    required_vars = ["MATTERMOST_URL"]
    optional_vars = [
        "MATTERMOST_TEAM_INNOGS", 
        "MATTERMOST_TEAM_SECURITYNET", 
        "MATTERMOST_CHANNEL",
        # "MATTERMOST_USERNAME",  # [SB] 선택사항으로 이동
        # "MATTERMOST_PASSWORD"   # [SB] 선택사항으로 이동
    ]
    
    result = {
        "status": True,
        "missing_required": [],
        "missing_optional": [],
        "available": []
    }
    
    # 필수 환경 변수 확인
    for var in required_vars:
        if not os.getenv(var):
            result["status"] = False
            result["missing_required"].append(var)
        else:
            result["available"].append(var)
    
    # 선택적 환경 변수 확인
    for var in optional_vars:
        if not os.getenv(var):
            result["missing_optional"].append(var)
        else:
            result["available"].append(var)
    
    return result

def get_mattermost_username():
    """
    Mattermost에 로그인하여 현재 사용자의 이름을 가져오는 함수
    
    Returns:
        tuple: (성공 여부, 사용자 이름, 사용자 ID)
    """
    # 환경 변수 가져오기
    url, login_id, password, success = _get_mattermost_credentials()
    if not success:
        return False, None, None
    
    try:
        # Mattermost 드라이버 생성
        driver, success = _create_mattermost_driver(url, login_id, password)
        if not success:
            return False, None, None
        
        # 로그인
        driver.login()
        
        # 사용자 정보 가져오기
        user = driver.users.get_user('me')
        user_id = user['id']
        username = user.get('username', '')
        
        # 추가 정보 가져오기 (별명, 실명 등)
        nickname = user.get('nickname', '')
        first_name = user.get('first_name', '')
        last_name = user.get('last_name', '')
        
        # 로그아웃
        driver.logout()
        
        # 표시할 이름 결정 (우선순위: 별명 > 실명 > 사용자명)
        display_name = username
        if first_name or last_name:
            display_name = f"{first_name} {last_name}".strip()
        if nickname:
            display_name = nickname
        
        print(f"[Mattermost] 사용자 이름을 가져왔습니다: {display_name} (ID: {user_id})")
        return True, display_name, user_id
        
    except Exception as e:
        print(f"[Mattermost] 오류 발생: {str(e)}")
        return False, None, None 