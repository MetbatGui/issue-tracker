"""도메인 포트 인터페이스

포트-어댑터 패턴을 위한 추상 인터페이스를 정의합니다.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, Dict, Any


__all__ = ["StoragePort"]


class StoragePort(ABC):
    """스토리지 추상 인터페이스 (포트)
    
    외부 스토리지 시스템(구글 드라이브, AWS S3 등)과의 
    상호작용을 위한 포트 인터페이스입니다.
    """
    
    @abstractmethod
    def upload_file(
        self, 
        file_path: Path, 
        folder_id: str,
        file_name: Optional[str] = None
    ) -> str:
        """파일을 스토리지에 업로드합니다.
        
        Args:
            file_path: 업로드할 로컬 파일 경로
            folder_id: 대상 폴더 ID
            file_name: 업로드할 파일명 (None이면 원본 파일명 사용)
        
        Returns:
            업로드된 파일의 ID 또는 URL
        
        Raises:
            Exception: 업로드 실패 시
        """
        pass
    
    @abstractmethod
    def delete_file(self, file_id: str) -> bool:
        """파일을 삭제합니다.
        
        Args:
            file_id: 삭제할 파일의 ID
        
        Returns:
            삭제 성공 여부
        """
        pass
    
    @abstractmethod
    def list_files(self, folder_id: str) -> List[Dict[str, Any]]:
        """폴더 내 파일 목록을 조회합니다.
        
        Args:
            folder_id: 조회할 폴더 ID
        
        Returns:
            파일 정보 딕셔너리 리스트
        """
        pass
