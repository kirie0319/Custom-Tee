# app/models/order.py
from datetime import datetime
from app import db

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')
    shipping_address = db.Column(db.JSON, nullable=False, comment='{name, address, city, postal_code, country}')
    payment_id = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    order_items = db.relationship('OrderItem', backref='order', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'total_amount': self.total_amount,
            'status': self.status,
            'shipping_address': self.shipping_address,
            'payment_id': self.payment_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'items': [item.to_dict() for item in self.order_items]
        }

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    design_id = db.Column(db.Integer, db.ForeignKey('designs.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    size = db.Column(db.String(10), nullable=False)
    color = db.Column(db.String(20), nullable=False)
    price = db.Column(db.Float, nullable=False)
    design_config = db.Column(db.JSON, nullable=True, comment='{position, scale, rotation}')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    design = db.relationship('Design', backref='order_items')

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'design_id': self.design_id,
            'quantity': self.quantity,
            'size': self.size,
            'color': self.color,
            'price': self.price,
            'design_config': self.design_config,
            'created_at': self.created_at.isoformat(),
            'design': self.design.to_dict() if self.design else None  # design情報を追加
        }

class CartItem(db.Model):
    __tablename__ = 'cart_items'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    design_id = db.Column(db.Integer, db.ForeignKey('designs.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    size = db.Column(db.String(10), nullable=False)
    color = db.Column(db.String(20), nullable=False)
    design_config = db.Column(db.JSON, nullable=True)  # デザイン位置などの設定を保存
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    design = db.relationship('Design', backref='cart_items')

    def to_dict(self):
        return {
            'id': self.id,
            'design_id': self.design_id,
            'quantity': self.quantity,
            'size': self.size,
            'color': self.color,
            'design_config': self.design_config,
            'design': self.design.to_dict() if self.design else None,
            'created_at': self.created_at.isoformat()
        }