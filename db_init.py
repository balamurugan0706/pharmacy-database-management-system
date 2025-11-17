"""Initialize the SQLite database and optionally seed products.

Run:
    python db_init.py
"""
from app import app
from models import db, Product
from models import Address, User
from sqlalchemy import text

seed_products = [
    {'name':'Multivitamin Tablets','category':'nutrition','price':600,'description':'Daily multivitamin for overall health','image':'image/multivitamin.webp'},
    {'name':'Paracetamol 500mg','category':'otc','price':100,'description':'Pain & fever relief','image':'image/paracetamol.svg'},
    {'name':'Baby Diaper Pack','category':'baby','price':400,'description':'Soft and absorbent diapers','image':'image/diaper.svg'},
    {'name':'Hand Sanitizer 250ml','category':'personal','price':90,'description':'Kills 99.9% germs','image':'image/sanitizer.svg'},
    {'name':'Feminine Care Pack','category':'women','price':300,'description':'Comfortable daily protection','image':'image/feminine.svg'},
    {'name':'Ashwagandha Capsules','category':'ayurveda','price':900,'description':'Supports stress relief and vitality','image':'image/ashwagandha.svg'},
    {'name':'Vitamin C 500mg','category':'nutrition','price':200,'description':'Immune support','image':'image/vitaminc.svg'},
    {'name':'Baby Shampoo','category':'baby','price':250,'description':'Gentle, tear-free formula','image':'image/babyshampoo.svg'},
    {'name':'Dental Care Kit','category':'personal','price':300,'description':'Complete oral hygiene set','image':'image/dentalcare.svg'},
    {'name':'Prenatal Vitamins','category':'women','price':500,'description':'Essential nutrients for pregnancy','image':'image/prenatal.svg'},
    {'name':'Turmeric Capsules','category':'ayurveda','price':250,'description':'Natural anti-inflammatory support','image':'image/turmeric.svg'},
    {'name':'Antacid Tablets','category':'otc','price':80,'description':'Quick acid reflux relief','image':'image/antacid.svg'},
    {'name':'Baby Wipes Pack','category':'baby','price':200,'description':'Alcohol-free wipes (80)','image':'image/babywipes.svg'},
    {'name':'Baby Powder','category':'baby','price':150,'description':'Talc-free gentle powder','image':'image/babypowder.svg'},
    {'name':'Baby Care Kit','category':'baby','price':700,'description':'Complete grooming essentials kit','image':'image/babykit.svg'},
    {'name':'Face Wash','category':'personal','price':200,'description':'Gentle daily face cleanser','image':'image/facewash.svg'},
    {'name':'Deodorant','category':'personal','price':160,'description':'48-hour protection','image':'image/deodorant.svg'},
    {'name':'Body Wash','category':'personal','price':180,'description':'Refreshing shower gel','image':'image/bodywash.svg'},
    {'name':'Cold Relief Tablets','category':'otc','price':150,'description':'Cold & flu relief','image':'image/coldrelief.svg'},
    {'name':'Allergy Relief','category':'otc','price':190,'description':'24-hour allergy protection','image':'image/allergy.svg'},
    {'name':'Pain Relief Gel','category':'otc','price':160,'description':'Topical pain relief','image':'image/paingel.svg'},
    {'name':'Women\'s Multivitamin','category':'women','price':380,'description':'Complete daily nutrition for women','image':'image/womenvitamin.svg'},
    {'name':'Iron Supplements','category':'women','price':420,'description':'Support healthy iron levels','image':'image/iron.svg'},
    {'name':'Calcium Plus D3','category':'women','price':550,'description':'Bone health support','image':'image/calcium.svg'},
    {'name':'Protein Powder','category':'nutrition','price':650,'description':'High-quality whey protein blend','image':'image/protein.svg'},
    {'name':'Omega-3 Fish Oil','category':'nutrition','price':480,'description':'Heart and brain health support','image':'image/fishoil.svg'},
    {'name':'Zinc Complex','category':'nutrition','price':320,'description':'Immune system support','image':'image/zinc.svg'},
    {'name':'Triphala Powder','category':'ayurveda','price':450,'description':'Digestive health supplement','image':'image/triphala.svg'},
    {'name':'Giloy Tablets','category':'ayurveda','price':380,'description':'Immunity booster','image':'image/giloy.svg'},
    {'name':'Brahmi Capsules','category':'ayurveda','price':290,'description':'Memory and cognitive support','image':'image/brahmi.svg'},
]


