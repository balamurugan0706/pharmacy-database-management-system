from flask import Flask, render_template, jsonify, request, url_for, session, flash, redirect
from models import db, Product, Order, OrderItem
from models import User, Address, Prescription, Admin
from sqlalchemy import text
from functools import wraps
from flask_migrate import Migrate
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import smtplib



app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Bala2007@localhost/pharmacy_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'change-me-in-prod')
# where to store uploaded prescriptions (served as static files)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'prescriptions')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_PRESCRIPTION_EXT = {'pdf', 'png', 'jpg', 'jpeg'}

# initialize SQLAlchemy
db.init_app(app)
migrate = Migrate(app, db)


# simple login_required decorator
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            # redirect to login and include next param so user returns here after login
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_id'):
            return redirect(url_for('admin_login', next=request.path))
        return f(*args, **kwargs)
    return decorated



@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        next_url = request.form.get('next') or request.args.get('next')

        if not (username and password):
            flash('Username and password are required.', 'error')
            return render_template('login.html', next=next_url)

        # Find existing user by username
        try:
            user = User.query.filter_by(username=username).first()
            
            if user:
                # existing user: verify password
                if not user.check_password(password):
                    flash('Invalid password. Please try again.', 'error')
                    return render_template('login.html', next=next_url)
            else:
                # create new user with provided username; use username as name by default
                try:
                    user = User(username=username, name=username)
                    user.set_password(password)
                    db.session.add(user)
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    if 'Duplicate entry' in str(e):
                        flash('Username already taken. Please choose a different username.', 'error')
                    else:
                        flash('An error occurred while creating your account. Please try again.', 'error')
                    return render_template('login.html', next=next_url)

            # Set session
            session['user_id'] = user.id
            session['user_name'] = user.name
            flash('Successfully logged in!', 'success')

            if next_url:
                return redirect(next_url)
            return redirect(url_for('home'))

        except Exception as e:
            flash('An error occurred. Please try again.', 'error')
            return render_template('login.html', next=next_url)

    return render_template('login.html')




@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    return redirect(url_for('login'))

@app.route('/home')
def home():
    # If user is not logged in, send them to the login page first
    if not session.get('user_id'):
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/products')
@login_required
def products():
    return render_template('products.html')


@app.route('/services')
@login_required
def services():
    return render_template('services.html')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_PRESCRIPTION_EXT

@app.route('/prescriptions')
@login_required
def prescriptions():
    user_prescriptions = Prescription.query.filter_by(user_id=session['user_id']).order_by(Prescription.uploaded_at.desc()).all()
    return render_template('prescriptions.html', prescriptions=user_prescriptions)


# Admin area
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        admin = Admin.query.filter_by(username=username).first()
        if not admin or not admin.check_password(password):
            flash('Invalid admin credentials', 'error')
            return render_template('admin/login.html')
        session['admin_id'] = admin.id
        session['admin_name'] = admin.name or admin.username
        flash('Admin logged in', 'success')
        next_url = request.args.get('next') or url_for('admin_dashboard')
        return redirect(next_url)
    return render_template('admin/login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_name', None)
    return redirect(url_for('admin_login'))


@app.route('/admin')
@admin_required
def admin_dashboard():
    # simple dashboard counts
    total_prescriptions = Prescription.query.count()
    pending_prescriptions = Prescription.query.filter_by(status='pending').count()
    total_orders = Order.query.count()
    total_products = Product.query.count()
    return render_template('admin/dashboard.html',
                           total_prescriptions=total_prescriptions,
                           pending_prescriptions=pending_prescriptions,
                           total_orders=total_orders,
                           total_products=total_products)


@app.route('/admin/account', methods=['GET', 'POST'])
@admin_required
def admin_account():
    from models import Admin
    admin = Admin.query.get(session.get('admin_id'))
    if not admin:
        flash('Admin not found', 'error')
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        # Form fields
        current_password = request.form.get('current_password')
        new_username = request.form.get('new_username')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Verify current password
        if not admin.check_password(current_password):
            flash('Current password is incorrect.', 'error')
            return render_template('admin/account.html', admin=admin)

        changed = False
        # Update username if provided
        if new_username and new_username != admin.username:
            # ensure uniqueness
            exists = Admin.query.filter_by(username=new_username).first()
            if exists and exists.id != admin.id:
                flash('Username already taken by another admin.', 'error')
                return render_template('admin/account.html', admin=admin)
            admin.username = new_username
            changed = True

        # Update password if provided (and matches confirm)
        if new_password:
            if new_password != confirm_password:
                flash('New password and confirmation do not match.', 'error')
                return render_template('admin/account.html', admin=admin)
            admin.set_password(new_password)
            changed = True

        if changed:
            db.session.add(admin)
            db.session.commit()
            # update session name if changed
            session['admin_name'] = admin.name or admin.username
            flash('Account updated successfully.', 'success')
            return redirect(url_for('admin_dashboard'))

        flash('No changes made.', 'info')

    return render_template('admin/account.html', admin=admin)


