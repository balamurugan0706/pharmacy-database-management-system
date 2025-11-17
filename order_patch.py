from flask import jsonify
from models import db, Order, Prescription, PrescriptionArchive
import os

def archive_prescription(prescription, order):
    """Archive a prescription and its file instead of deleting them"""
    try:
        # Create archive record
        archive = PrescriptionArchive(
            original_id=prescription.id,
            user_id=prescription.user_id,
            order_id=order.id,
            prescription_number=prescription.prescription_number,
            filename=prescription.filename,
            doctor_name=prescription.doctor_name,
            uploaded_at=prescription.uploaded_at
        )
        
        # Move the file to archive directory
        old_path = os.path.join(app.config['UPLOAD_FOLDER'], prescription.filename)
        archive_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'archived')
        os.makedirs(archive_dir, exist_ok=True)
        new_path = os.path.join(archive_dir, prescription.filename)
        
        if os.path.exists(old_path):
            os.rename(old_path, new_path)  # Move file to archive
            
        # Save archive record and delete original
        db.session.add(archive)
        db.session.delete(prescription)
        
        return True
    except Exception as e:
        print(f"Error archiving prescription: {str(e)}")
        return False

@app.route('/admin/orders/<int:oid>/status', methods=['POST'])
@admin_required
def admin_change_order_status(oid):
    """Update order status and archive prescription if delivered"""
    try:
        new_status = request.form.get('status')
        order = Order.query.get_or_404(oid)
        
        if new_status:
            old_status = order.status
            order.status = new_status
            
            # If changing to delivered and there's a linked prescription
            if new_status == 'delivered' and order.prescription_id and old_status != 'delivered':
                prescription = Prescription.query.get(order.prescription_id)
                if prescription:
                    if archive_prescription(prescription, order):
                        flash('Order marked as delivered. Prescription has been archived.', 'success')
                    else:
                        flash('Order updated but there was an error archiving the prescription.', 'warning')
                        
            db.session.commit()
            if new_status != 'delivered' or old_status == 'delivered':
                flash('Order status updated', 'success')
                
    except Exception as e:
        db.session.rollback()
        flash('Error updating order status', 'error')
        print('Error updating order status:', str(e))
        
    return redirect(url_for('admin_orders'))

@app.route('/api/orders/<int:oid>/link-prescription', methods=['POST'])
@admin_required
def link_prescription_to_order(oid):
    """Link a prescription to an order"""
    try:
        data = request.get_json()
        if not data or 'prescription_id' not in data:
            return jsonify({'error': 'Missing prescription ID'}), 400
            
        order = Order.query.get_or_404(oid)
        prescription = Prescription.query.get_or_404(data['prescription_id'])
        
        # Ensure prescription belongs to the same user as the order
        if prescription.user_id != order.user_id:
            return jsonify({'error': 'Prescription belongs to different user'}), 403
            
        # Link prescription to order
        order.prescription_id = prescription.id
        db.session.commit()
        
        return jsonify({'message': 'Prescription linked successfully'})
        
    except Exception as e:
        db.session.rollback()
        print('Error linking prescription:', str(e))
        return jsonify({'error': 'Could not link prescription'}), 500

@app.route('/api/prescriptions/search')
@admin_required
def search_prescriptions():
    """Search prescriptions by number for linking to orders"""
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({'prescriptions': []})
            
        # Search for matching prescriptions
        prescriptions = Prescription.query.filter(
            Prescription.prescription_number.ilike(f'%{query}%')
        ).all()
        
        return jsonify({
            'prescriptions': [p.to_dict() for p in prescriptions]
        })
        
    except Exception as e:
        print('Error searching prescriptions:', str(e))
        return jsonify({'error': 'Search failed'}), 500