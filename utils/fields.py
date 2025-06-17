# [SB] utils/fields.py - Hydra 데시보드 필드 추출 전용
import json
from bs4 import BeautifulSoup

def extract_fields(html, login_status=None):
    """[SB] HTML에서 필요한 필드들을 추출하는 함수"""
    soup = BeautifulSoup(html, "html.parser")
    result = {}

    # [SB] 1. 로그인 상태
    if login_status is not None:
        result["로그인상태"] = login_status

    # [SB] 2. Whois, Gabia 예치금 정보 추출
    dashboard = soup.select_one("#dashboard")
    if dashboard:
        for box in dashboard.select(".box"):
            title = box.select_one(".title")
            if title and "예치금" in title.get_text(strip=True):
                for item in box.select(".item"):
                    value = item.select_one(".value")
                    if not value:
                        continue
                    value_text = value.get_text(strip=True)
                    if "USD" in value_text:
                        result["whois_usd"] = value_text
                    elif "KRW" in value_text:
                        result["gabia_krw"] = value_text

    # [SB] 3. 기타 박스들 처리
    answer_ready_count = 0
    db_sync = {}
    frontend = {"상태": "", "도메인 검색": ""}
    services = {}
    
    # [SB] box 요소들을 한 번만 순회하며 모든 정보 추출
    for box in soup.select(".box"):
        title = box.select_one(".title")
        title_text = title.get_text(strip=True) if title else ""
        
        # [SB] FrontEnd 존재 여부 미리 확인
        has_frontend = any(
            (item.select_one(".header") and "FrontEnd" in item.select_one(".header").get_text(strip=True))
            for item in box.select(".item")
        )
        
        for item in box.select(".item"):
            header = item.select_one(".header")
            value = item.select_one(".value")
            if not header or not value:
                continue
                
            header_text = header.get_text(strip=True)
            value_text = value.get_text(strip=True)
            
            # [SB] 조건 검사 최적화: 서비스 및 시스템 상태 확인
            if header_text == "답변 준비중":
                if answer_ready_count == 0:
                    result["1:1문의"] = value_text
                elif answer_ready_count == 1:
                    result["이메일문의"] = value_text
                answer_ready_count += 1
            elif header_text == "신규":
                result["에러리포트"] = value_text
            elif header_text == "활성":
                result["Region활성"] = value_text
            elif "스케줄러" in title_text and "적용여부" in header_text:
                result["스케줄러상태"] = value_text
            elif "미보고" in header_text:
                result["장비미보고"] = value_text
            elif "일시중지" in header_text:
                db_sync["일시중지"] = value_text
            elif "오류" in header_text:
                db_sync["오류"] = value_text
            elif "FrontEnd" in header_text and "상태" in header_text:
                result["상태"] = value_text
                
            # [SB] 서비스 관련 항목 처리
            if any(key in header_text.lower() for key in ["parking", "furl", "url"]):
                service_key = header_text.lower()
                if service_key == "url":
                    services["url"] = value_text
                elif "parking" in service_key:
                    services["parking"] = value_text
                elif "furl" in service_key:
                    services["furl"] = value_text
                    
            # [SB] FrontEnd 상태 처리
            if has_frontend:
                if header_text == "상태":
                    frontend["상태"] = value_text
                elif header_text == "도메인 검색":
                    frontend["도메인 검색"] = value_text
    
    # [SB] 결과 병합
    if db_sync:
        result["DB_Sync"] = db_sync
    if frontend["상태"] or frontend["도메인 검색"]:
        result["FrontEnd"] = frontend
    if services:
        result["운영중인서비스"] = services

    return result
