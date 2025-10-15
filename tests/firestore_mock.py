'''
Firestoreモック実装

開発・テスト環境で使用するFirestoreのモック。
実際のFirestoreと同じインターフェースを提供。
'''

from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid


class MockDocument:
    '''モックドキュメント'''

    def __init__(self, doc_id: str, data: Dict[str, Any] = None):
        '''初期化'''
        self.id = doc_id
        self._data = data or {}
        self._exists = data is not None

    @property
    def exists(self) -> bool:
        '''ドキュメントが存在するか'''
        return self._exists

    def to_dict(self) -> Dict[str, Any]:
        '''ドキュメントデータを辞書として取得'''
        return self._data.copy() if self._exists else None

    def get(self):
        '''ドキュメントを取得（自身を返す）'''
        return self


class MockDocumentReference:
    '''モックドキュメントリファレンス'''

    def __init__(self, collection, doc_id: str):
        '''初期化'''
        self.collection = collection
        self.id = doc_id

    def get(self) -> MockDocument:
        '''ドキュメントを取得'''
        data = self.collection._get_document(self.id)
        return MockDocument(self.id, data)

    def set(self, data: Dict[str, Any], merge: bool = False):
        '''ドキュメントを設定'''
        self.collection._set_document(self.id, data, merge)

    def update(self, data: Dict[str, Any]):
        '''ドキュメントを更新'''
        self.collection._update_document(self.id, data)

    def delete(self):
        '''ドキュメントを削除'''
        self.collection._delete_document(self.id)


class MockQuery:
    '''モッククエリ'''

    def __init__(self, collection, filters: List = None):
        '''初期化'''
        self.collection = collection
        self.filters = filters or []
        self._limit_count = None

    def where(self, field: str, operator: str, value: Any):
        '''フィルタ条件を追加'''
        new_filters = self.filters.copy()
        new_filters.append((field, operator, value))
        return MockQuery(self.collection, new_filters)

    def limit(self, count: int):
        '''結果数を制限'''
        query = MockQuery(self.collection, self.filters)
        query._limit_count = count
        return query

    def get(self) -> List[MockDocument]:
        '''クエリを実行してドキュメントを取得'''
        results = []
        for doc_id, doc_data in self.collection._documents.items():
            if self._matches_filters(doc_data):
                results.append(MockDocument(doc_id, doc_data))
                if self._limit_count and len(results) >= self._limit_count:
                    break
        return results

    def _matches_filters(self, doc_data: Dict[str, Any]) -> bool:
        '''フィルタ条件にマッチするか確認'''
        for field, operator, value in self.filters:
            doc_value = doc_data.get(field)

            if operator == '==':
                if doc_value != value:
                    return False
            elif operator == '!=':
                if doc_value == value:
                    return False
            elif operator == '>':
                if doc_value <= value:
                    return False
            elif operator == '>=':
                if doc_value < value:
                    return False
            elif operator == '<':
                if doc_value >= value:
                    return False
            elif operator == '<=':
                if doc_value > value:
                    return False
            # 他の演算子は必要に応じて追加

        return True


class MockCollection:
    '''モックコレクション'''

    def __init__(self, name: str):
        '''初期化'''
        self.name = name
        self._documents = {}

    def document(self, doc_id: str = None) -> MockDocumentReference:
        '''ドキュメントリファレンスを取得'''
        if doc_id is None:
            doc_id = str(uuid.uuid4())
        return MockDocumentReference(self, doc_id)

    def where(self, field: str, operator: str, value: Any) -> MockQuery:
        '''クエリを作成'''
        return MockQuery(self).where(field, operator, value)

    def _get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        '''内部: ドキュメントを取得'''
        return self._documents.get(doc_id)

    def _set_document(self, doc_id: str, data: Dict[str, Any], merge: bool = False):
        '''内部: ドキュメントを設定'''
        if merge and doc_id in self._documents:
            self._documents[doc_id].update(data)
        else:
            self._documents[doc_id] = data.copy()

    def _update_document(self, doc_id: str, data: Dict[str, Any]):
        '''内部: ドキュメントを更新'''
        if doc_id in self._documents:
            self._documents[doc_id].update(data)
        else:
            raise Exception(f'Document {doc_id} not found')

    def _delete_document(self, doc_id: str):
        '''内部: ドキュメントを削除'''
        if doc_id in self._documents:
            del self._documents[doc_id]


class MockFirestoreClient:
    '''モックFirestoreクライアント'''

    def __init__(self):
        '''初期化'''
        self._collections = {}

    def collection(self, name: str) -> MockCollection:
        '''コレクションを取得'''
        if name not in self._collections:
            self._collections[name] = MockCollection(name)
        return self._collections[name]

    def clear(self):
        '''全データをクリア（テスト用）'''
        self._collections.clear()