def ensure_product_columns():
    """Add sku, stock, is_active columns to products table if they don't exist.

    This is a convenience for development. In production use Alembic/Flask-Migrate.
    """
    with app.app_context():
        db_name = db.engine.url.database
        checks = {
            'sku': "ALTER TABLE products ADD COLUMN sku VARCHAR(100)",
            'stock': "ALTER TABLE products ADD COLUMN stock INT DEFAULT 0",
            'is_active': "ALTER TABLE products ADD COLUMN is_active TINYINT(1) DEFAULT 1",
        }
        for col, alter_sql in checks.items():
            qry = text("SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=:schema AND table_name='products' AND column_name=:col")
            res = db.session.execute(qry, {'schema': db_name, 'col': col}).scalar()
            if not res:
                db.session.execute(text(alter_sql))
                db.session.commit()


def ensure_order_columns():
    """Add delivery-related columns to orders table if they don't exist.

    Convenience only - use migrations for production.
    """
    with app.app_context():
        db_name = db.engine.url.database
        checks = {
            'address_id': "ALTER TABLE orders ADD COLUMN address_id INT",
            'street': "ALTER TABLE orders ADD COLUMN street VARCHAR(300)",
            'city': "ALTER TABLE orders ADD COLUMN city VARCHAR(100)",
            'state': "ALTER TABLE orders ADD COLUMN state VARCHAR(100)",
            'postal_code': "ALTER TABLE orders ADD COLUMN postal_code VARCHAR(20)",
            'country': "ALTER TABLE orders ADD COLUMN country VARCHAR(100)",
            'delivery_instructions': "ALTER TABLE orders ADD COLUMN delivery_instructions TEXT",
            'scheduled_delivery': "ALTER TABLE orders ADD COLUMN scheduled_delivery DATETIME",
            'delivery_fee': "ALTER TABLE orders ADD COLUMN delivery_fee INT DEFAULT 0",
        }
        for col, alter_sql in checks.items():
            qry = text("SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=:schema AND table_name='orders' AND column_name=:col")
            res = db.session.execute(qry, {'schema': db_name, 'col': col}).scalar()
            if not res:
                db.session.execute(text(alter_sql))
                db.session.commit()


def init_db(seed=True):
    with app.app_context():
        db.create_all()
        # ensure product and order columns exist for older schemas (adds columns if missing)
        try:
            ensure_product_columns()
        except Exception as e:
            print('ensure_product_columns failed:', e)
        try:
            ensure_order_columns()
        except Exception as e:
            print('ensure_order_columns failed:', e)
        if seed:
            # only seed if products table is empty
            if Product.query.first() is None:
                for i, p in enumerate(seed_products, start=1):
                    sku = f"SKU{i:04d}"
                    prod = Product(name=p['name'], category=p['category'], price=p['price'], sku=sku, stock=10, is_active=True, description=p.get('description',''), image=p.get('image',''))
                    db.session.add(prod)
                db.session.commit()
                print(f"Seeded {len(seed_products)} products")
            else:
                print("Products already present; skipping seed.")

            # create a sample address for the first user (if any) when none exist
            first_user = User.query.first()
            if first_user:
                if Address.query.filter_by(user_id=first_user.id).first() is None:
                    addr = Address(user_id=first_user.id, label='Home', recipient_name=first_user.name, phone='', street=first_user.street if hasattr(first_user, 'street') else '', city=first_user.city if hasattr(first_user, 'city') else '', state='Tamilnadu', postal_code='00000', country='India', is_default=True)
                    db.session.add(addr)
                    db.session.commit()
                    print('Added a sample address for user', first_user.name)


if __name__ == '__main__':
    init_db(seed=True)


def ensure_order_columns():
    """Add delivery-related columns to orders table if they don't exist.

    Convenience only - use migrations for production.
    """
    with app.app_context():
        db_name = db.engine.url.database
        checks = {
            'address_id': "ALTER TABLE orders ADD COLUMN address_id INT",
            'street': "ALTER TABLE orders ADD COLUMN street VARCHAR(300)",
            'city': "ALTER TABLE orders ADD COLUMN city VARCHAR(100)",
            'state': "ALTER TABLE orders ADD COLUMN state VARCHAR(100)",
            'postal_code': "ALTER TABLE orders ADD COLUMN postal_code VARCHAR(20)",
            'country': "ALTER TABLE orders ADD COLUMN country VARCHAR(100)",
            'delivery_instructions': "ALTER TABLE orders ADD COLUMN delivery_instructions TEXT",
            'scheduled_delivery': "ALTER TABLE orders ADD COLUMN scheduled_delivery DATETIME",
            'delivery_fee': "ALTER TABLE orders ADD COLUMN delivery_fee INT DEFAULT 0",
        }
        for col, alter_sql in checks.items():
            qry = text("SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=:schema AND table_name='orders' AND column_name=:col")
            res = db.session.execute(qry, {'schema': db_name, 'col': col}).scalar()
            if not res:
                db.session.execute(text(alter_sql))
                db.session.commit()

