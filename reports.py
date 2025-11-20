from flask import render_template, request, redirect, url_for, flash, send_file
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.fonts import tt2ps
from datetime import datetime
from io import BytesIO
import pymysql
from reportlab.platypus import Image, Table, TableStyle
import os

def get_db_connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='',
        database='spice_bazaar',
        cursorclass=pymysql.cursors.DictCursor
    )

def admin_reports(app, session):
    if 'username' not in session:
        flash('Please login to access reports', 'danger')
        return redirect(url_for('loginpage'))

    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT Login_type FROM tbl_login WHERE Username = %s", (session['username'],))
        user_type = cursor.fetchone()['Login_type']
    connection.close()

    if user_type != 'Staff':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))

    report_types = [
        'Courier Report', 'Vendor Report', 'Category Report', 'Subcategory Report', 'Purchase Report', 
        'Sales Report', 'Customer Report', 'Staff Report', 'Item Report'
    ]

    if request.method == 'POST':
        report_type = request.form.get('report_type')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        if not report_type:
            flash('Please select a report type', 'danger')
            return render_template('admin_reports.html', report_types=report_types)

        today = datetime.now().date()
        if not start_date and not end_date:
            start_date = None
            end_date = None
        elif start_date and not end_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = today
            except ValueError:
                flash('Invalid start date format', 'danger')
                return render_template('admin_reports.html', report_types=report_types)
        elif start_date and end_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                if start_date > end_date:
                    flash('Start date cannot be after end date', 'danger')
                    return render_template('admin_reports.html', report_types=report_types)
            except ValueError:
                flash('Invalid date format', 'danger')
                return render_template('admin_reports.html', report_types=report_types)
        elif not start_date and end_date:
            flash('Please select a start date when an end date is provided', 'danger')
            return render_template('admin_reports.html', report_types=report_types)

        pdf_buffer = generate_pdf_report(report_type, start_date, end_date)
        filename = f"{report_type.replace(' ', '_')}_{today}.pdf"
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )

    return render_template('admin_reports.html', report_types=report_types)

def calculate_column_widths(table_data, font_name='Helvetica', font_size=10):
    """
    Calculate the width of each column based on the maximum content length,
    with special handling for Paragraph objects.
    Returns a list of widths in points.
    """
    page_width = letter[0] - 2 * 36  # 36 points (0.5 inch) margin on each side
    num_cols = len(table_data[0])
    max_widths = [0] * num_cols

    # Calculate the maximum width for each column
    for row in table_data:
        for col_idx, cell in enumerate(row):
            if isinstance(cell, Paragraph):
                text = cell.getPlainText()
                lines = text.split('\n') if '\n' in text else [text]
                max_line_width = max(stringWidth(line, font_name, font_size) for line in lines)
                width = max_line_width + 40
            else:
                text = str(cell)
                width = stringWidth(text, font_name, font_size)
            max_widths[col_idx] = max(max_widths[col_idx], width)

    # Calculate the total width of all columns
    total_content_width = sum(max_widths)

    # Scale down if total width exceeds page width, or distribute extra space
    if total_content_width > page_width:
        scale_factor = page_width / total_content_width
        max_widths = [width * scale_factor for width in max_widths]
    else:
        extra_space = (page_width - total_content_width) / num_cols
        max_widths = [width + extra_space for width in max_widths]

    # Apply minimum and maximum widths with special handling for "Name" column (index 1)
    max_widths = [
        max(min(width, 300 if col_idx == 2 else 150), 40 if col_idx != 1 else 80)
        for col_idx, width in enumerate(max_widths)
    ]
    # Ensure the Description column (index 2) gets more space if needed
    if num_cols > 2 and max_widths[2] < 200:
        remaining_space = page_width - sum(max_widths[:2] + max_widths[3:])
        max_widths[2] = min(remaining_space, 300)
    # Ensure the Name column (index 1) has enough space
    if num_cols > 1 and max_widths[1] < 100:
        remaining_space = page_width - sum(max_widths[:1] + max_widths[2:])
        max_widths[1] = min(remaining_space, 150)

    return max_widths

def generate_pdf_report(report_type, start_date, end_date):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    elements = []
    styles = getSampleStyleSheet()

