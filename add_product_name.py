from app import app, db
from sqlalchemy import text

def add_product_name_column():
    with app.app_context():
        # Add the column
        try:
            db.session.execute(text("ALTER TABLE order_items ADD COLUMN product_name VARCHAR(200) NOT NULL AFTER product_id"))
            db.session.commit()
            print("Added product_name column")
        except Exception as e:
            if "Duplicate column name" not in str(e):
                print(f"Error adding column: {e}")
                return
            else:
                print("Column already exists")

        # Update existing records
        try:
            db.session.execute(text("""
                UPDATE order_items oi 
                INNER JOIN products p ON oi.product_id = p.id 
                SET oi.product_name = p.name
                WHERE oi.product_name IS NULL OR oi.product_name = ''
            """))
            db.session.commit()
            print("Updated existing records with product names")
        except Exception as e:
            print(f"Error updating records: {e}")

if __name__ == "__main__":
    add_product_name_column()