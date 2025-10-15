'''
pytestの共通設定とフィクスチャ

すべてのテストで使用する共通のフィクスチャと設定を定義。
'''

import pytest
import asyncio
from typing import Generator
import os
import sys
from datetime import datetime, timezone

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# テスト実行時はモック使用フラグを無効化（個別にモックを注入）
os.environ['USE_MOCK_FIRESTORE'] = 'false'


@pytest.fixture(scope='session')
def event_loop() -> Generator:
    '''
    非同期テスト用のイベントループを提供

    セッションスコープで1つのイベントループを使い回す
    '''
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def reset_environment():
    '''
    各テストの前後で環境変数をリセット

    テスト間で環境変数の影響を防ぐ
    '''
    original_env = os.environ.copy()
    # USE_MOCK_FIRESTOREは常にfalse
    os.environ['USE_MOCK_FIRESTORE'] = 'false'
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_google_auth_environment():
    '''
    Google認証環境のモック

    実際のGoogle認証を行わずにテストできるようにする
    '''
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/path/to/fake/credentials.json'
    os.environ['GOOGLE_CLOUD_PROJECT'] = 'test-project'
    yield
    if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
        del os.environ['GOOGLE_APPLICATION_CREDENTIALS']
    if 'GOOGLE_CLOUD_PROJECT' in os.environ:
        del os.environ['GOOGLE_CLOUD_PROJECT']


@pytest.fixture
def mock_firestore_client():
    '''MockFirestoreClientのフィクスチャ'''
    from tests.firestore_mock import MockFirestoreClient
    return MockFirestoreClient()


@pytest.fixture
def user_subscription_repository(mock_firestore_client):
    '''UserSubscriptionRepositoryのフィクスチャ（モック使用）'''
    from app.infrastructure.firestore import UserSubscriptionRepository
    return UserSubscriptionRepository(mock_client=mock_firestore_client)


@pytest.fixture
def sample_subscription_data():
    '''テスト用のサブスクリプションデータ'''
    return {
        'stripe_customer_id': 'cus_test123',
        'stripe_subscription_id': 'sub_test123',
        'stripe_price_id': 'price_test123',
        'plan_name': 'Basic',
        'plan_amount': 1000,
        'subscription_status': 'active',
        'current_period_end': datetime(2025, 11, 15, 0, 0, 0, tzinfo=timezone.utc),
    }


@pytest.fixture
def sample_cuid():
    '''テスト用のCUID'''
    return '4754259718'