"""구글 드라이브 스토리지 어댑터

Google Drive API를 사용하여 파일을 업로드/관리하는 어댑터입니다.
"""
import sys
import os.path
from pathlib import Path
from typing import Optional, List, Dict, Any

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from ..logger import get_logger
from ..domain.ports import StoragePort


# UTF-8 인코딩 설정 (윈도우 콘솔용)
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


__all__ = ["GoogleDriveAdapter"]


class GoogleDriveAdapter(StoragePort):
    """구글 드라이브 스토리지 어댑터
    
    OAuth2 인증을 사용하여 구글 드라이브에 파일을 업로드하고 관리합니다.
    """
    
    SCOPES = ['https://www.googleapis.com/auth/drive']
    
    def __init__(
        self,
        credentials_path: str = "secrets/client_secret.json",
        token_path: str = "secrets/token.json"
    ):
        """구글 드라이브 어댑터를 초기화합니다.
        
        Args:
            credentials_path: OAuth2 클라이언트 시크릿 파일 경로
            token_path: 토큰 저장 경로
        """
        self.logger = get_logger(self.__class__.__name__)
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = self._authenticate()
    
    def _authenticate(self):
        """구글 드라이브 인증을 수행합니다.
        
        Returns:
            구글 드라이브 서비스 객체
        """
        creds = None
        
        # 기존 토큰 확인
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(
                self.token_path, self.SCOPES
            )
        
        # 토큰 갱신 또는 새로 생성
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                self.logger.info("🔄 토큰 갱신 중...")
                creds.refresh(Request())
            else:
                self.logger.info("🔐 구글 드라이브 인증 시작...")
                self.logger.info("브라우저에서 인증을 완료해주세요.")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # 토큰 저장
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
            self.logger.info("✅ 인증 완료!")
        
        return build('drive', 'v3', credentials=creds)
    
    def upload_file(
        self,
        file_path: Path,
        folder_id: str,
        file_name: Optional[str] = None
    ) -> str:
        """파일을 구글 드라이브에 업로드합니다.
        
        기존에 동일한 파일명이 있으면 덮어씁니다.
        
        Args:
            file_path: 업로드할 로컬 파일 경로
            folder_id: 대상 폴더 ID
            file_name: 업로드할 파일명 (None이면 원본 파일명 사용)
        
        Returns:
            업로드된 파일의 ID
        """
        if not file_path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
        
        if file_name is None:
            file_name = file_path.name
        
        # 1. 기존 파일 확인
        existing_file_id = self._find_file_by_name(folder_id, file_name)
        
        # 2. 파일 메타데이터
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        
        # 3. 미디어 업로드
        mime_type = (
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            if file_path.suffix.lower() == '.xlsx'
            else 'application/octet-stream'
        )
        media = MediaFileUpload(
            str(file_path),
            mimetype=mime_type,
            resumable=True
        )
        
        # 4. 업로드 또는 업데이트
        if existing_file_id:
            # 기존 파일 업데이트
            file = self.service.files().update(
                fileId=existing_file_id,
                media_body=media
            ).execute()
            self.logger.info(f"  ✅ 파일 업데이트: {file_name}")
        else:
            # 새 파일 생성
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            self.logger.info(f"  ✅ 새 파일 업로드: {file_name}")
        
        return file.get('id')
    
    def _find_file_by_name(self, folder_id: str, file_name: str) -> Optional[str]:
        """폴더 내에서 파일명으로 파일 ID를 검색합니다.
        
        Args:
            folder_id: 검색할 폴더 ID
            file_name: 검색할 파일명
        
        Returns:
            파일 ID (없으면 None)
        """
        # 파일명에 작은따옴표가 있으면 이스케이프
        escaped_name = file_name.replace("'", "\\'")
        query = f"name='{escaped_name}' and '{folder_id}' in parents and trashed=false"
        
        try:
            results = self.service.files().list(
                q=query,
                fields="files(id, name)",
                pageSize=10
            ).execute()
            
            files = results.get('files', [])
            return files[0]['id'] if files else None
        except Exception as e:
            self.logger.warning(f"  ⚠️ 파일 검색 중 오류: {e}")
            return None
    
    def delete_file(self, file_id: str) -> bool:
        """파일을 삭제합니다.
        
        Args:
            file_id: 삭제할 파일의 ID
        
        Returns:
            삭제 성공 여부
        """
        try:
            self.service.files().delete(fileId=file_id).execute()
            self.logger.info(f"  ✅ 파일 삭제 완료 (ID: {file_id})")
            return True
        except Exception as e:
            self.logger.error(f"  ❌ 파일 삭제 실패: {e}")
            return False
    
    def list_files(self, folder_id: str) -> List[Dict[str, Any]]:
        """폴더 내 파일 목록을 조회합니다.
        
        Args:
            folder_id: 조회할 폴더 ID
        
        Returns:
            파일 정보 딕셔너리 리스트
        """
        query = f"'{folder_id}' in parents and trashed=false"
        
        try:
            results = self.service.files().list(
                q=query,
                fields="files(id, name, modifiedTime, size)",
                pageSize=100,
                orderBy="modifiedTime desc"
            ).execute()
            
            return results.get('files', [])
        except Exception as e:
            self.logger.error(f"  ❌ 파일 목록 조회 실패: {e}")
            return []
