# app/utils/stripe.py
import stripe
import os
import logging
from dotenv import load_dotenv
from typing import Dict, Any, Optional

load_dotenv()

logger = logging.getLogger(__name__)
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

class StripeError(Exception):
    """Stripe固有のエラーハンドリング用カスタム例外"""
    pass

class StripeService:
    @staticmethod
    def create_payment_intent(amount: int, currency: str = 'jpy', metadata: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        支払いインテントを作成する
        """
        try:
            payment_intent_data = {
                'amount': amount,
                'currency': currency,
                'automatic_payment_methods': {'enabled': True}
            }
            
            if metadata:
                payment_intent_data['metadata'] = metadata

            intent = stripe.PaymentIntent.create(**payment_intent_data)
            
            logger.info(f"Created payment intent: {intent.id}")
            return {
                'client_secret': intent.client_secret,
                'payment_intent_id': intent.id
            }
        except stripe.error.CardError as e:
            logger.error(f"Card error: {str(e)}")
            raise StripeError(f"Card error: {str(e)}")
        except stripe.error.InvalidRequestError as e:
            logger.error(f"Invalid request: {str(e)}")
            raise StripeError(f"Invalid request: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in create_payment_intent: {str(e)}")
            raise StripeError(f"Failed to create payment intent: {str(e)}")

    @staticmethod
    def confirm_payment(payment_intent_id: str) -> bool:
        """
        支払いの状態を確認する
        """
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            logger.info(f"Payment intent {payment_intent_id} status: {payment_intent.status}")
            return payment_intent.status == 'succeeded'
        except stripe.error.InvalidRequestError as e:
            logger.error(f"Invalid payment intent ID: {str(e)}")
            raise StripeError(f"Invalid payment intent ID: {str(e)}")
        except Exception as e:
            logger.error(f"Error confirming payment: {str(e)}")
            raise StripeError(f"Failed to confirm payment: {str(e)}")

    @staticmethod
    def create_test_payment_intent(amount: int, currency: str = 'jpy') -> Dict[str, str]:
        """
        テスト用の支払いインテントを作成し、自動的に成功させる
        開発環境でのみ使用すること
        """
        try:
            # テストモードでのみ動作
            if not stripe.api_key.startswith('sk_test_'):
                raise StripeError("Test payment intents can only be created in test mode")

            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                confirm=True,
                payment_method='pm_card_visa',  # テスト用カード
                return_url='http://localhost:5000'  # テスト用リダイレクトURL
            )
            
            logger.info(f"Created test payment intent: {intent.id}")
            return {
                'client_secret': intent.client_secret,
                'payment_intent_id': intent.id
            }
        except Exception as e:
            logger.error(f"Error creating test payment intent: {str(e)}")
            raise StripeError(f"Failed to create test payment intent: {str(e)}")

    @staticmethod
    def get_payment_intent(payment_intent_id: str) -> Dict[str, Any]:
        """
        支払いインテントの詳細情報を取得する
        """
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return {
                'id': intent.id,
                'amount': intent.amount,
                'currency': intent.currency,
                'status': intent.status,
                'created': intent.created,
                'metadata': intent.metadata
            }
        except Exception as e:
            logger.error(f"Error retrieving payment intent: {str(e)}")
            raise StripeError(f"Failed to retrieve payment intent: {str(e)}")