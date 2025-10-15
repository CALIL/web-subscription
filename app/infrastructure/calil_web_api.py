'''
CalilWeb API (IAM認証) クライアントライブラリ

カーリルのCalilWeb APIと通信するためのクライアント実装。
Google IAM認証を使用してセキュアな通信を行う。
'''

import asyncio
from typing import Optional, Dict, Any
from functools import lru_cache
import httpx
from google.auth.transport.requests import Request
from google.oauth2 import id_token
import google.auth
from pydantic import BaseModel, Field, field_validator


class UserInfo(BaseModel):
    '''ユーザー情報のレスポンスモデル'''
    stat: str
    userkey: Optional[str] = None
    cuid: str
    email: str
    nickname: str
    fill_profile: Optional[int] = None
    profile: Optional[str] = None
    thumbnail_url: Optional[str] = None
    newsletter: Optional[int] = None
    service: str
    plan_id: str = ''  # 未契約時は空文字
    date: str
    update: str
    requested_by: Optional[str] = None

    @field_validator('plan_id')
    @classmethod
    def validate_plan_id(cls, v):
        '''プランIDの妥当性チェック'''
        valid_plans = ['', 'Basic', 'Standard', 'Pro']
        if v not in valid_plans:
            raise ValueError(f'Invalid plan_id: {v}')
        return v


class UpdatePlanResponse(BaseModel):
    '''プラン更新のレスポンスモデル'''
    success: bool
    cuid: str
    plan_id: str
    updated_by: str


class CalilWebAPIError(Exception):
    '''CalilWeb API関連のエラー'''
    def __init__(self, status_code: int, message: str, detail: Optional[Dict] = None):
        self.status_code = status_code
        self.message = message
        self.detail = detail
        super().__init__(f'[{status_code}] {message}')


class CalilWebAPIClient:
    '''CalilWeb API (IAM認証) クライアント'''

    def __init__(
        self,
        audience: str = 'https://libmuteki2.appspot.com',
        base_url: str = 'https://calil.jp/infrastructure',
        timeout: float = 30.0
    ):
        '''
        Args:
            audience: IAM認証のAudience (CalilWebのApp Engine URL)
            base_url: CalilWeb APIのベースURL
            timeout: HTTPリクエストのタイムアウト秒数
        '''
        self.audience = audience
        self.base_url = base_url
        self.timeout = timeout
        self._id_token_cache = None
        self._token_expiry = None

    @lru_cache(maxsize=1)
    def _get_credentials(self):
        '''Google認証情報の取得（キャッシュあり）'''
        return google.auth.default()

    def _get_id_token(self) -> str:
        '''
        Google IAM IDトークンの取得

        Returns:
            IDトークン文字列

        Raises:
            CalilWebAPIError: 認証に失敗した場合
        '''
        try:
            credentials, project = self._get_credentials()
            auth_req = Request()
            token = id_token.fetch_id_token(auth_req, self.audience)
            return token
        except Exception as e:
            raise CalilWebAPIError(
                status_code=401,
                message=f'Failed to get ID token: {str(e)}'
            )

    async def get_user_info(self, session_v2: str) -> UserInfo:
        '''
        セッションキーからユーザー情報を取得

        Args:
            session_v2: JWTセッショントークン (Cookieから取得)

        Returns:
            UserInfo: ユーザー情報

        Raises:
            CalilWebAPIError: APIエラーが発生した場合
        '''
        if not session_v2:
            raise CalilWebAPIError(
                status_code=400,
                message='session_v2 is required'
            )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f'{self.base_url}/get_userstat_v2',
                    headers={
                        'Authorization': f'Bearer {self._get_id_token()}',
                        'Content-Type': 'application/json'
                    },
                    json={'session_v2': session_v2}
                )

                if response.status_code == 404:
                    # ユーザー未ログインまたはデータなし
                    data = response.json()
                    if data.get('stat') == 'nouser':
                        raise CalilWebAPIError(
                            status_code=404,
                            message='User not logged in or user data not found',
                            detail=data
                        )

                response.raise_for_status()
                return UserInfo(**response.json())

        except httpx.HTTPStatusError as e:
            # HTTPステータスエラーをCalilWebAPIErrorに変換
            raise CalilWebAPIError(
                status_code=e.response.status_code,
                message=f'HTTP error occurred: {e.response.text}',
                detail=e.response.json() if e.response.text else None
            )
        except httpx.RequestError as e:
            # ネットワークエラーなど
            raise CalilWebAPIError(
                status_code=500,
                message=f'Request failed: {str(e)}'
            )
        except Exception as e:
            if isinstance(e, CalilWebAPIError):
                raise
            raise CalilWebAPIError(
                status_code=500,
                message=f'Unexpected error: {str(e)}'
            )

    async def update_user_plan(self, cuid: str, plan_id: str) -> UpdatePlanResponse:
        '''
        ユーザーのプランを更新

        Args:
            cuid: ユーザーID
            plan_id: プランID ('Basic', 'Standard', 'Pro', または空文字)

        Returns:
            UpdatePlanResponse: 更新結果

        Raises:
            CalilWebAPIError: APIエラーが発生した場合
        '''
        if not cuid:
            raise CalilWebAPIError(
                status_code=400,
                message='cuid is required'
            )

        valid_plans = ['', 'Basic', 'Standard', 'Pro']
        if plan_id not in valid_plans:
            raise CalilWebAPIError(
                status_code=400,
                message=f'Invalid plan_id: {plan_id}. Must be one of {valid_plans}'
            )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f'{self.base_url}/update_user_plan',
                    headers={
                        'Authorization': f'Bearer {self._get_id_token()}',
                        'Content-Type': 'application/json'
                    },
                    json={'cuid': cuid, 'plan_id': plan_id}
                )

                if response.status_code == 404:
                    raise CalilWebAPIError(
                        status_code=404,
                        message=f'User with cuid \'{cuid}\' not found'
                    )

                response.raise_for_status()
                return UpdatePlanResponse(**response.json())

        except httpx.HTTPStatusError as e:
            raise CalilWebAPIError(
                status_code=e.response.status_code,
                message=f'HTTP error occurred: {e.response.text}',
                detail=e.response.json() if e.response.text else None
            )
        except httpx.RequestError as e:
            raise CalilWebAPIError(
                status_code=500,
                message=f'Request failed: {str(e)}'
            )
        except Exception as e:
            if isinstance(e, CalilWebAPIError):
                raise
            raise CalilWebAPIError(
                status_code=500,
                message=f'Unexpected error: {str(e)}'
            )

    def get_user_info_sync(self, session_v2: str) -> UserInfo:
        '''
        同期版: セッションキーからユーザー情報を取得

        Args:
            session_v2: JWTセッショントークン

        Returns:
            UserInfo: ユーザー情報
        '''
        return asyncio.run(self.get_user_info(session_v2))

    def update_user_plan_sync(self, cuid: str, plan_id: str) -> UpdatePlanResponse:
        '''
        同期版: ユーザーのプランを更新

        Args:
            cuid: ユーザーID
            plan_id: プランID

        Returns:
            UpdatePlanResponse: 更新結果
        '''
        return asyncio.run(self.update_user_plan(cuid, plan_id))