@app.route('/admin/prescriptions')
@admin_required
def admin_prescriptions():
    prescs = Prescription.query.order_by(Prescription.uploaded_at.desc()).all()
    return render_template('admin/prescriptions.html', prescriptions=prescs)


@app.route('/admin/prescriptions/<int:pid>/status', methods=['POST'])
@admin_required
def admin_change_prescription_status(pid):
    new_status = request.form.get('status')
    presc = Prescription.query.get_or_404(pid)
    if new_status:
        presc.status = new_status
        db.session.commit()
        flash('Prescription status updated', 'success')
    return redirect(url_for('admin_prescriptions'))


@app.route('/admin/orders')
@admin_required
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders)


@app.route('/admin/orders/<int:oid>/status', methods=['POST'])
@admin_required
def admin_change_order_status(oid):
    new_status = request.form.get('status')
    order = Order.query.get_or_404(oid)
    if new_status:
        order.status = new_status
        db.session.commit()
        flash('Order status updated', 'success')
    return redirect(url_for('admin_orders'))


@app.route('/admin/products')
@admin_required
def admin_products():
    products = Product.query.order_by(Product.name).all()
    return render_template('admin/products.html', products=products)


@app.route('/admin/products/new', methods=['POST'])
@admin_required
def admin_create_product():
    name = request.form.get('name')
    category = request.form.get('category') or 'other'
    # parse numeric inputs more robustly (accept decimals in the form)
    def _parse_int_field(val, default=0):
        try:
            if val is None or str(val).strip() == '':
                return default
            # allow decimals like '12.50' but store as whole units
            return int(round(float(val)))
        except Exception:
            return default

    price = _parse_int_field(request.form.get('price'), 0)
    stock = _parse_int_field(request.form.get('stock'), 0)
    if not name:
        flash('Product name required', 'error')
        return redirect(url_for('admin_products'))
    p = Product(name=name, category=category, price=price, stock=stock, is_active=True)
    db.session.add(p)
    db.session.commit()
    flash('Product created', 'success')
    return redirect(url_for('admin_products'))


@app.route('/admin/products/<int:pid>/update', methods=['POST'])
@admin_required
def admin_update_product(pid):
    p = Product.query.get_or_404(pid)
    p.name = request.form.get('name') or p.name
    p.category = request.form.get('category') or p.category
    # robust parsing: preserve existing values when input is empty, accept decimal inputs
    def _parse_update_int_field(val, current):
        try:
            if val is None or str(val).strip() == '':
                return current
            return int(round(float(val)))
        except Exception:
            return current

    p.price = _parse_update_int_field(request.form.get('price'), p.price)
    p.stock = _parse_update_int_field(request.form.get('stock'), p.stock)
    # checkbox returns '1' when checked, otherwise missing
    p.is_active = True if request.form.get('is_active') in ('1', 'on', 'true', 'True') else False
    db.session.commit()
    flash('Product updated', 'success')
    return redirect(url_for('admin_products'))


@app.route('/admin/products/<int:pid>/delete', methods=['POST'])
@admin_required
def admin_delete_product(pid):
    p = Product.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    flash('Product deleted', 'success')
    return redirect(url_for('admin_products'))

