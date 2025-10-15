'''
サブスクリプションモデル

ユーザーのサブスクリプション情報を管理するモデル。
'''

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class PlanName(str, Enum):
    '''プラン名の列挙型'''
    BASIC = 'Basic'
    STANDARD = 'Standard'
    PRO = 'Pro'


class SubscriptionStatus(str, Enum):
    '''サブスクリプションステータスの列挙型'''
    ACTIVE = 'active'
    CANCELED = 'canceled'
    PAST_DUE = 'past_due'
    UNPAID = 'unpaid'
    INCOMPLETE = 'incomplete'
    INCOMPLETE_EXPIRED = 'incomplete_expired'
    TRIALING = 'trialing'


class UserSubscription(BaseModel):
    '''ユーザーサブスクリプションモデル'''

    # Stripe情報
    stripe_customer_id: str = Field(..., description='Stripe顧客ID')
    stripe_subscription_id: str = Field(..., description='StripeサブスクリプションID')
    stripe_price_id: str = Field(..., description='Stripe価格ID')

    # サブスクリプション情報
    plan_name: PlanName = Field(..., description='プラン名')
    plan_amount: int = Field(..., description='プラン金額（円）')
    subscription_status: SubscriptionStatus = Field(..., description='サブスクリプションステータス')
    current_period_end: datetime = Field(..., description='現在の請求期間終了日')

    # メタ情報
    created: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description='作成日時')
    updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description='更新日時')

    @field_validator('plan_amount')
    @classmethod
    def validate_plan_amount(cls, v: int) -> int:
        '''プラン金額の妥当性チェック'''
        valid_amounts = [1000, 2000, 5000]
        if v not in valid_amounts:
            raise ValueError(f'Invalid plan amount: {v}. Must be one of {valid_amounts}')
        return v

    def to_dict(self) -> dict:
        '''辞書形式に変換（Firestore保存用）'''
        data = self.model_dump()
        # datetimeをFirestoreが扱える形式に変換
        for key in ['current_period_end', 'created', 'updated']:
            if key in data and isinstance(data[key], datetime):
                data[key] = data[key]
        # Enumを文字列に変換
        data['plan_name'] = data['plan_name'].value if isinstance(data['plan_name'], Enum) else data['plan_name']
        data['subscription_status'] = data['subscription_status'].value if isinstance(data['subscription_status'], Enum) else data['subscription_status']
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'UserSubscription':
        '''辞書形式から生成'''
        # 必要に応じてデータを変換
        if 'plan_name' in data and isinstance(data['plan_name'], str):
            data['plan_name'] = PlanName(data['plan_name'])
        if 'subscription_status' in data and isinstance(data['subscription_status'], str):
            data['subscription_status'] = SubscriptionStatus(data['subscription_status'])
        return cls(**data)


class CreateCheckoutSessionRequest(BaseModel):
    '''Checkout Session作成リクエスト'''
    plan_name: PlanName = Field(..., description='購入するプラン名')


class CreateCheckoutSessionResponse(BaseModel):
    '''Checkout Session作成レスポンス'''
    checkout_url: str = Field(..., description='Stripeチェックアウト画面のURL')
    session_id: str = Field(..., description='Checkout SessionのID')


class CreatePortalSessionRequest(BaseModel):
    '''Portal Session作成リクエスト'''
    # CUIDはセッションから取得するため、リクエストボディには含まない
    pass


class CreatePortalSessionResponse(BaseModel):
    '''Portal Session作成レスポンス'''
    portal_url: str = Field(..., description='Customer PortalのURL')


class SubscriptionInfo(BaseModel):
    '''サブスクリプション情報（API返却用）'''
    cuid: str = Field(..., description='ユーザーID')
    plan_name: Optional[str] = Field(None, description='プラン名')
    plan_amount: Optional[int] = Field(None, description='プラン金額')
    subscription_status: Optional[str] = Field(None, description='ステータス')
    current_period_end: Optional[datetime] = Field(None, description='現在の請求期間終了日')
    is_active: bool = Field(default=False, description='アクティブかどうか')

    @classmethod
    def from_subscription(cls, cuid: str, subscription: Optional[UserSubscription]) -> 'SubscriptionInfo':
        '''UserSubscriptionから生成'''
        if subscription:
            return cls(
                cuid=cuid,
                plan_name=subscription.plan_name.value,
                plan_amount=subscription.plan_amount,
                subscription_status=subscription.subscription_status.value,
                current_period_end=subscription.current_period_end,
                is_active=subscription.subscription_status == SubscriptionStatus.ACTIVE
            )
        else:
            return cls(cuid=cuid, is_active=False)