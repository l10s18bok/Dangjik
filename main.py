# main.py 수정 부분

import asyncio
import json
import os
import sys
import stat
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from utils.xlsx import create_dashboard_excel
from utils.fields import extract_fields
from utils.llm import analyze_with_ollama
from utils.mattermost import send_excel_to_self, send_excel_to_team_channel, verify_mattermost_env, get_mattermost_username
import io

# 환경 변수 로드
load_dotenv()

async def main():
    # 로그인 정보
    login_config = {
        "d_url": os.getenv("DASHBOARD_URL"),
        "username": os.getenv("DASHBOARD_USERNAME"),
        "password": os.getenv("DASHBOARD_PASSWORD"),
        "frontend": os.getenv("FRONTEND_LINK"),
        "parking": os.getenv("PARKING_LINK"),
        "url": os.getenv("URL_LINK"),
        "furl": os.getenv("FURL_LINK"),
    }
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    browser_config = BrowserConfig(
        browser_type="chromium",
        headless=True,
        verbose=True,
        java_script_enabled=True,
        viewport_width=1024,
        viewport_height=768,
        extra_args=[
            "--disable-web-security",
            "--disable-font-subpixel-positioning",
            "--force-device-scale-factor=1", 
            "--lang=ko-KR",
            "--accept-lang=ko-KR,ko,en-US,en"
        ]
    )
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        delay_before_return_html=3.0,
        wait_until="networkidle",
        exclude_external_images=True,  # [SB] 외부 이미지 제외로 속도 향상
    )
    state = {"login_success": False, "dashboard_url": None, "login_processed": False}
    dashboard_screenshot_data = None  # [SB] 대시보드 스크린샷 메모리 저장용

    async def after_goto_hook(page, context, **kwargs):
        nonlocal dashboard_screenshot_data
        
        if state["login_processed"]:
            return
        if "hydra2.uxcloud.net" in page.url and "/page/" not in page.url:
            try:
                state["login_processed"] = True
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
                
                # [SB] 대시보드 스크린샷 원본 캡처 (축소 없음)
                print("[SB] 대시보드 스크린샷 캡처 중...")
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
                    
                    # [SB] 이미 로그인된 경우에도 스크린샷 캡처 (축소 없음)
                    print("[SB] 대시보드 스크린샷 캡처 중...")
                    screenshot_bytes = await page.screenshot(type='png', full_page=True)
                    
                    # [SB] 원본 이미지를 메모리 버퍼에 직접 저장
                    dashboard_screenshot_data = io.BytesIO(screenshot_bytes)
                    dashboard_screenshot_data.seek(0)  # 포인터를 시작으로 리셋
                    
                    print(f"[SB] 대시보드 스크린샷 캡처 완료 (원본 크기, {len(screenshot_bytes):,} bytes)")
                    
                except Exception as e:
                    print(f"[SB] 페이지 로딩 오류: {e}")

    async with AsyncWebCrawler(config=browser_config) as crawler:
        crawler.crawler_strategy.set_hook("after_goto", after_goto_hook)
        result = await crawler.arun(login_config["d_url"], config=run_config)
        if not state["login_success"] or not state["dashboard_url"]:
            print("[SB] 로그인 또는 대시보드 진입 실패")
            return
        print(f"[SB] 대시보드 URL: {state['dashboard_url']}")
        
        # HTML 추출 및 필드 추출
        html = result.html
        extracted = extract_fields(html, login_status="정상")
        print(f"[SB] 필드 추출 결과:")
        print(json.dumps(extracted, indent=2, ensure_ascii=False))
        
        # LLM에 질문
        llm_answer = analyze_with_ollama(extracted)
        try:
            llm_json = json.loads(llm_answer)

            # [SB] FrontEnd 링크 체크, Parking 링크 체크, URL 링크 체크, FURL 링크 체크
            frontend = llm_json.get("FrontEnd", {})
            if frontend.get("상태") != "예" or frontend.get("도메인 검색") != "예":
                front_success = await crawler.arun(login_config["frontend"], config=run_config)
                f_status = "비정상"
                if front_success.status_code == 200:
                    f_status = "정상"
                llm_json["FrontEnd"]["link"] = f_status  # [SB] 쉼표 없음
                print(f"[SB] FrontEnd link url : {f_status}")

            using_services = llm_json.get("운영중인서비스", {})
            if using_services.get("parking") != "예":
                parking_success = await crawler.arun(login_config["parking"], config=run_config)
                p_status = "비정상"
                if parking_success.status_code == 200:
                    p_status = "정상"
                llm_json["운영중인서비스"]["parking_link"] = p_status
                print(f"[SB] Parking link url : {p_status}")

            if using_services.get("url") != "예":
                url_success = await crawler.arun(login_config["url"], config=run_config)
                u_status = "비정상"
                if url_success.status_code == 200:
                    u_status = "정상"
                llm_json["운영중인서비스"]["url_link"] = u_status
                print(f"[SB] url link url : {u_status}")

            if using_services.get("furl") != "예":
                furl_success = await crawler.arun(login_config["furl"], config=run_config)
                f_status = "비정상"
                if furl_success.status_code == 200:
                    f_status = "정상"
                llm_json["운영중인서비스"]["furl_link"] = f_status
                print(f"[SB] furl link url : {f_status}")

            print(f"[SB] LLM 분석 결과:")
            print(json.dumps(llm_json, indent=2, ensure_ascii=False))
            
            # Mattermost 환경 변수 확인
            env_status = verify_mattermost_env()
            
            if not env_status["status"]:
                print(f"[SB] Mattermost 필수 환경 변수가 설정되지 않았습니다: {', '.join(env_status['missing_required'])}")
                # 사용자 이름 없이 Excel 생성 (스크린샷 포함)
                excel_file = create_dashboard_excel(llm_json, in_memory=True, dashboard_screenshot=dashboard_screenshot_data)
            else:
                # Mattermost에서 사용자 이름 가져오기
                mm_success, username, user_id = get_mattermost_username()
                
                if mm_success and username:
                    print(f"[SB] Mattermost에서 사용자 이름 '{username}'를 가져왔습니다.")
                    # 사용자 이름을 포함하여 Excel 대시보드 생성 (스크린샷 포함)
                    excel_file = create_dashboard_excel(llm_json, in_memory=True, username=username, dashboard_screenshot=dashboard_screenshot_data)
                else:
                    print(f"[SB] Mattermost에서 사용자 이름을 가져오지 못했습니다. 기본 이름으로 Excel을 생성합니다.")
                    # 사용자 이름 없이 Excel 생성 (스크린샷 포함)
                    excel_file = create_dashboard_excel(llm_json, in_memory=True, dashboard_screenshot=dashboard_screenshot_data)
                
                # 자신에게 Excel 보고서 전송
                success = send_excel_to_self(excel_file)
                # 팀 당직채널에도 Excel 보고서 전송
                # 팀 채널 전송 가능한지 확인
                if "MATTERMOST_TEAM_INNOGS" in env_status["available"] and "MATTERMOST_CHANNEL" in env_status["available"]:
                    # 팀 채널에도 보고서 전송
                    team_success = send_excel_to_team_channel(
                        excel_file,
                        team_key="INNOGS",
                    )  
                
                if success:
                    print(f"[SB] 대시보드 보고서가 Mattermost를 통해 성공적으로 전송되었습니다.")
                else:
                    print(f"[SB] 대시보드 보고서 전송 실패")
                
                # 메모리 객체 정리
                excel_file.close()
                del excel_file
            
        except Exception as e:
            print(f"[SB] LLM 응답 JSON 파싱 오류: {e}")
            print("[SB] 원본 LLM 응답:")
            print(llm_answer)

if __name__ == "__main__":
    asyncio.run(main())
