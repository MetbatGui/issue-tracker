"""Excel Utility Functions
"""
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.utils import get_column_letter

def apply_auto_column_width(worksheet: Worksheet, min_width: int = 10, max_width: int = 100) -> None:
    """Adjusts column width based on content length.
    
    Args:
        worksheet: OPENPYXL Worksheet object
        min_width: Minimum column width
        max_width: Maximum column width
    """
    for column_cells in worksheet.columns:
        length = max(len(str(cell.value) or "") for cell in column_cells)
        
        # 한글 등 멀티바이트 문자 고려 (대략적으로 2배 계산하거나, 단순 길이 + 여유분)
        # 여기서는 단순 문자열 길이에 여유분을 둠.
        # 엑셀의 너비 단위는 대략 영문자 너비 기준이므로, 한글이 포함되면 좀 더 넓게 잡아야 함.
        
        # 간단한 휴리스틱: 길이 * 1.2 + 2
        final_width = (length * 1.2) + 2
        
        final_width = min(max(final_width, min_width), max_width)
        
        col_letter = get_column_letter(column_cells[0].column)
        worksheet.column_dimensions[col_letter].width = final_width
