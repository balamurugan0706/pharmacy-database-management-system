from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False, index=True)
    price = db.Column(db.Integer, nullable=False)  # price in whole currency units
    stock = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, default=True)
    description = db.Column(db.String(500))
    image = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'price': self.price,
            'stock': self.stock,
            'is_active': self.is_active,
            'description': self.description,
            'image': self.image,
        }


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    total = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), default='pending')
    # delivery and payment info
    delivery_type = db.Column(db.String(50), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    address_id = db.Column(db.Integer, db.ForeignKey('addresses.id', ondelete='RESTRICT'), nullable=False, index=True)
    delivery_fee = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('orders', lazy=True))
    address = db.relationship('Address', backref=db.backref('orders', lazy=True))
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'total': self.total,
            'status': self.status,
            'delivery_type': self.delivery_type,
            'payment_method': self.payment_method,
            'address_id': self.address_id,
            'delivery_fee': self.delivery_fee,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False, index=True)
    product_name = db.Column(db.String(200), nullable=False)  # Store product name at time of order
    qty = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Integer, nullable=False)  # price at time of order
    
    # Relationship
    product = db.relationship('Product', backref=db.backref('order_items', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'product_id': self.product_id,
            'product_name': self.product_name,
            'qty': self.qty,
            'price': self.price,
            'product': self.product.to_dict() if self.product else None
        }


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    username = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # one-to-many: a user can have multiple saved addresses
    addresses = db.relationship('Address', backref='user', cascade='all, delete-orphan')

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)


class Admin(db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(300), nullable=False)
    name = db.Column(db.String(200))
    is_super = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)


class Address(db.Model):
    __tablename__ = 'addresses'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    label = db.Column(db.String(50))  # e.g., 'Home', 'Work'
    recipient_name = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    street = db.Column(db.String(300))
    city = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'label': self.label,
            'recipient_name': self.recipient_name,
            'phone': self.phone,
            'street': self.street,
            'city': self.city,
        }


class Prescription(db.Model):
    __tablename__ = 'prescriptions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    prescription_number = db.Column(db.String(50), unique=True)
    filename = db.Column(db.String(300), nullable=False)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    # notes column removed (no longer stored)
    doctor_name = db.Column(db.String(200))
    status = db.Column(db.String(50), nullable=False, default='pending')  # pending, processing, ready, completed, rejected
    type = db.Column(db.String(50), nullable=False, default='upload')  # upload, refill, transfer

    # Relationship with user
    user = db.relationship('User', backref=db.backref('prescriptions', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'prescription_number': self.prescription_number,
            'filename': self.filename,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'doctor_name': self.doctor_name,
            'status': self.status,
            'type': self.type
        }
