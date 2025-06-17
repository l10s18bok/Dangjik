# utils/llm.py
import json
import re
import ollama

# Ollama LLM 분석 함수
def analyze_with_ollama(extracted_json):
    # LLM 질문 프롬프트
    prompt = f'''
다음 데이터를 분석하고, 아래 질문에 대해 정확히 "예" 또는 "아니요"로만 답변해주세요.
각 질문에 대해 번호와 함께 한 줄로 답변하세요. 다른 설명은 추가하지 마세요.
예시 형식: "1. 예", "2. 아니요"

데이터: {json.dumps(extracted_json, ensure_ascii=False)}

질문:
1. 로그인상태의 값이 "정상"인가요?
2. 스케줄러상태의 값이 "적용됨"인가요?
3. 1:1문의의 값이 "0 개"인가요?
4. 이메일문의의 값이 "0 개"인가요?
5. 에러리포트의 값이 "0 개"인가요?
6. Region활성의 값이 "2 개"인가요?
7. 장비미보고 값이 "0 개"인가요?
8. DB_Sync의 일시중지 값이 "0 개"인가요?
9. DB_Sync의 오류 값이 "0 개"인가요?
10. FrontEnd의 상태 값이 "정상"인가요?
11. FrontEnd의 도메인 검색 값이 "정상"인가요?
12. 운영중인서비스의 parking 값이 "정상"인가요?
13. 운영중인서비스의 url 값이 "정상"인가요?
14. 운영중인서비스의 furl 값이 "정상"인가요?
15. Whois USD 예치금은 얼마인가요? (숫자만 답하세요)
16. Gabia KRW 예치금은 얼마인가요? (숫자만 답하세요)
'''
    print(f"[SB] LLM 분석 중....\n")
    
    # [SB] 기대되는 결과 생성 (화폐값 제외한 예상 응답)
    expected_results = {
        "로그인상태": "예" if extracted_json.get("로그인상태") == "정상" else "아니요",
        "whois_usd": extracted_json.get("whois_usd", "0 USD"),
        "gabia_krw": extracted_json.get("gabia_krw", "0 KRW"),
        "스케줄러상태": "예" if extracted_json.get("스케줄러상태") == "적용됨" else "아니요",
        "1:1문의": "예" if extracted_json.get("1:1문의", "1개") == "0 개" else "아니요",
        "이메일문의": "예" if extracted_json.get("이메일문의", "1개") == "0 개" else "아니요",
        "에러리포트": "예" if extracted_json.get("에러리포트", "1개") == "0 개" else "아니요",
        "Region활성": "예" if extracted_json.get("Region활성") == "2 개" else "아니요",
        "장비미보고": "예" if extracted_json.get("장비미보고", "1개") == "0 개" else "아니요",
        "DB_Sync": {
            "일시중지": "예" if extracted_json.get("DB_Sync", {}).get("일시중지", "1개") == "0 개" else "아니요",
            "오류": "예" if extracted_json.get("DB_Sync", {}).get("오류", "1개") == "0 개" else "아니요"
        },
        "FrontEnd": {
            "상태": "예" if extracted_json.get("FrontEnd", {}).get("상태", "") == "정상" else "아니요",
            "도메인 검색": "예" if extracted_json.get("FrontEnd", {}).get("도메인 검색", "") == "정상" else "아니요"
        },
        "운영중인서비스": {
            "parking": "예" if extracted_json.get("운영중인서비스", {}).get("parking", "") == "정상" else "아니요",
            "url": "예" if extracted_json.get("운영중인서비스", {}).get("url", "") == "정상" else "아니요",
            "furl": "예" if extracted_json.get("운영중인서비스", {}).get("furl", "") == "정상" else "아니요"
        }
    }
    
    # LLM에게 한 번만 질문, 불일치 시 예상 결과(expected_results) 사용
    try:
        print(f"[SB] LLM 분석 시도...")
        
        # LLM 모델 호출
        response = ollama.chat(
            model='EEVE-Korean-10.8B:latest',
            messages=[{'role': 'user', 'content': prompt}],
            options={"temperature": 0.1}  # [SB] 낮은 temperature로 일관된 응답 유도
        )
        
        # LLM 응답 처리
        llm_response = response['message']['content']
        print(f"[SB] LLM 원시 응답: \n{llm_response}")
        
        # [SB] 간단한 응답 파싱 함수
        def parse_llm_response(response_text):
            result = {
                "로그인상태": "아니요",
                "whois_usd": extracted_json.get("whois_usd", "0 USD"),
                "gabia_krw": extracted_json.get("gabia_krw", "0 KRW"),
                "스케줄러상태": "아니요",
                "1:1문의": "아니요",
                "이메일문의": "아니요",
                "에러리포트": "아니요",
                "Region활성": "아니요",
                "장비미보고": "아니요",
                "DB_Sync": {
                    "일시중지": "아니요",
                    "오류": "아니요"
                },
                "FrontEnd": {
                    "상태": "아니요",
                    "도메인 검색": "아니요"
                },
                "운영중인서비스": {
                    "parking": "아니요",
                    "url": "아니요",
                    "furl": "아니요"
                }
            }
            
            # [SB] 라인별로 처리
            lines = response_text.split('\n')
            for line in lines:
                line = line.strip()
                
                # [SB] 예/아니요 응답 처리 (1-14번 질문)
                if re.match(r'^\d+[\.\)]', line):
                    num_match = re.match(r'^(\d+)[\.\)]', line)
                    if not num_match:
                        continue
                        
                    q_num = int(num_match.group(1))
                    answer = "아니요"
                    if "예" in line:
                        answer = "예"
                    
                    # [SB] 번호에 따라 해당 필드 업데이트
                    if q_num == 1:
                        result["로그인상태"] = answer
                    elif q_num == 2:
                        result["스케줄러상태"] = answer
                    elif q_num == 3:
                        result["1:1문의"] = answer
                    elif q_num == 4:
                        result["이메일문의"] = answer
                    elif q_num == 5:
                        result["에러리포트"] = answer
                    elif q_num == 6:
                        result["Region활성"] = answer
                    elif q_num == 7:
                        result["장비미보고"] = answer
                    elif q_num == 8:
                        result["DB_Sync"]["일시중지"] = answer
                    elif q_num == 9:
                        result["DB_Sync"]["오류"] = answer
                    elif q_num == 10:
                        result["FrontEnd"]["상태"] = answer
                    elif q_num == 11:
                        result["FrontEnd"]["도메인 검색"] = answer
                    elif q_num == 12:
                        result["운영중인서비스"]["parking"] = answer
                    elif q_num == 13:
                        result["운영중인서비스"]["url"] = answer
                    elif q_num == 14:
                        result["운영중인서비스"]["furl"] = answer
                
                # [SB] 15번, 16번 화폐 값 처리 - LLM 응답 그대로 사용
                # [SB] 15번 질문: "15. 1,072.88 USD" -> "1,072.88 USD" 추출
                if line.startswith("15."):
                    # [SB] "15. " 부분을 제거하고 나머지 텍스트 그대로 사용
                    answer_part = line[3:].strip()  # [SB] "15." 3글자 제거
                    if answer_part:  # [SB] 빈 문자열이 아닌 경우만 사용
                        result["whois_usd"] = answer_part
                
                # [SB] 16번 질문: "16. 442,400 KRW" -> "442,400 KRW" 추출  
                elif line.startswith("16."):
                    # [SB] "16. " 부분을 제거하고 나머지 텍스트 그대로 사용
                    answer_part = line[3:].strip()  # [SB] "16." 3글자 제거
                    if answer_part:  # [SB] 빈 문자열이 아닌 경우만 사용
                        result["gabia_krw"] = answer_part
            
            return result
        
        # [SB] 응답 파싱
        result = parse_llm_response(llm_response)
        
        
        # [SB] 결과 검증 - 예상 결과와 일치하는지 확인 (화폐값 제외)
        all_match = True
        mismatch_count = 0
        
        # [SB] 불일치 항목 체크 및 출력 (화폐값도 비교 대상에 포함)
        for key in expected_results:
            if key in ["DB_Sync", "FrontEnd", "운영중인서비스"]:
                for sub_key in expected_results[key]:
                    if expected_results[key][sub_key] != result[key][sub_key]:
                        all_match = False
                        mismatch_count += 1
                        print(f"[SB] 불일치: {key}.{sub_key} - 예상: {expected_results[key][sub_key]}, 실제: {result[key][sub_key]}")
                        # [SB] 불일치시 예상 결과로 대체
                        result[key][sub_key] = expected_results[key][sub_key]
            else:
                # [SB] 화폐값 포함 모든 항목 비교
                if expected_results[key] != result[key]:
                    all_match = False
                    mismatch_count += 1
                    print(f"[SB] 불일치: {key} - 예상: {expected_results[key]}, 실제: {result[key]}")
                    # [SB] 불일치시 예상 결과로 대체 (화폐값 포함)
                    result[key] = expected_results[key]
        
        # [SB] 결과 출력 및 반환
        if all_match:
            print(f"[SB] 모든 값이 예상과 일치합니다!")
        else:
            print(f"[SB] {mismatch_count}개 항목 불일치, 예상 결과로 대체했습니다.")
        
        return json.dumps(result, ensure_ascii=False)
            
    except Exception as e:
        print(f"[SB] LLM 분석 중 오류 발생: {e}")
        # [SB] 오류 발생 시 기존 값 사용 (화폐값은 원본 데이터 유지)
        return json.dumps(expected_results, ensure_ascii=False)