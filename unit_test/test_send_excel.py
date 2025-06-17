#!/usr/bin/env python
# -*- coding: utf-8 -*-

from utils.mattermost import send_excel_to_self, verify_mattermost_env
import sys
import os

def main():
    """
    Mattermost 엑셀 전송 테스트 함수
    """
    # 환경 변수 확인
    env_status = verify_mattermost_env()
    
    if not env_status["status"]:
        print(f"[테스트] 필수 환경 변수가 설정되지 않았습니다: {', '.join(env_status['missing_required'])}")
        return False
    
    print(f"[테스트] 환경 변수가 올바르게 설정되었습니다.")
    print(f"  - 사용 가능한 환경 변수: {', '.join(env_status['available'])}")
    
    if env_status["missing_optional"]:
        print(f"  - 설정되지 않은 선택적 환경 변수: {', '.join(env_status['missing_optional'])}")
    
    # 테스트 파일 경로
    excel_path = "test_file.xlsx"
    
    if not os.path.exists(excel_path):
        print(f"[테스트] 테스트 파일을 찾을 수 없습니다: {excel_path}")
        return False
    
    # 자신에게 전송 테스트
    print("\n[테스트] 자신에게 엑셀 파일 전송 테스트 시작...")
    success = send_excel_to_self(excel_path)
    
    if success:
        print("[테스트] ✅ 자신에게 엑셀 파일 전송 성공!")
    else:
        print("[테스트] ❌ 자신에게 엑셀 파일 전송 실패!")
    
    return True

if __name__ == "__main__":
    print("Mattermost 엑셀 전송 테스트 시작...")
    success = main()
    
    if success:
        print("\n✅ 테스트 완료!")
        sys.exit(0)
    else:
        print("\n❌ 테스트 실패!")
        sys.exit(1) 