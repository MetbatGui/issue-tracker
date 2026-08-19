import pandas as pd
import sys
from pathlib import Path

# UTF-8 인코딩 설정 (윈도우 콘솔용)
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def check_excel_parent_rcp():
    excel_path = Path("data/전환사채/전환사채.xlsx")
    
    if not excel_path.exists():
        print("❌ Excel file not found.")
        return

    print(f"🔍 Checking Parent Receipt Numbers in Excel...")
    
    try:
        # Read all sheets
        xls = pd.ExcelFile(excel_path)
        print(f"📄 Sheets: {xls.sheet_names}")
        
        total_rows = 0
        rows_with_parent = 0
        
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(excel_path, sheet_name=sheet_name)
            
            if '상위접수번호' not in df.columns:
                print(f"  Warning: '상위접수번호' column missing in sheet {sheet_name}")
                continue
                
            sheet_rows = len(df)
            total_rows += sheet_rows
            
            # Count non-empty parent_rcp_no
            # Convert to string, remove '.0', replace 'nan' with empty
            parents = df['상위접수번호'].astype(str).str.replace(r'\.0$', '', regex=True).replace('nan', '')
            valid_parents = parents[parents != '']
            
            sheet_valid = len(valid_parents)
            rows_with_parent += sheet_valid
            
            print(f"  [Sheet: {sheet_name}] Rows: {sheet_rows}, With Parent: {sheet_valid}")
            
            # Sample check
            if sheet_valid > 0:
                print(f"    Sample: {valid_parents.iloc[0]}")
                
        print(f"\n📊 Result: Total Rows {total_rows}, Rows with Parent {rows_with_parent}")
        
        if rows_with_parent > 0:
             print("✅ Success: Parent Receipt Numbers found.")
        else:
             print("⚠️ Warning: No Parent Receipt Numbers found. (Maybe expected if no corrections?)")

    except Exception as e:
        print(f"❌ Error reading Excel: {e}")

if __name__ == "__main__":
    check_excel_parent_rcp()
