"""비대화형 실행 환경의 로그 순서를 보장하기 위한 회귀 테스트."""
import ast
from pathlib import Path


def test_src_does_not_call_print():
    source_root = Path("src")
    violations = []

    for source_file in source_root.rglob("*.py"):
        tree = ast.parse(source_file.read_text(encoding="utf-8"), filename=str(source_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
                violations.append(f"{source_file}:{node.lineno}")

    assert not violations, "src의 print() 호출: " + ", ".join(violations)
