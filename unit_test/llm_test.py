# xlsx_test.py
import asyncio
import json
import os
import sys
import importlib
import io
from pathlib import Path  # [SB] Path import 이미 있음 - 확인됨
from datetime import datetime
from dotenv import load_dotenv
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

# [SB] 모듈 캐시 강제 제거
if 'utils.xlsx' in sys.modules:
    del sys.modules['utils.xlsx']
if 'utils.llm' in sys.modules:
    del sys.modules['utils.llm']

from utils.xlsx import create_dashboard_excel
from utils.llm import analyze_with_ollama

# [SB] 환경 변수 로드
load_dotenv()

async def test_xlsx_generation():
    """
    [SB] xlsx 출력을 테스트하기 위한 함수 (main.py와 동일한 방식 + 스크린샷)
    """
    print("[SB] xlsx 테스트 시작...")
    print("[SB] 모듈 캐시 제거 완료")
    
    # [SB] utils.xlsx 모듈 강제 리로드
    import utils.xlsx
    importlib.reload(utils.xlsx)
    print("[SB] utils.xlsx 모듈 리로드 완료")
    
    # [SB] logs 폴더가 존재하는지 확인하고 없으면 생성
    logs_dir = Path("logs")
    if not logs_dir.exists():
        logs_dir.mkdir(exist_ok=True)
        print(f"[SB] logs 폴더 생성됨: {logs_dir.absolute()}")
    else:
        print(f"[SB] logs 폴더 이미 존재: {logs_dir.absolute()}")
    
    # [SB] 임의로 대시보드 추출 결과 생성 (의도적으로 일부 비정상 설정)
    mock_extracted_data = {
        "로그인상태": "정상",
        "whois_usd": "199.99 USD",
        "gabia_krw": "000,400 KRW",
        "스케줄러상태": "적용됨",
        "1:1문의": "0 개",
        "이메일문의": "0 개",
        "에러리포트": "0 개",
        "장비미보고": "0 개",
        "Region활성": "2 개",
        "DB_Sync": {
            "일시중지": "0 개",
            "오류": "0 개"
        },
        "FrontEnd": {
            "상태": "정상",
            "도메인 검색": "비정상"  # [SB] 의도적으로 비정상 (링크 체크 트리거용)
        },
        "운영중인서비스": {
            "parking": "정상",
            "url": "비정상",  # [SB] 의도적으로 비정상 (링크 체크 트리거용)
            "furl": "정상"
        }
    }
    
    print("[SB] 모의 추출 데이터:")
    print(json.dumps(mock_extracted_data, indent=2, ensure_ascii=False))
    
    # [SB] LLM 분석 수행
    print("\n[SB] LLM 분석 시작...")
    llm_answer = analyze_with_ollama(mock_extracted_data)
    
    try:
        # [SB] LLM 결과를 JSON으로 파싱
        llm_json = json.loads(llm_answer)
        print("\n[SB] LLM 분석 결과:")
        print(json.dumps(llm_json, indent=2, ensure_ascii=False))
        
        # [SB] 디버깅: 기존 링크 키들 제거 (깨끗한 상태로 시작)
        print("\n[SB] 기존 링크 키들 제거...")
        if "link" in llm_json.get("FrontEnd", {}):
            del llm_json["FrontEnd"]["link"]
            print("[SB] FrontEnd.link 제거됨")
        
        운영서비스 = llm_json.get("운영중인서비스", {})
        for key in ["parking_link", "url_link", "furl_link"]:
            if key in 운영서비스:
                del 운영서비스[key]
                print(f"[SB] 운영중인서비스.{key} 제거됨")
        
        print("\n[SB] 링크 키 제거 후 LLM 데이터:")
        print(json.dumps(llm_json, indent=2, ensure_ascii=False))
        
        # [SB] main.py와 동일한 크롤러 설정
        browser_config = BrowserConfig(
            browser_type="chromium",
            headless=True,
            verbose=True,
            java_script_enabled=True,
            viewport_width=1920,
            viewport_height=1080
        )
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            delay_before_return_html=3.0,
            wait_until="networkidle"
        )
        
        # [SB] 대시보드 스크린샷 메모리 저장용 (main.py와 동일)
        dashboard_screenshot_data = None
        
        # [SB] 로그인 설정 (main.py와 동일)
        login_config = {
            "d_url": os.getenv("DASHBOARD_URL"),
            "username": os.getenv("DASHBOARD_USERNAME"),
            "password": os.getenv("DASHBOARD_PASSWORD"),
            "frontend": os.getenv("FRONTEND_LINK"),
            "parking": os.getenv("PARKING_LINK"),
            "url": os.getenv("URL_LINK"),
            "furl": os.getenv("FURL_LINK"),
        }
        
        # [SB] 로그인 상태 추적 (main.py와 동일)
        state = {"login_success": False, "dashboard_url": None, "login_processed": False}
        
        async def after_goto_hook(page, context, **kwargs):
            nonlocal dashboard_screenshot_data
            
            if state["login_processed"]:
                return
            if "hydra2.uxcloud.net" in page.url and "/page/" not in page.url:
                try:
                    state["login_processed"] = True
                    print("[SB] 로그인 페이지에서 로그인 시도 중...")
                    await page.wait_for_selector('#htxtId', timeout=10000)
                    await page.fill('#htxtId', login_config["username"])
                    await page.fill('#htxtPwd', login_config["password"])
                    navigation_promise = page.wait_for_url("**/page/*/main", timeout=15000)
                    await page.click('.btn_login')
                    await navigation_promise
                    state["dashboard_url"] = page.url
                    state["login_success"] = True
                    await page.wait_for_load_state('networkidle', timeout=10000)
                    await page.wait_for_timeout(1000)
                    
                    # [SB] 로그인 성공 후 대시보드에서 스크린샷 캡처
                    print("[SB] 로그인 성공! 대시보드 스크린샷 캡처 중...")
                    screenshot_bytes = await page.screenshot(type='png', full_page=True)
                    
                    # [SB] 원본 이미지를 메모리 버퍼에 직접 저장
                    dashboard_screenshot_data = io.BytesIO(screenshot_bytes)
                    dashboard_screenshot_data.seek(0)  # 포인터를 시작으로 리셋
                    
                    print(f"[SB] 대시보드 스크린샷 캡처 완료 (원본 크기, {len(screenshot_bytes):,} bytes)")
                    
                except Exception as e:
                    print(f"[SB] 로그인 오류: {e}")
                    state["login_success"] = False
            else:
                if "/page/" in page.url and "main" in page.url:
                    state["dashboard_url"] = page.url
                    state["login_success"] = True
                    state["login_processed"] = True
                    try:
                        await page.wait_for_load_state('networkidle', timeout=10000)
                        await page.wait_for_timeout(1000)
                        
                        # [SB] 이미 로그인된 경우 대시보드에서 스크린샷 캡처
                        print("[SB] 이미 로그인됨! 대시보드 스크린샷 캡처 중...")
                        screenshot_bytes = await page.screenshot(type='png', full_page=True)
                        
                        # [SB] 원본 이미지를 메모리 버퍼에 직접 저장
                        dashboard_screenshot_data = io.BytesIO(screenshot_bytes)
                        dashboard_screenshot_data.seek(0)  # 포인터를 시작으로 리셋
                        
                        print(f"[SB] 대시보드 스크린샷 캡처 완료 (원본 크기, {len(screenshot_bytes):,} bytes)")
                        
                    except Exception as e:
                        print(f"[SB] 페이지 로딩 오류: {e}")
        
        # [SB] main.py와 동일한 크롤링 및 링크 체크
        async with AsyncWebCrawler(config=browser_config) as crawler:
            print("\n[SB] 대시보드 로그인 및 스크린샷 캡처 시작...")
            
            # [SB] 로그인 훅 설정 (main.py와 동일)
            crawler.crawler_strategy.set_hook("after_goto", after_goto_hook)
            
            # [SB] 대시보드 접속 및 로그인
            dashboard_result = await crawler.arun(login_config["d_url"], config=run_config)
            
            if not state["login_success"] or not state["dashboard_url"]:
                print("[SB] 로그인 또는 대시보드 진입 실패 - 스크린샷 없이 진행")
                dashboard_screenshot_data = None
            else:
                print(f"[SB] 대시보드 로그인 성공: {state['dashboard_url']}")
            
            print("\n[SB] 링크 체크 로직 수행...")
            
            # [SB] FrontEnd 링크 체크 (main.py와 동일)
            frontend = llm_json.get("FrontEnd", {})
            print(f"\n[SB] FrontEnd 조건 체크:")
            print(f"    상태: {frontend.get('상태')} (예와 같은가? {frontend.get('상태') == '예'})")
            print(f"    도메인 검색: {frontend.get('도메인 검색')} (예와 같은가? {frontend.get('도메인 검색') == '예'})")
            
            condition1 = frontend.get("상태") != "예"
            condition2 = frontend.get("도메인 검색") != "예"
            should_check = condition1 or condition2
            print(f"    조건1 (상태 != 예): {condition1}")
            print(f"    조건2 (도메인검색 != 예): {condition2}")
            print(f"    최종 조건 (OR): {should_check}")
            
            if should_check:
                print(f"[SB] FrontEnd 링크 체크 실행: {login_config['frontend']}")
                front_success = await crawler.arun(login_config["frontend"], config=run_config)
                f_status = "비정상"
                if front_success.status_code == 200:
                    f_status = "정상"
                print(f"[SB] FrontEnd 크롤링 결과: Status Code {front_success.status_code} → {f_status}")
                
                llm_json["FrontEnd"]["link"] = f_status  # [SB] 쉼표 없음 (튜플 방지)
                print(f"[SB] FrontEnd link 설정됨: {f_status}")
            else:
                print("[SB] FrontEnd 링크 체크 건너뜀")
            
            # [SB] 운영중인서비스 링크 체크 (main.py와 동일)
            using_services = llm_json.get("운영중인서비스", {})
            print(f"\n[SB] 운영중인서비스 조건 체크:")
            print(f"    parking: {using_services.get('parking')} (예와 같은가? {using_services.get('parking') == '예'})")
            print(f"    url: {using_services.get('url')} (예와 같은가? {using_services.get('url') == '예'})")
            print(f"    furl: {using_services.get('furl')} (예와 같은가? {using_services.get('furl') == '예'})")
            
            # [SB] Parking 체크
            parking_condition = using_services.get("parking") != "예"
            print(f"    Parking 조건 (parking != 예): {parking_condition}")
            if parking_condition:
                print(f"[SB] Parking 링크 체크 실행: {login_config['parking']}")
                parking_success = await crawler.arun(login_config["parking"], config=run_config)
                p_status = "비정상"
                if parking_success.status_code == 200:
                    p_status = "정상"
                print(f"[SB] Parking 크롤링 결과: Status Code {parking_success.status_code} → {p_status}")
                llm_json["운영중인서비스"]["parking_link"] = p_status
                print(f"[SB] Parking link 설정됨: {p_status}")
            else:
                print("[SB] Parking 링크 체크 건너뜀")

            # [SB] URL 체크
            url_condition = using_services.get("url") != "예"
            print(f"    URL 조건 (url != 예): {url_condition}")
            if url_condition:
                print(f"[SB] URL 링크 체크 실행: {login_config['url']}")
                url_success = await crawler.arun(login_config["url"], config=run_config)
                u_status = "비정상"
                if url_success.status_code == 200:
                    u_status = "정상"
                print(f"[SB] URL 크롤링 결과: Status Code {url_success.status_code} → {u_status}")
                llm_json["운영중인서비스"]["url_link"] = u_status
                print(f"[SB] URL link 설정됨: {u_status}")
            else:
                print("[SB] URL 링크 체크 건너뜀")

            # [SB] FURL 체크
            furl_condition = using_services.get("furl") != "예"
            print(f"    FURL 조건 (furl != 예): {furl_condition}")
            if furl_condition:
                print(f"[SB] FURL 링크 체크 실행: {login_config['furl']}")
                furl_success = await crawler.arun(login_config["furl"], config=run_config)
                f_status = "비정상"
                if furl_success.status_code == 200:
                    f_status = "정상"
                print(f"[SB] FURL 크롤링 결과: Status Code {furl_success.status_code} → {f_status}")
                llm_json["운영중인서비스"]["furl_link"] = f_status
                print(f"[SB] FURL link 설정됨: {f_status}")
            else:
                print("[SB] FURL 링크 체크 건너뜀")
            
            print("\n[SB] 링크 체크 후 최종 LLM 데이터:")
            print(json.dumps(llm_json, indent=2, ensure_ascii=False))
        
        # [SB] 각 링크 값 디버깅 출력
        print(f"\n[SB] FrontEnd link 값: {llm_json.get('FrontEnd', {}).get('link')}")
        print(f"[SB] FrontEnd link 타입: {type(llm_json.get('FrontEnd', {}).get('link'))}")
        print(f"[SB] parking_link 값: {llm_json.get('운영중인서비스', {}).get('parking_link')}")
        print(f"[SB] url_link 값: {llm_json.get('운영중인서비스', {}).get('url_link')}")
        print(f"[SB] furl_link 값: {llm_json.get('운영중인서비스', {}).get('furl_link')}")
        
        # [SB] 링크 키 존재 여부 확인
        print(f"\n[SB] 'link' 키 존재 여부: {'link' in llm_json.get('FrontEnd', {})}")
        print(f"[SB] 'parking_link' 키 존재 여부: {'parking_link' in llm_json.get('운영중인서비스', {})}")
        print(f"[SB] 'url_link' 키 존재 여부: {'url_link' in llm_json.get('운영중인서비스', {})}")
        print(f"[SB] 'furl_link' 키 존재 여부: {'furl_link' in llm_json.get('운영중인서비스', {})}")
        
        # [SB] 스크린샷 데이터 확인
        if dashboard_screenshot_data:
            print(f"[SB] 대시보드 스크린샷 데이터 크기: {dashboard_screenshot_data.getbuffer().nbytes:,} bytes")
        else:
            print("[SB] 대시보드 스크린샷 없음")
        
        # [SB] Excel 파일 생성 (logs 폴더에 저장)
        print("\n[SB] Excel 파일 생성 중...")
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        # [SB] 캐시 방지를 위해 고유한 파일명 생성
        import random
        unique_id = random.randint(1000, 9999)
        unique_timestamp = f"{timestamp}_{unique_id}"
        
        print(f"[SB] 고유 타임스탬프: {unique_timestamp}")
        
        # [SB] 디스크에 저장 (스크린샷 포함 - main.py와 동일)
        excel_path = create_dashboard_excel(
            llm_json, 
            timestamp=unique_timestamp, 
            in_memory=False,  # [SB] logs 폴더에 파일로 저장
            username="테스트스크린샷포함",
            dashboard_screenshot=dashboard_screenshot_data  # [SB] 스크린샷 데이터 전달
        )
        
        print(f"[SB] Excel 파일이 성공적으로 생성되었습니다: {excel_path}")
        print(f"[SB] 파일 경로: {excel_path.absolute()}")
        
        # [SB] 파일 존재 여부 확인
        if excel_path.exists():
            file_size = excel_path.stat().st_size
            print(f"[SB] 파일 크기: {file_size:,} bytes")
            print("[SB] 테스트 성공! ✅")
            
            # [SB] Excel 구성 확인
            print("\n[SB] Excel 파일 구성:")
            print("  - 시트 1: 대시보드 체크리스트 (로그인 항목에 축소된 스크린샷)")
            print("  - 시트 2: 원본 스크린샷 (대시보드 원본 크기 스크린샷)")
        else:
            print("[SB] 파일이 생성되지 않았습니다. ❌")
            
    except Exception as e:
        print(f"[SB] 오류 발생: {e}")
        import traceback
        traceback.print_exc()  # [SB] 상세한 오류 정보 출력
        print("[SB] 원본 LLM 응답:")
        print(llm_answer)

if __name__ == "__main__":
    print("[SB] xlsx 테스트 스크립트 실행 (스크린샷 포함)")
    print("="*60)
    
    # [SB] async 함수 실행
    asyncio.run(test_xlsx_generation())
    
    print("\n" + "="*60)
    print("[SB] 테스트 완료!")
    print("[SB] logs 폴더에서 생성된 Excel 파일을 확인해보세요.")
    print("[SB] 파일에는 대시보드 스크린샷이 포함되어 있습니다.")