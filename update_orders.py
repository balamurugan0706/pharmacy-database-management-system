from app import app
from models import db, Order, User

def update_orders():
    with app.app_context():
        # Get any orders without user_id
        orders = Order.query.filter_by(user_id=None).all()
        if not orders:
            print("No orders found that need updating")
            return

        # Get the first user as default owner
        default_user = User.query.first()
        if not default_user:
            print("No users found in database")
            return

        print(f"Found {len(orders)} orders to update")
        for order in orders:
            order.user_id = default_user.id
            if not order.address_id:
                # Use user's default address if available
                default_address = next((addr for addr in default_user.addresses if addr.is_default), None)
                if default_address:
                    order.address_id = default_address.id
        
        try:
            db.session.commit()
            print("Successfully updated all orders")
        except Exception as e:
            db.session.rollback()
            print(f"Error updating orders: {str(e)}")

if __name__ == '__main__':
    update_orders()