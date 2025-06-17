#!/usr/bin/env python
# -*- coding: utf-8 -*-

from mattermostdriver import Driver
import os
from dotenv import load_dotenv
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# .env 파일 로드
load_dotenv()

def test_find_team_and_channel():
    """
    Mattermost의 팀과 채널을 찾는 테스트 함수
    
    팀을 찾을 수 없는 문제를 디버깅하기 위한 테스트
    """
    # 환경 변수에서 Mattermost 설정 로드
    url = os.getenv("MATTERMOST_URL")
    login_id = os.getenv("MATTERMOST_USERNAME")
    password = os.getenv("MATTERMOST_PASSWORD")
    team_key = "INNOGS"
    team_env_var = f"MATTERMOST_TEAM_{team_key}"
    team_name = os.getenv(team_env_var)
    channel_name = os.getenv("MATTERMOST_CHANNEL")
    
    # 환경 변수 값 확인 출력
    print(f"[테스트] URL: {url}")
    print(f"[테스트] 사용자명: {login_id}")
    print(f"[테스트] 팀 환경변수: {team_env_var}")
    print(f"[테스트] 팀명: {team_name}")
    print(f"[테스트] 채널명: {channel_name}")
    
    # 환경 변수 확인
    if not all([url, login_id, password, team_name, channel_name]):
        print(f"[테스트] 환경 변수가 설정되지 않았습니다")
        return False
    
    try:
        # Mattermost 연결 설정
        domain = url
        scheme = 'https'
        port = 443  # https의 기본 포트
        
        # URL에서 scheme이 있으면 제거
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
                        print(f"[테스트] 포트 번호 변환 실패. 기본값 443 사용: {port_str}")
                        port = 443
        
        # 도메인에서 추가 경로 제거
        if '/' in domain:
            domain = domain.split('/', 1)[0]
        
        print(f"[테스트] 파싱된 URL 정보 - Scheme: {scheme}, Domain: {domain}, Port: {port}")
        
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
        
        # 로그인
        driver.login()
        user_id = driver.users.get_user('me')['id']
        my_username = driver.users.get_user('me')['username']
        
        print(f"[테스트] {url}에 연결되었습니다. 사용자: {my_username} (ID: {user_id})")
        
        # 모든 팀 정보 출력
        print("\n[테스트] 모든 팀 목록:")
        teams = driver.teams.get_teams()
        print(f"[테스트] 총 {len(teams)}개의 팀이 있습니다.")
        if len(teams) == 0:
            print("[테스트] 접근할 수 있는 팀이 없습니다. 계정 권한을 확인하세요.")
        
        for i, team in enumerate(teams):
            print(f"  {i+1}. ID: {team['id']}")
            print(f"     Name: {team['name']}")
            print(f"     Display Name: {team['display_name']}")
            print(f"     Type: {team.get('type', 'N/A')}")
        
        # 내가 속한 팀 목록 출력 (추가)
        print("\n[테스트] 내가 속한 팀 목록:")
        my_teams = driver.teams.get_user_teams(user_id)
        print(f"[테스트] 내가 속한 팀은 총 {len(my_teams)}개입니다.")
        
        for i, team in enumerate(my_teams):
            print(f"  {i+1}. ID: {team['id']}")
            print(f"     Name: {team['name']}")
            print(f"     Display Name: {team['display_name']}")
            print(f"     Type: {team.get('type', 'N/A')}")
            
            # 환경변수와 일치하는지 확인
            if team['name'].lower() == team_name.lower() or team['display_name'].lower() == team_name.lower():
                print(f"  -> 환경변수 {team_env_var}의 값({team_name})과 일치!")
        
        print(f"\n[테스트] 팀 찾기: {team_name}")
        print(f"[테스트] 팀 환경변수 '{team_env_var}'에서 '{team_name}' 값을 가져왔습니다.")
        
        # 내가 속한 팀에서 먼저 찾기
        for team in my_teams:
            if team['name'].lower() == team_name.lower() or team['display_name'].lower() == team_name.lower():
                team_id = team['id']
                print(f"[테스트] ✅ 팀을 찾았습니다: {team_name} (ID: {team_id})")
                print(f"[테스트] 매치된 팀 정보 - 이름: {team['name']}, 표시명: {team['display_name']}")
                found_team = team
                break
        
        # 모든 팀에서 찾기
        if not team_id:
            for team in teams:
                if team['name'].lower() == team_name.lower() or team['display_name'].lower() == team_name.lower():
                    team_id = team['id']
                    print(f"[테스트] ✅ 팀을 찾았습니다: {team_name} (ID: {team_id})")
                    print(f"[테스트] 매치된 팀 정보 - 이름: {team['name']}, 표시명: {team['display_name']}")
                    found_team = team
                    break
            
        # 부분 일치로 재시도
        if not team_id:
            # 내가 속한 팀에서 부분 일치 시도
            for team in my_teams:
                if team_name.lower() in team['name'].lower() or team_name.lower() in team['display_name'].lower():
                    team_id = team['id']
                    print(f"[테스트] ✅ 팀을 부분 일치로 찾았습니다: {team_name} -> {team['name']} (ID: {team_id})")
                    print(f"[테스트] 매치된 팀 정보 - 이름: {team['name']}, 표시명: {team['display_name']}")
                    found_team = team
                    break
            
            # 모든 팀에서 부분 일치 시도
            if not team_id:
                for team in teams:
                    if team_name.lower() in team['name'].lower() or team_name.lower() in team['display_name'].lower():
                        team_id = team['id']
                        print(f"[테스트] ✅ 팀을 부분 일치로 찾았습니다: {team_name} -> {team['name']} (ID: {team_id})")
                        print(f"[테스트] 매치된 팀 정보 - 이름: {team['name']}, 표시명: {team['display_name']}")
                        found_team = team
                        break
            
            # 매치 실패 시, 첫 번째 팀 사용
            if not team_id and len(my_teams) > 0:
                team_id = my_teams[0]['id']
                found_team = my_teams[0]
                print(f"[테스트] ⚠️ 팀을 찾을 수 없어 첫 번째 팀을 사용합니다: {found_team['name']} (ID: {team_id})")
            
            if not team_id:
                print(f"[테스트] ❌ 팀을 찾을 수 없습니다: {team_name}")
                # 팀을 찾을 수 없으면 모든 팀 정보 다시 출력
                print("\n[테스트] 접근 가능한 모든 팀 목록:")
                for i, team in enumerate(teams):
                    print(f"  {i+1}. Name: {team['name']}, Display Name: {team['display_name']}")
                driver.logout()
                return False
        
        # 채널 ID 찾기
        print(f"\n[테스트] 채널 찾기: {channel_name}")
        channels = driver.channels.get_channels_for_user(user_id, team_id)
        
        # 모든 채널 정보 출력
        print("[테스트] 모든 채널 목록:")
        for i, channel in enumerate(channels):
            print(f"  {i+1}. ID: {channel['id']}")
            print(f"     Name: {channel['name']}")
            if 'display_name' in channel:
                print(f"     Display Name: {channel['display_name']}")
            print(f"     Type: {channel.get('type', 'N/A')}")
        
        channel_id = None
        for channel in channels:
            if channel['name'].lower() == channel_name.lower():
                channel_id = channel['id']
                print(f"[테스트] ✅ 채널을 찾았습니다: {channel_name} (ID: {channel_id})")
                break
            if 'display_name' in channel and channel['display_name'].lower() == channel_name.lower():
                channel_id = channel['id']
                print(f"[테스트] ✅ 채널을 display_name으로 찾았습니다: {channel_name} (ID: {channel_id})")
                break
        
        if not channel_id:
            # 부분 일치로 재시도
            for channel in channels:
                if channel_name.lower() in channel['name'].lower():
                    channel_id = channel['id']
                    print(f"[테스트] ✅ 채널을 부분 일치로 찾았습니다: {channel_name} -> {channel['name']} (ID: {channel_id})")
                    break
                if 'display_name' in channel and channel_name.lower() in channel['display_name'].lower():
                    channel_id = channel['id']
                    print(f"[테스트] ✅ 채널을 display_name 부분 일치로 찾았습니다: {channel_name} -> {channel['display_name']} (ID: {channel_id})")
                    break
                
            if not channel_id:
                print(f"[테스트] ❌ 채널을 찾을 수 없습니다: {channel_name}")
                print("\n[테스트] 접근 가능한 모든 채널 목록:")
                for i, channel in enumerate(channels):
                    name = channel['name']
                    display_name = channel.get('display_name', 'N/A')
                    print(f"  {i+1}. Name: {name}, Display Name: {display_name}")
                driver.logout()
                return False
        
        print("\n[테스트] ✅ 팀과 채널 모두 찾았습니다")
        print(f"  - 팀: {team_name} (ID: {team_id})")
        print(f"  - 채널: {channel_name} (ID: {channel_id})")
        
        # 해당 채널의 상세 정보 조회
        try:
            channel_info = driver.channels.get_channel(channel_id)
            print("\n[테스트] 채널 상세 정보:")
            for key, value in channel_info.items():
                print(f"  {key}: {value}")
        except Exception as e:
            print(f"[테스트] 채널 상세 정보 조회 실패: {e}")
        
        # 로그아웃
        driver.logout()
        return True
        
    except Exception as e:
        print(f"[테스트] 오류 발생: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Mattermost 팀 및 채널 검색 테스트 시작")
    print("=" * 50)
    
    result = test_find_team_and_channel()
    
    print("\n" + "=" * 50)
    if result:
        print("테스트 성공: 팀과 채널을 모두 찾았습니다!")
    else:
        print("테스트 실패: 팀 또는 채널을 찾을 수 없습니다.")
    print("=" * 50) 