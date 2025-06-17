# xlsx_test.py - Hook에서 직접 page.screenshot() 사용 방식
import asyncio
import json
import os
import sys
import importlib
import io
from pathlib import Path
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
    [SB] xlsx 출력을 테스트하기 위한 함수 (Hook에서 직접 page.screenshot() 사용)
    """
    print("[SB] xlsx 테스트 시작 (Hook에서 직접 스크린샷 방식)...")
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
        "gabia_krw": "199,999 KRW",
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
            "도메인 검색": "정상"  # [SB] 의도적으로 비정상 (링크 체크 트리거용)
        },
        "운영중인서비스": {
            "parking": "정상",
            "url": "정상",  # [SB] 의도적으로 비정상 (링크 체크 트리거용)
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
        
        # [SB] 최적화된 크롤러 설정 (작은 해상도로 메모리 절약)
        browser_config = BrowserConfig(
            browser_type="chromium",
            headless=True,
            verbose=False,  # [SB] 로그 줄이기
            java_script_enabled=True,
            # [SB] 해상도를 작게 설정하여 스크린샷 크기 자체를 줄임
            viewport_width=1024,   # [SB] 1920 → 1024로 축소
            viewport_height=768,   # [SB] 1080 → 768로 축소
        )
        
        # [SB] *** 수정사항 3: screenshot=False로 설정 (Hook에서 직접 처리) ***
        dashboard_run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            delay_before_return_html=2.0,
            wait_until="networkidle",
            screenshot=False,  # [SB] Hook에서 직접 처리하므로 False
            exclude_external_images=True,  # [SB] 외부 이미지 제외로 속도 향상
        )
        
        # [SB] 링크 체크용 런 설정 (screenshot 없음)
        link_check_run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            delay_before_return_html=1.0,  # [SB] 링크 체크는 더 빠르게
            wait_until="networkidle",
            screenshot=False,  # [SB] 링크 체크시엔 스크린샷 불필요
        )
        
        # [SB] 대시보드 스크린샷 메모리 저장용
        dashboard_screenshot_data = None
        
        # [SB] 로그인 설정
        login_config = {
            "d_url": os.getenv("DASHBOARD_URL"),
            "username": os.getenv("DASHBOARD_USERNAME"),
            "password": os.getenv("DASHBOARD_PASSWORD"),
            "frontend": os.getenv("FRONTEND_LINK"),
            "parking": os.getenv("PARKING_LINK"),
            "url": os.getenv("URL_LINK"),
            "furl": os.getenv("FURL_LINK"),
        }
        
        # [SB] 로그인 상태 추적
        state = {"login_success": False, "dashboard_url": None, "login_processed": False}
        
        async def after_goto_hook(page, context, **kwargs):
            """[SB] *** 수정사항 3: Hook에서 직접 page.screenshot() 사용 ***"""
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
                    
                    # [SB] *** Hook에서 직접 스크린샷 캡처 ***
                    print("[SB] 로그인 성공! Hook에서 직접 스크린샷 캡처 중...")
                    screenshot_bytes = await page.screenshot(
                        type='png', 
                        full_page=True  # [SB] 전체 페이지 캡처
                    )
                    
                    # [SB] 메모리 버퍼에 저장
                    dashboard_screenshot_data = io.BytesIO(screenshot_bytes)
                    dashboard_screenshot_data.seek(0)
                    
                    print(f"[SB] Hook 스크린샷 캡처 완료 (크기: {len(screenshot_bytes):,} bytes)")
                    
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
                        
                        # [SB] *** Hook에서 직접 스크린샷 캡처 (이미 로그인된 경우) ***
                        print("[SB] 이미 로그인됨! Hook에서 직접 스크린샷 캡처 중...")
                        screenshot_bytes = await page.screenshot(
                            type='png', 
                            full_page=True
                        )
                        
                        # [SB] 메모리 버퍼에 저장
                        dashboard_screenshot_data = io.BytesIO(screenshot_bytes)
                        dashboard_screenshot_data.seek(0)
                        
                        print(f"[SB] Hook 스크린샷 캡처 완료 (크기: {len(screenshot_bytes):,} bytes)")
                        
                    except Exception as e:
                        print(f"[SB] 페이지 로딩 오류: {e}")
        
        # [SB] 크롤링 및 링크 체크
        async with AsyncWebCrawler(config=browser_config) as crawler:
            print("\n[SB] 대시보드 로그인 및 Hook 스크린샷 캡처 시작...")
            
            # [SB] 로그인 훅 설정
            crawler.crawler_strategy.set_hook("after_goto", after_goto_hook)
            
            # [SB] 대시보드 접속 및 로그인 (Hook에서 스크린샷 처리)
            dashboard_result = await crawler.arun(
                login_config["d_url"], 
                config=dashboard_run_config  # [SB] screenshot=False 설정
            )
            
            if not state["login_success"] or not state["dashboard_url"]:
                print("[SB] 로그인 또는 대시보드 진입 실패 - 스크린샷 없이 진행")
                dashboard_screenshot_data = None
            else:
                print(f"[SB] 대시보드 로그인 성공: {state['dashboard_url']}")
                
                # [SB] Hook에서 캡처된 스크린샷 확인
                if dashboard_screenshot_data:
                    print(f"[SB] Hook에서 캡처된 스크린샷 크기: {dashboard_screenshot_data.getbuffer().nbytes:,} bytes")
                    print(f"[SB] 해상도: {browser_config.viewport_width}x{browser_config.viewport_height}")
                else:
                    print("[SB] Hook에서 스크린샷이 캡처되지 않았습니다.")
            
            print("\n[SB] 링크 체크 로직 수행...")
            
            # [SB] FrontEnd 링크 체크
            frontend = llm_json.get("FrontEnd", {})
            print(f"\n[SB] FrontEnd 조건 체크:")
            print(f"    상태: {frontend.get('상태')} (예와 같은가? {frontend.get('상태') == '예'})")
            print(f"    도메인 검색: {frontend.get('도메인 검색')} (예와 같은가? {frontend.get('도메인 검색') == '예'})")
            
            condition1 = frontend.get("상태") != "예"
            condition2 = frontend.get("도메인 검색") != "예"
            should_check = condition1 or condition2
            
            if should_check:
                print(f"[SB] FrontEnd 링크 체크 실행: {login_config['frontend']}")
                # [SB] 링크 체크는 스크린샷 없이 빠르게
                front_success = await crawler.arun(login_config["frontend"], config=link_check_run_config)
                f_status = "비정상"
                if front_success.status_code == 200:
                    f_status = "정상"
                print(f"[SB] FrontEnd 크롤링 결과: Status Code {front_success.status_code} → {f_status}")
                llm_json["FrontEnd"]["link"] = f_status
                print(f"[SB] FrontEnd link 설정됨: {f_status}")
            else:
                print("[SB] FrontEnd 링크 체크 건너뜀")
            
            # [SB] 운영중인서비스 링크 체크
            using_services = llm_json.get("운영중인서비스", {})
            
            # URL 체크
            url_condition = using_services.get("url") != "예"
            if url_condition:
                print(f"[SB] URL 링크 체크 실행: {login_config['url']}")
                url_success = await crawler.arun(login_config["url"], config=link_check_run_config)
                u_status = "비정상"
                if url_success.status_code == 200:
                    u_status = "정상"
                print(f"[SB] URL 크롤링 결과: Status Code {url_success.status_code} → {u_status}")
                llm_json["운영중인서비스"]["url_link"] = u_status
                print(f"[SB] URL link 설정됨: {u_status}")
            else:
                print("[SB] URL 링크 체크 건너뜀")
            
            print("\n[SB] 링크 체크 후 최종 LLM 데이터:")
            print(json.dumps(llm_json, indent=2, ensure_ascii=False))
        
        # [SB] 스크린샷 데이터 확인
        if dashboard_screenshot_data:
            screenshot_size = dashboard_screenshot_data.getbuffer().nbytes
            print(f"\n[SB] Hook으로 캡처한 스크린샷:")
            print(f"     크기: {screenshot_size:,} bytes")
            print(f"     해상도: {browser_config.viewport_width}x{browser_config.viewport_height}")
            print(f"     방법: Hook에서 직접 page.screenshot() 호출")
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
        
        # [SB] 디스크에 저장 (Hook으로 캡처한 스크린샷 포함)
        excel_path = create_dashboard_excel(
            llm_json, 
            in_memory=False,  # [SB] logs 폴더에 파일로 저장
            username="테스트",
            dashboard_screenshot=dashboard_screenshot_data  # [SB] Hook 스크린샷 데이터 전달
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
            print("  - 시트 1: 대시보드 체크리스트 (이미지 없이 텍스트만)")
            print("  - 시트 2: 원본 스크린샷 (Hook으로 캡처한 대시보드 스크린샷)")
            print("\n[SB] 구글 스프레드시트 호환성 (수정사항 반영):")
            print(f"  - 브라우저 해상도 축소: {browser_config.viewport_width}x{browser_config.viewport_height}")
            print("  - Hook에서 직접 page.screenshot() 사용")
            print("  - 첫 번째 시트에는 이미지 없이 텍스트만")
            print("  - 원본 스크린샷 시트에만 이미지 저장")
            print("  - 추가 라이브러리 설치 불필요")
        else:
            print("[SB] 파일이 생성되지 않았습니다. ❌")
            
    except Exception as e:
        print(f"[SB] 오류 발생: {e}")
        import traceback
        traceback.print_exc()  # [SB] 상세한 오류 정보 출력
        print("[SB] 원본 LLM 응답:")
        print(llm_answer)

if __name__ == "__main__":
    print("[SB] xlsx 테스트 스크립트 실행 (Hook에서 직접 스크린샷)")
    print("="*70)
    print("[SB] ✅ Hook에서 직접 page.screenshot() 사용")
    print("[SB] ✅ 첫 번째 시트에는 이미지 없이 텍스트만")
    print("[SB] ✅ 원본 스크린샷 시트에만 이미지 저장")
    print("[SB] ✅ 추가 라이브러리 설치 불필요")
    
    # [SB] async 함수 실행
    asyncio.run(test_xlsx_generation())
    
    print("\n" + "="*70)
    print("[SB] 테스트 완료!")
    print("[SB] logs 폴더에서 생성된 Excel 파일을 확인해보세요.")
    print("[SB] Hook에서 직접 캡처한 스크린샷이 원본 스크린샷 시트에만 저장됩니다.")
    print("[SB] 구글 스프레드시트에서 열 수 있도록 최적화되었습니다.")