'''
CalilWeb API クライアントのテスト

CalilWebAPIClientクラスの各メソッドをテストする。
モックを使用してネットワーク通信を行わずにテストを実行。
'''

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import httpx
from app.infrastructure.calil_web_api import (
    CalilWebAPIClient,
    UserInfo,
    UpdatePlanResponse,
    CalilWebAPIError
)


@pytest.fixture
def mock_id_token():
    '''IDトークンのモック'''
    return 'mock_id_token_12345'


@pytest.fixture
def mock_credentials():
    '''Google認証情報のモック'''
    with patch('app.infrastructure.calil_web_api.google.auth.default') as mock_auth:
        mock_auth.return_value = (Mock(), 'test-project')
        yield mock_auth


@pytest.fixture
def mock_fetch_id_token(mock_id_token):
    '''IDトークン取得のモック'''
    with patch('app.infrastructure.calil_web_api.id_token.fetch_id_token') as mock_fetch:
        mock_fetch.return_value = mock_id_token
        yield mock_fetch


@pytest.fixture
def client(mock_credentials, mock_fetch_id_token):
    '''CalilWebAPIClientのインスタンス（モック済み）'''
    return CalilWebAPIClient(
        audience='https://test.appspot.com',
        base_url='https://test.api.com',
        timeout=10.0
    )


@pytest.fixture
def user_info_response():
    '''ユーザー情報の正常レスポンス'''
    return {
        'stat': 'ok',
        'userkey': 'calil:test123',
        'cuid': '1234567890',
        'email': 'test@example.com',
        'nickname': 'テストユーザー',
        'fill_profile': 1,
        'profile': 'テストプロフィール',
        'thumbnail_url': '/profile/pics/test.jpg',
        'newsletter': 1,
        'service': 'google',
        'plan_id': 'Basic',
        'date': '2023-01-01 00:00:00.000000',
        'update': '2023-10-01 00:00:00.000000',
        'requested_by': 'service-account@test.iam.gserviceaccount.com'
    }


@pytest.fixture
def update_plan_response():
    '''プラン更新の正常レスポンス'''
    return {
        'success': True,
        'cuid': '1234567890',
        'plan_id': 'Standard',
        'updated_by': 'service-account@test.iam.gserviceaccount.com'
    }


class TestUserInfoModel:
    '''UserInfoモデルのテスト'''

    def test_valid_user_info(self, user_info_response):
        '''正常なユーザー情報の検証'''
        user_info = UserInfo(**user_info_response)
        assert user_info.cuid == '1234567890'
        assert user_info.email == 'test@example.com'
        assert user_info.plan_id == 'Basic'

    def test_empty_plan_id(self, user_info_response):
        '''プランID未設定の場合'''
        user_info_response['plan_id'] = ''
        user_info = UserInfo(**user_info_response)
        assert user_info.plan_id == ''

    def test_invalid_plan_id(self, user_info_response):
        '''不正なプランIDの検証'''
        user_info_response['plan_id'] = 'Invalid'
        with pytest.raises(ValueError, match='Invalid plan_id'):
            UserInfo(**user_info_response)


