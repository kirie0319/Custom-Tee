# app/api/admin/routes.py
from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from app.models.order import Order, OrderItem
from app.models.user import User
from app import db
from sqlalchemy import func
from functools import wraps
from app.api.admin import bp

def admin_required():
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorator(*args, **kwargs):
            claims = get_jwt()
            if not claims.get("is_admin", False):
                return jsonify({"error": "Admin privileges required"}), 403
            return fn(*args, **kwargs)
        return decorator
    return wrapper

@bp.route('/users', methods=['GET'])
@admin_required()
def get_users():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '')

        query = User.query
        if search:
            query = query.filter(
                db.or_(
                    User.username.ilike(f'%{search}%'),
                    User.email.ilike(f'%{search}%')
                )
            )

        users = query.paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'users': [{
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_admin': user.is_admin,
                'is_active': True,
                'orders_count': user.orders.count(),
                'created_at': user.created_at.isoformat() if user.created_at else None
            } for user in users.items],
            'total': users.total,
            'pages': users.pages,
            'current_page': page
        }), 200

    except Exception as e:
        import traceback
        print("Error in get_users:", str(e))
        print("Traceback:", traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@bp.route('/orders/search', methods=['GET'])
@admin_required()
def search_orders():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status = request.args.get('status')
        query = request.args.get('query')

        order_query = Order.query
        if status:
            order_query = order_query.filter_by(status=status)
        if query:
            order_query = order_query.join(User).filter(
                db.or_(
                    Order.id.like(f'%{query}%'),
                    User.email.like(f'%{query}%')
                )
            )

        orders = order_query.order_by(Order.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify({
            'orders': [{
                'id': order.id,
                'user': {
                    'id': order.user_id,
                    'email': order.customer.email  # customerを使用
                },
                'total_amount': float(order.total_amount),
                'status': order.status,
                'created_at': order.created_at.isoformat(),
                'items_count': order.order_items.count()  # order_itemsを使用
            } for order in orders.items],
            'total': orders.total,
            'pages': orders.pages,
            'current_page': page
        }), 200

    except Exception as e:
        import traceback
        print("Error in search_orders:", str(e))
        print("Traceback:", traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@bp.route('/orders/<int:order_id>/status', methods=['PUT'])
@admin_required()
def update_order_status(order_id):
    try:
        data = request.get_json()
        if not data or 'status' not in data:
            return jsonify({'error': 'Status is required'}), 400

        order = Order.query.get_or_404(order_id)
        order.status = data['status']
        order.updated_at = datetime.utcnow()
        
        db.session.commit()

        return jsonify({
            'message': 'Order status updated',
            'order': order.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/stats', methods=['GET'])
@admin_required()
def get_stats():
    try:
        # 売上統計
        total_sales = db.session.query(func.sum(Order.total_amount)).scalar() or 0
        total_orders = Order.query.count()
        total_users = User.query.count()

        # 直近の注文
        recent_orders = Order.query.order_by(
            Order.created_at.desc()
        ).limit(5).all()

        # ステータス別の注文数
        status_counts = db.session.query(
            Order.status, func.count(Order.id)
        ).group_by(Order.status).all()

        return jsonify({
            'total_sales': float(total_sales),
            'total_orders': total_orders,
            'total_users': total_users,
            'status_counts': dict(status_counts),
            'recent_orders': [order.to_dict() for order in recent_orders]
        }), 200
        
    except Exception as e:
        print("Error in get_stats:", str(e))
        return jsonify({"error": str(e)}), 500

@bp.route('/users/manage', methods=['POST'])
@admin_required()
def manage_user():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        action = data.get('action')

        if not user_id or not action:
            return jsonify({'error': 'Missing required fields'}), 400

        user = User.query.get_or_404(user_id)
        
        valid_actions = ['deactivate', 'activate', 'make_admin', 'remove_admin']
        if action not in valid_actions:
            return jsonify({'error': 'Invalid action'}), 400

        if action == 'make_admin':
            user.is_admin = True
        elif action == 'remove_admin':
            user.is_admin = False

        db.session.commit()
        return jsonify({
            'message': f'User {action} successful',
            'user': user.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
        
@bp.route('/orders/<int:order_id>', methods=['GET'])
@admin_required()
def get_order_details(order_id):
    try:
        order = Order.query.get_or_404(order_id)
        
        # Orderモデルのto_dict()メソッドを使用して詳細情報を取得
        order_data = order.to_dict()
        
        # ユーザー情報を追加
        order_data['user'] = {
            'id': order.user_id,
            'email': order.customer.email if order.customer else None
        }
        
        return jsonify(order_data), 200

    except Exception as e:
        import traceback
        print("Error in get_order_details:", str(e))
        print("Traceback:", traceback.format_exc())
        return jsonify({"error": str(e)}), 500