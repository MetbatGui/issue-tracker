import re
import requests
from typing import List, Set
from bs4 import BeautifulSoup

class DartHistoryScraper:
    """DART 공시 이력 스크래퍼"""
    
    def __init__(self):
        pass
        
    def get_history_rcp_list(self, rcp_no: str) -> List[str]:
        """주어진 공시의 DART 뷰어 페이지에서 관련 공시(이력) 접수번호들을 추출합니다.
        
        Args:
            rcp_no: 기준 공시 접수번호
            
        Returns:
            관련 접수번호(rcp_no) 목록 (오름차순 정렬)
        """
        url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcp_no}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        try:
            import time
            import random
            import http.client
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry

            # 재시도 로직 설정
            session = requests.Session()
            retry = Retry(
                total=5,
                connect=5,
                read=5,
                backoff_factor=1.0,
                allowed_methods=["HEAD", "GET", "OPTIONS"],
                status_forcelist=[429, 500, 502, 503, 504]
            )
            adapter = HTTPAdapter(max_retries=retry)
            session.mount('http://', adapter)
            session.mount('https://', adapter)

            # 랜덤 지연 (1.0 ~ 2.0초) - 차단 회피 강화
            sleep_time = random.uniform(1.0, 2.0)
            time.sleep(sleep_time)

            response = session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            html = response.text
            
            soup = BeautifulSoup(html, "html.parser")
            found_ids: Set[str] = set()
            
            # 1. 문서목록 (History) Select Box 파싱 (id="family")
            history_select = soup.find("select", id="family")
            if history_select:
                for option in history_select.find_all("option"):
                    value = option.get("value", "")
                    # value format: "rcpNo=2023..." or just "2023..." sometimes? usually "rcpNo=..."
                    # Extract 14 digit number
                    match = re.search(r"rcpNo=(\d{14})", value)
                    if match:
                        found_ids.add(match.group(1))
            
            # 2. 기준 rcp_no는 항상 포함 (혹시 목록에 없더라도)
            found_ids.add(rcp_no)
            
            # 정렬하여 반환
            return sorted(list(found_ids))
            
        except (requests.exceptions.ConnectionError, http.client.RemoteDisconnected) as e:
            print(f"  └ [Warning] 이력 추출 연결 실패 (재시도 소진, {rcp_no}): {e}")
            return [rcp_no]
        except Exception as e:
            print(f"  └ [Warning] 이력 추출 실패 ({rcp_no}): {e}")
            return [rcp_no]
