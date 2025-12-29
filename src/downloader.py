import os
import json
import re
import requests
import time
import zipfile
import io
from datetime import datetime, timedelta
from dotenv import load_dotenv

# ==========================================
# [설정 영역]
# .env 파일에서 API 키 로드
# ==========================================
load_dotenv()  # .env 파일 활성화
DART_API_KEY = os.getenv("DART_API_KEY")

# 저장할 폴더 설정
BASE_DIR = "data"
SUB_DIR = "유상증자"
XML_SUB_DIR = "xml"  # XML 파일 저장할 하위 폴더
SAVE_PATH = os.path.join(BASE_DIR, SUB_DIR)
XML_SAVE_PATH = os.path.join(SAVE_PATH, XML_SUB_DIR)

def fetch_disclosure_list(api_key, bgn_de, end_de, page_no=1, page_count=100):
    """Open DART 공시검색 API 호출"""
    url = "https://opendart.fss.or.kr/api/list.json"
    params = {
        "crtfc_key": api_key,
        "bgn_de": bgn_de,
        "end_de": end_de,
        "pblntf_ty": "B",  # 주요사항보고서
        "page_no": page_no,
        "page_count": page_count,
        "last_reprt_at": "Y"
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        time.sleep(0.1) # API 부하 조절
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"[Error] 목록 검색 실패: {e}")
        return None

def download_document_xml(api_key, rcept_no, corp_name):
    """
    상세 원본 파일(document.xml) 다운로드 및 저장
    """
    url = "https://opendart.fss.or.kr/api/document.xml"
    params = {
        "crtfc_key": api_key,
        "rcept_no": rcept_no
    }
    
    # 저장될 파일명: [회사명]_[접수번호].xml
    # 파일명에 쓸 수 없는 특수문자 제거
    safe_corp_name = re.sub(r'[\\/*?:"<>|]', "", corp_name)
    filename = f"{safe_corp_name}_{rcept_no}.xml"
    file_path = os.path.join(XML_SAVE_PATH, filename)

    # 이미 다운로드 받았다면 건너뜀 (시간 절약)
    if os.path.exists(file_path):
        return file_path

    try:
        # ZIP 파일 형태로 받아짐
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        # 메모리 상에서 압축 해제
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            # 보통 압축 내부에 파일이 하나 들어있음 (파일명은 제각각일 수 있음)
            xml_filename_in_zip = z.namelist()[0]
            xml_data = z.read(xml_filename_in_zip)
            
            # 우리가 원하는 이름으로 XML 저장
            with open(file_path, "wb") as f:
                f.write(xml_data)
        
        # API 과부하 방지 딜레이 (파일 다운로드는 무거우므로 조금 더 쉼)
        time.sleep(0.2) 
        return file_path

    except Exception as e:
        print(f"  └ [Error] XML 다운로드 실패 ({corp_name}): {e}")
        return None

def filter_reports(data_list):
    """정규식 필터링: [기재정정](선택) + 유상증자결정(필수) + (괄호내용)(선택)"""
    filtered = []
    if not data_list:
        return filtered

    regex = re.compile(r"^(\[기재정정\]\s*)?유상증자결정(\s*\(.*\))?$")
    
    for item in data_list:
        report_nm = item.get("report_nm", "").strip()
        if regex.fullmatch(report_nm):
            filtered.append(item)
    return filtered

def save_to_json(data, filename):
    """데이터 저장"""
    if not os.path.exists(SAVE_PATH):
        os.makedirs(SAVE_PATH)
    
    file_path = os.path.join(SAVE_PATH, filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"\n[저장 완료] 목록 파일: {filename} ({len(data)}건)")

def main():
    if not DART_API_KEY:
        print("❌ .env 파일에 DART_API_KEY가 설정되지 않았습니다.")
        return

    # XML 저장 디렉토리 생성
    if not os.path.exists(XML_SAVE_PATH):
        os.makedirs(XML_SAVE_PATH)

    # 1. 기간 설정
    start_str = "20200101"
    end_str = datetime.now().strftime("%Y%m%d")
    
    curr_start = datetime.strptime(start_str, "%Y%m%d")
    final_end = datetime.strptime(end_str, "%Y%m%d")

    all_filtered_reports = []
    
    print(f"🚀 수집 시작: {start_str} ~ {end_str}")
    print(f"📂 XML 저장 경로: {XML_SAVE_PATH}")

    # 2. 3개월 단위 루프
    while curr_start <= final_end:
        curr_end = curr_start + timedelta(days=90)
        if curr_end > final_end:
            curr_end = final_end
            
        bgn_de = curr_start.strftime("%Y%m%d")
        end_de = curr_end.strftime("%Y%m%d")
        
        print(f"\n📅 기간 검색: {bgn_de} ~ {end_de}")
        
        page = 1
        while True:
            result = fetch_disclosure_list(DART_API_KEY, bgn_de, end_de, page_no=page)
            
            if not result: break
            if result.get('status') != '000':
                if result.get('status') != '013':
                    print(f"  ⚠️ API 메시지: {result.get('message')}")
                break
                
            list_data = result.get('list', [])
            if not list_data: break
            
            # 필터링
            filtered = filter_reports(list_data)
            
            # === [추가된 부분] 필터링된 항목들에 대해 XML 다운로드 ===
            for item in filtered:
                rcept_no = item['rcept_no']
                corp_name = item['corp_name']
                
                # XML 다운로드 실행
                xml_path = download_document_xml(DART_API_KEY, rcept_no, corp_name)
                
                # JSON 결과에 로컬 파일 경로 추가
                if xml_path:
                    item['xml_path'] = xml_path
            # ========================================================
            
            all_filtered_reports.extend(filtered)
            
            # 진행상황 출력 (XML 다운로드 때문에 속도가 느릴 수 있음)
            print(f"  - p.{page} 완료: {len(filtered)}건 추가 (누적 {len(all_filtered_reports)}건)", end="\r")
            
            total_page = int(result.get('total_page', 1))
            if page >= total_page:
                break
            page += 1
            
        curr_start = curr_end + timedelta(days=1)

    print("\n\n✅ 전체 수집 및 XML 다운로드 완료.")

    # 3. 결과 목록 저장
    if all_filtered_reports:
        filename = f"paid_increase_{start_str}_to_{end_str}.json"
        save_to_json(all_filtered_reports, filename)
    else:
        print("해당 기간 내 수집된 데이터가 없습니다.")

if __name__ == "__main__":
    main()