# === Company Header ===
    logo_path = os.path.join('static', 'images', 'logo.jpg')
    company_name = "<b>Spice Bazaar</b>"
    company_address = (
        "Orient Square, Kadavanthra Junction, Kadavanthra,<br/>"
        "Ernakulam, Kerala 682020"
    )
    company_phone = "<b>Company Phone Number:</b> +91 8987562319"
    company_email = "<b>Company Email Address:</b> info@spicebazaar.com"

    style_normal = styles['Normal']
    style_normal.spaceAfter = 4

    if os.path.exists(logo_path):
        logo = Image(logo_path, width=0.9*inch, height=0.9*inch)
    else:
        logo = Paragraph("Bag Genie", styles['Title'])

    company_details = Paragraph(
        f"{company_name}<br/>{company_address}<br/>{company_phone}<br/>{company_email}",
        style_normal
    )

    header_table = Table([[logo, company_details]], colWidths=[1.2*inch, 5.8*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 12))

    # Title
    title = Paragraph(f"{report_type} - Spice Bazaar", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))

    # Date Range
    date_range = f"Date Range: {start_date if start_date else 'All'} to {end_date if end_date else 'All'}"
    elements.append(Paragraph(date_range, styles['Normal']))
    elements.append(Spacer(1, 12))

    # Fetch data based on report type
    connection = get_db_connection()
    with connection.cursor() as cursor:
        if report_type == 'Courier Report':
            query = """
                SELECT Courier_id, C_name, C_phone, C_join, Courier_status
                FROM tbl_courier
                WHERE (%s IS NULL OR C_join >= %s) AND (%s IS NULL OR C_join <= %s)
            """
            cursor.execute(query, (start_date, start_date, end_date, end_date))
            data = cursor.fetchall()
            headers = ['ID', 'Name', 'Phone', 'Join Date', 'Status']
            table_data = [headers] + [[row['Courier_id'], row['C_name'], row['C_phone'], 
                                     row['C_join'].strftime('%Y-%m-%d'), 
                                     'Active' if row['Courier_status'] else 'Inactive'] for row in data]

        elif report_type == 'Category Report':
            query = "SELECT Cat_id, Cat_name, Cat_desc, Cat_status FROM tbl_category"
            cursor.execute(query)
            data = cursor.fetchall()
            headers = ['ID', 'Name', 'Description', 'Status']
            table_data = [headers] + [
                [
                    row['Cat_id'],
                    row['Cat_name'],
                    Paragraph(row['Cat_desc'], style=styles['Normal']),
                    'Active' if row['Cat_status'] else 'Inactive'
                ] for row in data
            ]

        elif report_type == 'Subcategory Report':
            query = "SELECT s.Subcat_id, s.Subcat_name, c.Cat_name, s.Subcat_status FROM tbl_subcategory s JOIN tbl_category c ON s.Cat_id = c.Cat_id"
            cursor.execute(query)
            data = cursor.fetchall()
            headers = ['ID', 'Name','Category', 'Status']
            table_data = [headers] + [
                [
                    row['Subcat_id'],
                    row['Subcat_name'],
                    row['Cat_name'],
                    'Active' if row['Subcat_status'] else 'Inactive'
                ] for row in data
            ]

        elif report_type == 'Purchase Report':
            query = """
                SELECT pm.Pur_master_id, v.Vendor_name, pm.Pur_date, pm.Pur_tot_amt
                FROM tbl_purchase_master pm
                JOIN tbl_vendor v ON pm.Vendor_id = v.Vendor_id
                WHERE (%s IS NULL OR pm.Pur_date >= %s) AND (%s IS NULL OR pm.Pur_date <= %s)
            """
            cursor.execute(query, (start_date, start_date, end_date, end_date))
            data = cursor.fetchall()
            headers = ['ID', 'Vendor', 'Date', 'Total Amount']
            table_data = [headers] + [[row['Pur_master_id'], row['Vendor_name'], 
                                     row['Pur_date'].strftime('%Y-%m-%d'), row['Pur_tot_amt']] for row in data]

        elif report_type == 'Sales Report':
            query = """
                SELECT cm.Cart_master_id, cm.Cart_tot_amt, cm.Cart_item_status, p.Pay_date
                FROM tbl_cart_master cm
                LEFT JOIN tbl_payment p ON cm.Cart_master_id = p.Cart_master_id
                WHERE cm.Cart_item_status IN ('Paid', 'Out for Delivery', 'Delivered')
                AND (%s IS NULL OR p.Pay_date >= %s) AND (%s IS NULL OR p.Pay_date <= %s)
            """
            cursor.execute(query, (start_date, start_date, end_date, end_date))
            data = cursor.fetchall()
            headers = ['Cart ID', 'Total Amount', 'Status', 'Payment Date']
            table_data = [headers] + [[row['Cart_master_id'], row['Cart_tot_amt'], row['Cart_item_status'], 
                                     row['Pay_date'].strftime('%Y-%m-%d') if row['Pay_date'] else 'N/A'] for row in data]

        elif report_type == 'Customer Report':
            query = """
                SELECT Cust_id, Cust_fname, Cust_lname, Cust_phone, Cust_join, Cust_status
                FROM tbl_customer
                WHERE (%s IS NULL OR Cust_join >= %s) AND (%s IS NULL OR Cust_join <= %s)
            """
            cursor.execute(query, (start_date, start_date, end_date, end_date))
            data = cursor.fetchall()
            headers = ['ID', 'First Name', 'Last Name', 'Phone', 'Join Date', 'Status']
            table_data = [headers] + [[row['Cust_id'], row['Cust_fname'], row['Cust_lname'], 
                                     row['Cust_phone'], row['Cust_join'].strftime('%Y-%m-%d'), 
                                     'Active' if row['Cust_status'] else 'Inactive'] for row in data]

        elif report_type == 'Staff Report':
            query = """
                SELECT Staff_id, Staff_fname, Staff_lname, Staff_phone, Staff_join, Staff_status
                FROM tbl_staff
                WHERE (%s IS NULL OR Staff_join >= %s) AND (%s IS NULL OR Staff_join <= %s)
            """
            cursor.execute(query, (start_date, start_date, end_date, end_date))
            data = cursor.fetchall()
            headers = ['ID', 'First Name', 'Last Name', 'Phone', 'Join Date', 'Status']
            table_data = [headers] + [[row['Staff_id'], row['Staff_fname'], row['Staff_lname'], 
                                     row['Staff_phone'], row['Staff_join'].strftime('%Y-%m-%d'), 
                                     'Active' if row['Staff_status'] else 'Inactive'] for row in data]

        elif report_type == 'Vendor Report':
            query = """
                SELECT Vendor_id, Vendor_name, Vendor_email, Vendor_phone, Vendor_status
                FROM tbl_vendor
                WHERE (%s IS NULL OR Vendor_id >= %s) AND (%s IS NULL OR Vendor_id <= %s)
            """
            cursor.execute(query, (start_date, start_date, end_date, end_date))
            data = cursor.fetchall()
            headers = ['ID', 'Name', 'Email', 'Phone', 'Status']
            table_data = [headers] + [[row['Vendor_id'], row['Vendor_name'], row['Vendor_email'], 
                                     row['Vendor_phone'], 'Active' if row['Vendor_status'] else 'Inactive'] for row in data]

        elif report_type == 'Item Report':
            query = """
                SELECT i.Item_id, i.Item_name, i.Item_profit, i.Item_status, s.Subcat_name
                FROM tbl_item i
                JOIN tbl_subcategory s ON i.Subcat_id = s.Subcat_id
            """
            cursor.execute(query)
            data = cursor.fetchall()
            headers = ['ID', 'Name', 'Profit', 'Status', 'Subcategory']
            table_data = [headers] + [[row['Item_id'], row['Item_name'], 
                                     row['Item_profit'], 'Active' if row['Item_status'] else 'Inactive', 
                                     row['Subcat_name']] for row in data]

    connection.close()

    # Calculate dynamic column widths
    col_widths = calculate_column_widths(table_data)

    # Create Table with dynamic column widths
    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('WORDWRAP', (0, 1), (-1, -1), True),  # Enable word wrap for all columns
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(table)

    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer