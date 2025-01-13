# app/api/payment/routes.py
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.order import Order, OrderItem, CartItem
from app.models.user import User
from app.utils.stripe import StripeService
from app.utils.email import EmailService
from app.api.payment import bp

@bp.route('/create-payment', methods=['POST'])
@jwt_required()
def create_payment():
   try:
       current_user_id = get_jwt_identity()
       
       # カート内のアイテムを取得
       cart_items = CartItem.query.filter_by(user_id=current_user_id).all()
       if not cart_items:
           return jsonify({'error': 'Cart is empty'}), 400

       # 合計金額を計算
       total_amount = sum(item.quantity * 3000 + 500 for item in cart_items)

       # Stripeの支払いインテントを作成
       payment_data = StripeService.create_payment_intent(total_amount)

       return jsonify({
           'client_secret': payment_data['client_secret'],
           'payment_intent_id': payment_data['payment_intent_id'],
           'amount': total_amount
       }), 200

   except Exception as e:
       print(f"Error in create_payment: {str(e)}")
       return jsonify({'error': str(e)}), 500

# app/api/payment/routes.py

@bp.route('/confirm-payment', methods=['POST'])
@jwt_required()
def confirm_payment():
    try:
        data = request.get_json()
        if not data or not data.get('payment_intent_id') or not data.get('shipping_address'):
            return jsonify({'error': 'Missing required fields'}), 400

        current_user_id = get_jwt_identity()
        payment_intent_id = data['payment_intent_id']
        shipping_info = data['shipping_address']

        # Stripeで支払い状態を確認
        payment_status = StripeService.confirm_payment(payment_intent_id)
        if not payment_status:
            return jsonify({'error': 'Payment verification failed'}), 400

        user = User.query.get(current_user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # トランザクション開始
        try:
            # カート内のアイテムを取得し、在庫確認
            cart_items = CartItem.query.filter_by(user_id=current_user_id).all()
            if not cart_items:
                return jsonify({'error': 'Cart is empty'}), 400

            total_amount = sum(item.quantity * 2000 for item in cart_items)

            # 注文作成
            order = Order(
                user_id=current_user_id,
                total_amount=total_amount,
                status='processing',  # 支払い確認後は'processing'に
                payment_id=payment_intent_id,
                shipping_address=shipping_info
            )
            db.session.add(order)
            db.session.flush()

            # 注文アイテム作成
            for cart_item in cart_items:
                order_item = OrderItem(
                    order_id=order.id,
                    design_id=cart_item.design_id,
                    quantity=cart_item.quantity,
                    size=cart_item.size,
                    color=cart_item.color,
                    price=3000
                )
                db.session.add(order_item)

            # カートクリア
            for item in cart_items:
                db.session.delete(item)

            db.session.commit()

            # 注文確認メール送信
            try:
                EmailService.send_order_confirmation(
                    order=order,
                    recipient_email=user.email
                )
            except Exception as mail_error:
                current_app.logger.error(f"Failed to send order confirmation email: {mail_error}")
                # メール送信失敗は注文処理には影響させない

            return jsonify({
                'message': 'Order processed successfully',
                'order_id': order.id
            }), 200

        except Exception as db_error:
            db.session.rollback()
            current_app.logger.error(f"Database error in order processing: {db_error}")
            return jsonify({'error': 'Failed to process order'}), 500

    except Exception as e:
        current_app.logger.error(f"Error in confirm_payment: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/orders', methods=['GET'])
@jwt_required()
def get_orders():
   try:
       current_user_id = get_jwt_identity()
       orders = Order.query.filter_by(user_id=current_user_id).all()

       return jsonify({
           'orders': [{
               'id': order.id,
               'total_amount': order.total_amount,
               'status': order.status,
               'created_at': order.created_at.isoformat(),
               'items': [{
                   'design_id': item.design_id,
                   'quantity': item.quantity,
                   'size': item.size,
                   'color': item.color,
                   'price': item.price
               } for item in order.order_items]
           } for order in orders]
       }), 200

   except Exception as e:
       return jsonify({'error': str(e)}), 500

@bp.route('/test-email', methods=['POST'])
def test_email():
   try:
       # テスト注文データ
       test_order = {
           'id': 'TEST-001',
           'total_amount': 2000,
           'order_items': [{
               'design_id': 1,
               'size': 'M',
               'color': 'White',
               'quantity': 1,
               'price': 2000,
               'design': {
                   'prompt': 'テストデザイン'
               }
           }],
           'shipping_address': {
               'name': 'テスト太郎',
               'address': 'テスト住所1-1-1',
               'city': 'テスト市',
               'postal_code': '123-4567',
               'country': '日本'
           }
       }

       result = EmailService.send_order_confirmation(
           test_order,
           current_app.config['ADMIN_EMAIL']
       )

       if result:
           return jsonify({
               'message': 'Test email sent successfully',
               'recipient': current_app.config['ADMIN_EMAIL']
           }), 200
       else:
           return jsonify({'error': 'Failed to send test email'}), 500

   except Exception as e:
       print(f"Error sending test email: {str(e)}")
       return jsonify({'error': str(e)}), 500

@bp.route('/test-payment-flow', methods=['POST'])
@jwt_required()
def test_payment_flow():
    """テスト用の決済フローエンドポイント"""
    try:
        current_user_id = get_jwt_identity()
        
        # カート内のアイテムを取得
        cart_items = CartItem.query.filter_by(user_id=current_user_id).all()
        if not cart_items:
            return jsonify({'error': 'Cart is empty'}), 400

        total_amount = sum(item.quantity * 2000 for item in cart_items)
        
        # テスト用の支払いインテントを作成（自動的に成功する）
        payment_data = StripeService.create_test_payment_intent(total_amount)
        
        # 支払い確認用のデータを作成
        confirmation_data = {
            'payment_intent_id': payment_data['payment_intent_id'],
            'shipping_address': {
                'name': 'テストユーザー',
                'postal_code': '123-4567',
                'address': 'テスト住所1-1-1',
                'city': 'テスト市'
            }
        }
        
        # リクエストデータを更新
        request.get_json = lambda: confirmation_data
        
        # 既存のconfirm_payment関数を呼び出し
        return confirm_payment()
        
    except Exception as e:
        current_app.logger.error(f"Error in test payment flow: {str(e)}")
        return jsonify({'error': str(e)}), 500