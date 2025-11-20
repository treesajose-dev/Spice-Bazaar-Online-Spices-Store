# invoice_generator.py
from io import BytesIO
from flask import send_file, flash, redirect, url_for
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
import os
from datetime import datetime

def download_invoice(order_id, is_logged_in, get_db_connection):
    if not is_logged_in():
        flash('Please login to download invoice', 'danger')
        return redirect(url_for('login'))

    # Database connection
    db = get_db_connection()
    cursor = db.cursor()

    # Fetch cart details using Cart_master_id (order_id from dashboard)
    cursor.execute("""
        SELECT Cart_tot_amt
        FROM tbl_cart_master
        WHERE Cart_master_id = %s
    """, (order_id,))
    cart = cursor.fetchone()

    if not cart:
        flash('Invalid order', 'danger')
        cursor.close()
        db.close()
        return redirect(url_for('custdash'))  # Redirect to dashboard if order not found

    total_amount = cart['Cart_tot_amt'] if isinstance(cart, dict) else cart[0]

    # Fetch payment date (if paid) to use as invoice date
    cursor.execute("""
        SELECT Pay_date
        FROM tbl_payment
        WHERE Cart_master_id = %s AND Pay_status = 1
    """, (order_id,))
    payment = cursor.fetchone()

    pay_date = payment['Pay_date'] if payment and isinstance(payment, dict) else (payment[0] if payment else None)
    if pay_date:
        # If pay_date is a string, convert it to a datetime object
        if isinstance(pay_date, str):
            pay_date = datetime.strptime(pay_date, "%Y-%m-%d %H:%M:%S")  # Adjust format if needed
    else:
        pay_date = "Not Paid Yet"  # Fallback if no payment record exists

    # Fetch customer details including address and email (Username)
    cursor.execute("""
        SELECT c.Cust_fname, c.Cust_lname, c.Cust_phone, c.Cust_street, c.Cust_city, c.Cust_dist, 
               c.Cust_pin, c.Username
        FROM tbl_customer c
        JOIN tbl_cart_master cm ON c.Cust_id = cm.Cust_id
        WHERE cm.Cart_master_id = %s
    """, (order_id,))
    customer = cursor.fetchone()

    if not customer:
        flash('Customer details not found', 'danger')
        cursor.close()
        db.close()
        return redirect(url_for('custdash'))

    cust_fname = customer['Cust_fname'] if isinstance(customer, dict) else customer[0]
    cust_lname = customer['Cust_lname'] if isinstance(customer, dict) else customer[1]
    cust_phone = customer['Cust_phone'] if isinstance(customer, dict) else customer[2]
    cust_street = customer['Cust_street'] if isinstance(customer, dict) else customer[3]
    cust_city = customer['Cust_city'] if isinstance(customer, dict) else customer[4]
    cust_dist = customer['Cust_dist'] if isinstance(customer, dict) else customer[5]
    cust_pin = customer['Cust_pin'] if isinstance(customer, dict) else customer[6]
    cust_email = customer['Username'] if isinstance(customer, dict) else customer[7]

    # Fetch cart items
    cursor.execute("""
        SELECT i.Item_name, cc.Cart_qty, cc.Cart_unit_price, cc.Cart_price
        FROM tbl_cart_child cc
        JOIN tbl_item i ON cc.Item_id = i.Item_id
        WHERE cc.Cart_master_id = %s
    """, (order_id,))
    cart_items = cursor.fetchall()

    if not cart_items:
        flash('No items found in the order', 'danger')
        cursor.close()
        db.close()
        return redirect(url_for('custdash'))

    cursor.close()
    db.close()

    # Generate PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Header with Logo and Title
    logo_path = os.path.join('static', 'images', 'logo.jpg')
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=0.5*inch, height=0.5*inch)
        elements.append(logo)
    else:
        elements.append(Paragraph("Spice Bazaar", styles['Heading2']))

    elements.append(Paragraph("Invoice", styles['Title']))
    elements.append(Spacer(1, 12))

    # Invoice Number and Date
    invoice_info = f"""
    <b>Bill Number:</b> CM00{order_id}<br/>
    <b>Bill generated at</b><br/>
    <b>Date: </b>{pay_date.strftime('%d-%m-%Y') if isinstance(pay_date, datetime) else pay_date}<br/>
    <b>Time: </b>{pay_date.strftime('%I:%M:%S %p') if isinstance(pay_date, datetime) else ''}<br/>
    """
    elements.append(Paragraph(invoice_info, styles['Normal']))
    elements.append(Spacer(1, 12))

    # Bill From and Bill To in a Table
    data = [
        ["Bill from:", "Bill to:"],
        [
            Paragraph("""
                <b>Company Name:</b> Spice Bazaar<br/>
                <b>Company Address:</b> Orient Square, Kadavanthra Junction, Kadavanthra,<br/>
                Ernakulam, Kerala 682020<br/>
                <b>Company Phone Number:</b> +91 8987562319<br/>
                <b>Company Email Address:</b> info@spicebazaar.com
            """, styles['Normal']),
            Paragraph(f"""
                <b>Name:</b> {cust_fname} {cust_lname}<br/>
                <b>Address:</b> {cust_street}, {cust_city}, {cust_dist} - {cust_pin}<br/>
                <b>Phone Number:</b> {cust_phone}<br/>
                <b>Email:</b> {cust_email}<br/>
            """, styles['Normal'])
        ]
    ]
    bill_table = Table(data, colWidths=[2.4*inch, 2.4*inch])
    bill_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (1, 0), 12),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.black),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(bill_table)
    elements.append(Spacer(1, 24))

    # Table Header for Items
    data = [["Item Name", "Quantity", "Unit Price", "Total Price"]]
    
    # Add cart items to table
    for item in cart_items:
        item_name = item['Item_name'] if isinstance(item, dict) else item[0]
        qty = item['Cart_qty'] if isinstance(item, dict) else item[1]
        unit_price = item['Cart_unit_price'] if isinstance(item, dict) else item[2]
        total_price = item['Cart_price'] if isinstance(item, dict) else item[3]
        data.append([item_name, str(qty), f"Rs. {unit_price:.2f}", f"Rs. {total_price:.2f}"])

    # Add total amount
    data.append(["", "", "Total", f"Rs. {total_amount:.2f}"])

    # Create table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (-1, -1), (-1, -1), 'RIGHT'),
    ]))
    elements.append(table)

    # Build PDF
    doc.build(elements)

    # Prepare response
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"invoice_CM00{order_id}.pdf",
        mimetype='application/pdf'
    )