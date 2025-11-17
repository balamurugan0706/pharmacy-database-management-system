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

# ... (previous imports and app setup code remains the same) ...

@app.route('/admin/orders/<int:oid>/status', methods=['POST'])
@admin_required
def admin_change_order_status(oid):
    try:
        new_status = request.form.get('status')
        order = Order.query.get_or_404(oid)
        
        if new_status:
            old_status = order.status
            order.status = new_status
            
            # If changing to delivered and there's a linked prescription
            if new_status == 'delivered' and order.prescription_id:
                # Get the prescription before we delete it
                prescription = Prescription.query.get(order.prescription_id)
                if prescription:
                    # Delete the actual file if it exists
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], prescription.filename)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    # Delete the prescription record
                    db.session.delete(prescription)
            
            db.session.commit()
            if new_status == 'delivered' and old_status != 'delivered':
                flash('Order marked as delivered. Associated prescription has been archived.', 'success')
            else:
                flash('Order status updated', 'success')
                
    except Exception as e:
        db.session.rollback()
        flash('Error updating order status', 'error')
        print('Error updating order status:', str(e))
        
    return redirect(url_for('admin_orders'))