@app.route('/api/prescriptions/upload', methods=['POST'])
@login_required
def upload_prescription():
    try:
        if 'prescription' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['prescription']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': f'File type not allowed. Allowed types: {", ".join(ALLOWED_PRESCRIPTION_EXT)}'}), 400
        
        # Get form data
        doctor_name = request.form.get('doctor_name', '')
        
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"prescription_{session['user_id']}_{timestamp}_{secure_filename(file.filename)}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Save file
        file.save(file_path)
        
        # Create prescription record
        prescription = Prescription(
            user_id=session['user_id'],
            filename=filename,
            doctor_name=doctor_name,
            type='upload',
            status='pending',
            prescription_number=f"RX{timestamp}"  # Generate unique prescription number
        )
        
        db.session.add(prescription)
        db.session.commit()
        
        return jsonify({
            'message': 'Prescription uploaded successfully',
            'prescription': prescription.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        print('Prescription upload failed:', str(e))
        return jsonify({'error': 'Could not upload prescription'}), 500


@app.route('/cart')
@login_required
def cart():
    return render_template('cart.html')

@app.route('/orders')
@login_required
def orders():
    user_orders = Order.query.filter_by(user_id=session['user_id']).order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=user_orders)


@app.route('/delivery')

def delivery():
    return render_template('delivery.html')


@app.route('/api/orders', methods=['POST'])
def create_order():
    """API endpoint for creating new orders."""
    try:
        # Require authentication
        if not session.get('user_id'):
            return jsonify({'error': 'Please log in to place orders.'}), 401

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # validate required fields
        required = ['customer_name', 'phone', 'streetAddress', 'city', 'delivery_type', 'payment_method', 'items']
        missing = [f for f in required if not data.get(f)]
        if missing:
            return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

        if not data['items']:
            return jsonify({'error': 'Cart is empty'}), 400

        # calculate order total including delivery fee
        items_total = 0
        order_items = []

        for item in data['items']:
            if not isinstance(item, dict):  # handle raw cart format
                continue
            qty = int(item.get('qty', 1))
            price = int(item.get('price', 0))  # from cart
            items_total += qty * price
            order_items.append({
                'qty': qty,
                'price': price,
                'product_name': item.get('name', '')
            })

        delivery_fee = 60 if data['delivery_type'] == 'express' else 30
        total = items_total + delivery_fee

        # get user
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # save address if it's new (check by street+city combination)
        street = data.get('streetAddress', '')
        city = data.get('city', '')
        
        # look for matching address
        existing_address = Address.query.filter_by(
            user_id=user_id,
            street=street,
            city=city
        ).first()

        if existing_address:
            address = existing_address
        else:
            # create new address
            address = Address(
                user_id=user_id,
                recipient_name=data['customer_name'],
                phone=data['phone'],
                street=street,
                city=city,
                label='Home'  # default label
            )
            db.session.add(address)
            db.session.flush()  # get address.id before creating order

        # create order
        order = Order(
            user_id=user_id,  # Set the user_id from the session
            delivery_type=data['delivery_type'],
            payment_method=data['payment_method'],
            total=total,
            delivery_fee=delivery_fee,
            address_id=address.id
        )
        db.session.add(order)

        # create order items (using cart data since we don't have product_ids)
        for item in order_items:
            # Try to find the product by name
            product = Product.query.filter_by(name=item['product_name']).first()
            if not product:
                # Create new product if it doesn't exist
                product = Product(
                    name=item['product_name'],
                    price=item['price'],
                    category='other',
                    stock=100,
                    is_active=True
                )
                db.session.add(product)
                db.session.flush()  # get product.id

            # Check stock before placing order
            if product.stock < item['qty']:
                return jsonify({'error': f'Insufficient stock for {product.name}. Only {product.stock} left.'}), 400

            # Decrease stock
            product.stock -= item['qty']
            # Set is_active to 0 if stock is 0
            if product.stock == 0:
                product.is_active = False

            order_item = OrderItem(
                order=order,
                product_id=product.id,
                product_name=product.name,  # Store the product name at time of order
                qty=item['qty'],
                price=item['price']
            )
            db.session.add(order_item)

        db.session.commit()
        return jsonify({
            'order_id': order.id,
            'total': total,
            'delivery_fee': delivery_fee
        })

    except Exception as e:
        db.session.rollback()
        print('Order creation failed:', str(e))
        return jsonify({'error': 'Could not create order'}), 500


def ensure_password_column():
    """Ensure users.password_hash column exists; alter table if necessary."""
    db_name = db.engine.url.database
    qry = text("SELECT COUNT(*) AS cnt FROM information_schema.columns WHERE table_schema=:schema AND table_name='users' AND column_name='password_hash'")
    res = db.session.execute(qry, {'schema': db_name}).scalar()
    if not res:
        # add the password_hash column
        db.session.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(300)"))
        db.session.commit()




if __name__ == '__main__':
    # create DB tables if they don't exist (safe to call)
    with app.app_context():
        # ensure users table has password_hash column (adds if missing)
        try:
            ensure_password_column()
        except Exception as e:
            # non-fatal: log and continue
            print('ensure_password_column failed:', e)
        # (no runtime schema changes for prescriptions)
        db.create_all()
    app.run(debug=True)



