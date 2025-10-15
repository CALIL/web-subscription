"""
pytestの共通設定とフィクスチャ

すべてのテストで使用する共通のフィクスチャと設定を定義。
"""

import pytest
import asyncio
from typing import Generator
import os
import sys

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """
    非同期テスト用のイベントループを提供

    セッションスコープで1つのイベントループを使い回す
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def reset_environment():
    """
    各テストの前後で環境変数をリセット

    テスト間で環境変数の影響を防ぐ
    """
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_google_auth_environment():
    """
    Google認証環境のモック

    実際のGoogle認証を行わずにテストできるようにする
    """
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/path/to/fake/credentials.json'
    os.environ['GOOGLE_CLOUD_PROJECT'] = 'test-project'
    yield
    if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
        del os.environ['GOOGLE_APPLICATION_CREDENTIALS']
    if 'GOOGLE_CLOUD_PROJECT' in os.environ:
        del os.environ['GOOGLE_CLOUD_PROJECT']