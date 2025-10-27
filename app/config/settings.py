'''
環境設定モジュール

環境変数から設定を読み込み、アプリケーション全体で使用する設定を管理。
'''

import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()


class Settings(BaseSettings):
    '''アプリケーション設定'''

    # 環境設定
    app_env: str = os.getenv('APP_ENV', 'development')

    # Google Cloud設定
    google_cloud_project: Optional[str] = os.getenv('GOOGLE_CLOUD_PROJECT')
    use_mock_firestore: bool = os.getenv('USE_MOCK_FIRESTORE', 'false').lower() == 'true'
    firestore_database_name: str = os.getenv('FIRESTORE_DATABASE_NAME', '(default)')

    # CalilWeb API設定
    calil_web_audience: str = os.getenv('CALIL_WEB_AUDIENCE', 'https://libmuteki2.appspot.com')
    calil_web_base_url: str = os.getenv('CALIL_WEB_BASE_URL', 'https://calil.jp/infrastructure')

    # Stripe設定
    stripe_secret_key: str = os.getenv('STRIPE_SECRET_KEY', '')
    stripe_publishable_key: str = os.getenv('STRIPE_PUBLISHABLE_KEY', '')
    stripe_webhook_secret: str = os.getenv('STRIPE_WEBHOOK_SECRET', '')

    # Stripe価格ID
    stripe_price_id_basic: str = os.getenv('STRIPE_PRICE_ID_BASIC', '')
    stripe_price_id_standard: str = os.getenv('STRIPE_PRICE_ID_STANDARD', '')
    stripe_price_id_pro: str = os.getenv('STRIPE_PRICE_ID_PRO', '')

    # SendGrid設定
    sendgrid_api_key: str = os.getenv('SENDGRID_API_KEY', '')
    sendgrid_from_email: str = os.getenv('SENDGRID_FROM_EMAIL', '')
    sendgrid_from_name: str = os.getenv('SENDGRID_FROM_NAME', '')

    # SendGridテンプレートID
    sendgrid_template_id_subscription_new: str = os.getenv('SENDGRID_TEMPLATE_ID_SUBSCRIPTION_NEW', '')
    sendgrid_template_id_subscription_upgrade: str = os.getenv('SENDGRID_TEMPLATE_ID_SUBSCRIPTION_UPGRADE', '')
    sendgrid_template_id_subscription_downgrade: str = os.getenv('SENDGRID_TEMPLATE_ID_SUBSCRIPTION_DOWNGRADE', '')
    sendgrid_template_id_subscription_canceled: str = os.getenv('SENDGRID_TEMPLATE_ID_SUBSCRIPTION_CANCELED', '')

    @property
    def is_production(self) -> bool:
        '''本番環境かどうか'''
        return self.app_env == 'production'

    @property
    def is_development(self) -> bool:
        '''開発環境かどうか'''
        return self.app_env == 'development'

    @property
    def stripe_price_ids(self) -> dict[str, str]:
        '''プラン名と価格IDのマッピング'''
        return {
            'Basic': self.stripe_price_id_basic,
            'Standard': self.stripe_price_id_standard,
            'Pro': self.stripe_price_id_pro,
        }

    def get_price_id_for_plan(self, plan_name: str) -> Optional[str]:
        '''プラン名から価格IDを取得'''
        return self.stripe_price_ids.get(plan_name)

    def get_plan_for_price_id(self, price_id: str) -> Optional[str]:
        '''価格IDからプラン名を取得'''
        for plan_name, pid in self.stripe_price_ids.items():
            if pid == price_id:
                return plan_name
        return None

    class Config:
        '''Pydantic設定'''
        env_file = '.env'
        case_sensitive = False


# シングルトンインスタンス
settings = Settings()