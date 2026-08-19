"""기재정정 히스토리 추적 디버깅 스크립트"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.infrastructure import DartHistoryScraper

def debug_history():
    sys.stdout.reconfigure(encoding='utf-8')
    scraper = DartHistoryScraper()
    
    # 씨엔플러스 [기재정정]주요사항보고서(전환사채권발행결정)
    rcept_no = "20251209000395" 
    
    print(f"Checking history for {rcept_no}...")
    history = scraper.get_history_rcp_list(rcept_no)
    
    print(f"History IDs: {history}")
    
    if len(history) > 1:
        print("✅ History found!")
        for i in range(1, len(history)):
            parent = history[i-1]
            child = history[i]
            print(f"  Relation: {child} -> {parent}")
    else:
        print("❌ No history or single item found.")

if __name__ == "__main__":
    debug_history()