class TestCalilWebAPIClient:
    '''CalilWebAPIClientのテスト'''

    @pytest.mark.asyncio
    async def test_get_user_info_success(self, client, user_info_response, mock_id_token):
        '''ユーザー情報取得の成功ケース'''
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value=user_info_response)
        mock_response.raise_for_status = Mock()

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance

            user_info = await client.get_user_info('test_session_token')

            # APIが正しく呼ばれたか確認
            mock_instance.post.assert_called_once_with(
                'https://test.api.com/get_userstat_v2',
                headers={
                    'Authorization': f'Bearer {mock_id_token}',
                    'Content-Type': 'application/json'
                },
                json={'session_v2': 'test_session_token'}
            )

            # レスポンスの検証
            assert user_info.cuid == '1234567890'
            assert user_info.email == 'test@example.com'
            assert user_info.plan_id == 'Basic'

    @pytest.mark.asyncio
    async def test_get_user_info_no_session(self, client):
        '''セッショントークンが空の場合'''
        with pytest.raises(CalilWebAPIError) as exc_info:
            await client.get_user_info('')

        assert exc_info.value.status_code == 400
        assert 'session_v2 is required' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_user_info_user_not_found(self, client, mock_id_token):
        '''ユーザーが見つからない場合'''
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json = Mock(return_value={'stat': 'nouser'})

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance

            with pytest.raises(CalilWebAPIError) as exc_info:
                await client.get_user_info('invalid_session')

            assert exc_info.value.status_code == 404
            assert 'User not logged in' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_user_info_http_error(self, client, mock_id_token):
        '''HTTPエラーの場合'''
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_response.json = Mock(return_value={'error': 'server error'})
        mock_response.raise_for_status = Mock(side_effect=httpx.HTTPStatusError(
            message='500 Internal Server Error',
            request=Mock(),
            response=mock_response
        ))

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance

            with pytest.raises(CalilWebAPIError) as exc_info:
                await client.get_user_info('test_session')

            assert exc_info.value.status_code == 500
            assert 'HTTP error occurred' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_user_plan_success(self, client, update_plan_response, mock_id_token):
        '''プラン更新の成功ケース'''
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value=update_plan_response)
        mock_response.raise_for_status = Mock()

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance

            result = await client.update_user_plan('1234567890', 'Standard')

            # APIが正しく呼ばれたか確認
            mock_instance.post.assert_called_once_with(
                'https://test.api.com/update_user_plan',
                headers={
                    'Authorization': f'Bearer {mock_id_token}',
                    'Content-Type': 'application/json'
                },
                json={'cuid': '1234567890', 'plan_id': 'Standard'}
            )

            # レスポンスの検証
            assert result.success is True
            assert result.cuid == '1234567890'
            assert result.plan_id == 'Standard'

    @pytest.mark.asyncio
    async def test_update_user_plan_invalid_plan_id(self, client):
        '''不正なプランIDの場合'''
        with pytest.raises(CalilWebAPIError) as exc_info:
            await client.update_user_plan('1234567890', 'InvalidPlan')

        assert exc_info.value.status_code == 400
        assert 'Invalid plan_id' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_user_plan_empty_cuid(self, client):
        '''CUIDが空の場合'''
        with pytest.raises(CalilWebAPIError) as exc_info:
            await client.update_user_plan('', 'Basic')

        assert exc_info.value.status_code == 400
        assert 'cuid is required' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_user_plan_user_not_found(self, client, mock_id_token):
        '''ユーザーが見つからない場合'''
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json = Mock(return_value={'error': 'User not found'})
        mock_response.raise_for_status = Mock()

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance

            with pytest.raises(CalilWebAPIError) as exc_info:
                await client.update_user_plan('9999999999', 'Basic')

            assert exc_info.value.status_code == 404
            assert 'User with cuid' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_network_error(self, client, mock_id_token):
        '''ネットワークエラーの場合'''
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.side_effect = httpx.RequestError('Connection refused')
            mock_client.return_value.__aenter__.return_value = mock_instance

            with pytest.raises(CalilWebAPIError) as exc_info:
                await client.get_user_info('test_session')

            assert exc_info.value.status_code == 500
            assert 'Request failed' in str(exc_info.value)

    def test_get_user_info_sync(self, client, user_info_response, mock_id_token):
        '''同期版メソッドのテスト'''
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value=user_info_response)
        mock_response.raise_for_status = Mock()

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance

            user_info = client.get_user_info_sync('test_session_token')

            assert user_info.cuid == '1234567890'
            assert user_info.email == 'test@example.com'

    def test_update_user_plan_sync(self, client, update_plan_response, mock_id_token):
        '''同期版メソッドのテスト'''
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value=update_plan_response)
        mock_response.raise_for_status = Mock()

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance

            result = client.update_user_plan_sync('1234567890', 'Standard')

            assert result.success is True
            assert result.plan_id == 'Standard'


class TestCalilWebAPIError:
    '''CalilWebAPIErrorのテスト'''

    def test_error_with_detail(self):
        '''詳細情報付きエラー'''
        error = CalilWebAPIError(
            status_code=400,
            message='Bad Request',
            detail={'field': 'plan_id', 'error': 'invalid'}
        )
        assert error.status_code == 400
        assert error.message == 'Bad Request'
        assert error.detail['field'] == 'plan_id'
        assert '[400] Bad Request' in str(error)

    def test_error_without_detail(self):
        '''詳細情報なしエラー'''
        error = CalilWebAPIError(
            status_code=500,
            message='Internal Server Error'
        )
        assert error.status_code == 500
        assert error.detail is None


class TestIDTokenCaching:
    '''IDトークンのキャッシュ機能のテスト'''

    def test_credentials_cache(self, mock_credentials):
        '''認証情報のキャッシュが効いているか確認'''
        client = CalilWebAPIClient()

        # 2回呼び出しても、実際の認証は1回のみ
        creds1 = client._get_credentials()
        creds2 = client._get_credentials()

        assert mock_credentials.call_count == 1
        assert creds1 == creds2

    def test_id_token_error_handling(self):
        '''IDトークン取得エラーのハンドリング'''
        with patch('app.infrastructure.calil_web_api.id_token.fetch_id_token') as mock_fetch:
            mock_fetch.side_effect = Exception('Auth failed')

            client = CalilWebAPIClient()
            with pytest.raises(CalilWebAPIError) as exc_info:
                client._get_id_token()

            assert exc_info.value.status_code == 401
            assert 'Failed to get ID token' in str(exc_info.value)