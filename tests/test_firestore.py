'''
Firestoreリポジトリのテスト
'''

import pytest
from datetime import datetime, timezone
from app.models.subscription import UserSubscription


@pytest.mark.asyncio
async def test_create_or_update_new_document(user_subscription_repository, sample_subscription_data, sample_cuid):
    '''新規ドキュメント作成のテスト'''
    # UserSubscriptionモデルを作成
    subscription = UserSubscription(**sample_subscription_data)

    # リポジトリでドキュメント作成
    result = await user_subscription_repository.create_or_update(
        sample_cuid,
        subscription.to_dict()
    )

    # 結果の検証
    assert result is not None
    assert result['stripe_customer_id'] == sample_subscription_data['stripe_customer_id']
    assert result['plan_name'] == sample_subscription_data['plan_name']
    assert result['subscription_status'] == sample_subscription_data['subscription_status']
    assert 'created' in result
    assert 'updated' in result


def test_get_by_cuid(user_subscription_repository, sample_subscription_data, sample_cuid):
    '''CUIDでのドキュメント取得テスト'''
    # まずドキュメントを作成（同期的に実行）
    subscription = UserSubscription(**sample_subscription_data)
    doc_ref = user_subscription_repository.collection.document(sample_cuid)
    doc_ref.set(subscription.to_dict())

    # CUIDで取得
    result = user_subscription_repository.get_by_cuid(sample_cuid)

    # 結果の検証
    assert result is not None
    assert result['id'] == sample_cuid
    assert result['stripe_customer_id'] == sample_subscription_data['stripe_customer_id']
    assert result['plan_name'] == sample_subscription_data['plan_name']


def test_get_by_cuid_not_found(user_subscription_repository):
    '''存在しないCUIDでの取得テスト'''
    result = user_subscription_repository.get_by_cuid('non_existent_cuid')
    assert result is None


def test_get_by_stripe_customer_id(user_subscription_repository, sample_subscription_data, sample_cuid):
    '''Stripe顧客IDでのドキュメント取得テスト'''
    # ドキュメントを作成
    subscription = UserSubscription(**sample_subscription_data)
    doc_ref = user_subscription_repository.collection.document(sample_cuid)
    doc_ref.set(subscription.to_dict())

    # Stripe顧客IDで取得
    result = user_subscription_repository.get_by_stripe_customer_id(
        sample_subscription_data['stripe_customer_id']
    )

    # 結果の検証
    assert result is not None
    assert result['id'] == sample_cuid
    assert result['stripe_customer_id'] == sample_subscription_data['stripe_customer_id']


def test_update_status(user_subscription_repository, sample_subscription_data, sample_cuid):
    '''ステータス更新テスト'''
    # ドキュメントを作成
    subscription = UserSubscription(**sample_subscription_data)
    doc_ref = user_subscription_repository.collection.document(sample_cuid)
    doc_ref.set(subscription.to_dict())

    # ステータス更新
    new_status = 'canceled'
    success = user_subscription_repository.update_status(sample_cuid, new_status)

    # 更新成功を確認
    assert success is True

    # 更新されたドキュメントを取得して確認
    updated_doc = user_subscription_repository.get_by_cuid(sample_cuid)
    assert updated_doc['subscription_status'] == new_status
    assert 'updated' in updated_doc


def test_update_status_not_found(user_subscription_repository):
    '''存在しないドキュメントのステータス更新テスト'''
    success = user_subscription_repository.update_status('non_existent_cuid', 'canceled')
    assert success is False


def test_delete(user_subscription_repository, sample_subscription_data, sample_cuid):
    '''ドキュメント削除テスト'''
    # ドキュメントを作成
    subscription = UserSubscription(**sample_subscription_data)
    doc_ref = user_subscription_repository.collection.document(sample_cuid)
    doc_ref.set(subscription.to_dict())

    # 削除
    success = user_subscription_repository.delete(sample_cuid)
    assert success is True

    # 削除されたことを確認
    result = user_subscription_repository.get_by_cuid(sample_cuid)
    assert result is None


def test_delete_non_existent(user_subscription_repository):
    '''存在しないドキュメントの削除テスト'''
    # 存在しないドキュメントを削除しても例外が発生しないことを確認
    success = user_subscription_repository.delete('non_existent_cuid')
    assert success is True  # Firestoreは存在しないドキュメントの削除も成功とする