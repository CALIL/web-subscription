'''
Firestore接続モジュール

Google Cloud Firestoreへの接続を管理。
開発環境ではモックを使用可能。
'''

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from google.cloud import firestore
from google.api_core import exceptions
from app.config.settings import settings


class FirestoreClient:
    '''Firestoreクライアント'''

    def __init__(self, mock_client=None):
        '''
        初期化

        Args:
            mock_client: テスト用のモッククライアント（オプション）
        '''
        if mock_client is not None:
            # テスト時に明示的にモッククライアントが渡された場合
            self.db = mock_client
        elif settings.use_mock_firestore:
            # 環境変数でモック使用が指定されている場合
            # テスト実行時はconftest.pyなどでモックを注入することを推奨
            raise ValueError(
                'USE_MOCK_FIRESTORE is true, but mock client is not provided. '
                'Please inject mock client in tests or set USE_MOCK_FIRESTORE=false'
            )
        else:
            # 実際のFirestoreに接続
            self.db = firestore.Client(project=settings.google_cloud_project)

    def get_collection(self, collection_name: str):
        '''コレクションの取得'''
        return self.db.collection(collection_name)


class UserSubscriptionRepository:
    '''UserSubscriptionのリポジトリ'''

    COLLECTION_NAME = 'user_subscriptions'

    def __init__(self, mock_client=None):
        '''初期化

        Args:
            mock_client: テスト用のモッククライアント（オプション）
        '''
        self.client = FirestoreClient(mock_client=mock_client)
        self.collection = self.client.get_collection(self.COLLECTION_NAME)

    async def create_or_update(self, cuid: str, data: Dict[str, Any]) -> Dict[str, Any]:
        '''
        ユーザーサブスクリプションの作成または更新

        Args:
            cuid: ユーザーID（ドキュメントIDとして使用）
            data: 保存するデータ

        Returns:
            保存されたデータ（タイムスタンプを含む）
        '''
        # タイムスタンプを追加
        now = datetime.now(timezone.utc)
        doc_ref = self.collection.document(cuid)

        # 既存ドキュメントの確認
        doc = doc_ref.get()

        if doc.exists:
            # 更新
            data['updated'] = now
            doc_ref.update(data)
        else:
            # 新規作成
            data['created'] = now
            data['updated'] = now
            doc_ref.set(data)

        # 保存後のデータを返す
        return self.get_by_cuid(cuid)

    def get_by_cuid(self, cuid: str) -> Optional[Dict[str, Any]]:
        '''
        CUIDでユーザーサブスクリプションを取得

        Args:
            cuid: ユーザーID

        Returns:
            サブスクリプションデータ、存在しない場合はNone
        '''
        doc_ref = self.collection.document(cuid)
        doc = doc_ref.get()

        if doc.exists:
            data = doc.to_dict()
            data['id'] = doc.id  # ドキュメントID（CUID）を含める
            return data
        return None

    def get_by_stripe_customer_id(self, customer_id: str) -> Optional[Dict[str, Any]]:
        '''
        Stripe顧客IDでユーザーサブスクリプションを取得

        Args:
            customer_id: Stripe顧客ID

        Returns:
            サブスクリプションデータ、存在しない場合はNone
        '''
        # Stripe顧客IDでクエリ
        query = self.collection.where('stripe_customer_id', '==', customer_id).limit(1)
        docs = query.get()

        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id  # ドキュメントID（CUID）を含める
            return data

        return None

    def delete(self, cuid: str) -> bool:
        '''
        ユーザーサブスクリプションを削除

        Args:
            cuid: ユーザーID

        Returns:
            削除成功の場合True
        '''
        try:
            doc_ref = self.collection.document(cuid)
            doc_ref.delete()
            return True
        except Exception:
            return False

    def update_status(self, cuid: str, status: str) -> bool:
        '''
        サブスクリプションステータスを更新

        Args:
            cuid: ユーザーID
            status: 新しいステータス

        Returns:
            更新成功の場合True
        '''
        try:
            doc_ref = self.collection.document(cuid)
            doc_ref.update({
                'subscription_status': status,
                'updated': datetime.now(timezone.utc)
            })
            return True
        except exceptions.NotFound:
            return False