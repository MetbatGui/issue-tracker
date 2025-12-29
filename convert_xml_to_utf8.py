"""XML 파일들을 UTF-8 인코딩으로 변환하는 스크립트"""
from pathlib import Path


def try_read_with_encoding(file_path: Path, encoding: str) -> str | None:
    """특정 인코딩으로 파일을 읽어봅니다."""
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    except (UnicodeDecodeError, LookupError):
        return None


def detect_and_read(file_path: Path) -> tuple[str, str] | None:
    """여러 인코딩을 시도하여 파일을 읽습니다."""
    # 시도할 인코딩 목록 (한국어 파일에서 자주 사용되는 순서)
    encodings = ['utf-8', 'cp949', 'euc-kr', 'latin-1']
    
    for encoding in encodings:
        content = try_read_with_encoding(file_path, encoding)
        if content is not None:
            return encoding, content
    
    return None


def convert_to_utf8(file_path: Path) -> None:
    """파일을 UTF-8로 변환합니다."""
    result = detect_and_read(file_path)
    
    if result is None:
        print(f"[오류] {file_path.name}: 인코딩을 감지할 수 없습니다")
        return
    
    current_encoding, content = result
    
    if current_encoding.lower() == 'utf-8':
        print(f"[건너뜀] {file_path.name}: 이미 UTF-8")
        return
    
    try:
        # UTF-8로 다시 쓰기
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"[변환완료] {file_path.name}: {current_encoding} -> UTF-8")
    except Exception as e:
        print(f"[오류] {file_path.name}: 오류 발생 - {e}")


def main():
    """메인 함수"""
    xml_dir = Path(r"c:\Users\user\Documents\최지석\Projects\issue-tracker\data\유상증자\xml")
    
    if not xml_dir.exists():
        print(f"디렉토리를 찾을 수 없습니다: {xml_dir}")
        return
    
    xml_files = list(xml_dir.glob("*.xml"))
    print(f"총 {len(xml_files)}개의 XML 파일을 처리합니다.\n")
    
    converted_count = 0
    already_utf8_count = 0
    error_count = 0
    
    for xml_file in xml_files:
        result_before = detect_and_read(xml_file)
        if result_before and result_before[0].lower() != 'utf-8':
            convert_to_utf8(xml_file)
            converted_count += 1
        elif result_before and result_before[0].lower() == 'utf-8':
            print(f"[건너뜀] {xml_file.name}: 이미 UTF-8")
            already_utf8_count += 1
        else:
            print(f"[오류] {xml_file.name}: 인코딩을 감지할 수 없습니다")
            error_count += 1
    
    print(f"\n=== 완료 ===")
    print(f"변환됨: {converted_count}개")
    print(f"이미 UTF-8: {already_utf8_count}개")
    print(f"오류: {error_count}개")


if __name__ == "__main__":
    main()
