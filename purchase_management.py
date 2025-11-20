import pymysql
from flask import request, redirect, url_for, flash, session
from datetime import datetime

def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="",
        database="spice_bazaar",
        cursorclass=pymysql.cursors.DictCursor
    )

def fetch_vendors():
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT Vendor_id, Vendor_name 
            FROM tbl_vendor 
            WHERE Vendor_status = 1
            ORDER BY Vendor_name
        """)
        return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching vendors: {str(e)}")
        return []
    finally:
        connection.close()

def fetch_items():
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT Item_id, Item_name 
            FROM tbl_item 
            WHERE Item_status = 1
            ORDER BY Item_name
        """)
        return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching items: {str(e)}")
        return []
    finally:
        connection.close()
'''
def fetch_purchases():
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT pm.Pur_master_id, v.Vendor_name, pm.Pur_date, pm.Pur_tot_amt
            FROM tbl_purchase_master pm
            JOIN tbl_vendor v ON pm.Vendor_id = v.Vendor_id
            ORDER BY pm.Pur_date DESC
        """)
        purchases = cursor.fetchall()
        
        # Format dates
        for purchase in purchases:
            purchase['Pur_date'] = purchase['Pur_date'].strftime('%Y-%m-%d')
            
        return purchases
    except Exception as e:
        print(f"Error fetching purchases: {str(e)}")
        return []
    finally:
        connection.close()
'''
def get_staff_id_from_username(username):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT Staff_id FROM tbl_staff WHERE Staff_username = %s", (username,))
        result = cursor.fetchone()
        return result[0] if result else None  # Access the result by index (0 for Staff_id)
    except Exception as e:
        print(f"Error fetching staff ID: {str(e)}")
        return None
    finally:
        connection.close()

def validate_purchase_data(vendor_id, pur_date, item_ids, pur_qtys, pur_unit_prices, 
                         pur_unit_weights, batch_nos, expiry_dates, item_doms):
    errors = []
    
    if not vendor_id:
        errors.append("Vendor must be selected")
    
    try:
        datetime.strptime(pur_date, '%Y-%m-%d')
    except ValueError:
        errors.append("Invalid purchase date format")
    
    arrays = [item_ids, pur_qtys, pur_unit_prices, pur_unit_weights, batch_nos, expiry_dates, item_doms]
    if not all(len(arr) == len(item_ids) for arr in arrays):
        errors.append("Invalid form data")
        return errors
    
    for i in range(len(item_ids)):
        if not item_ids[i]:
            errors.append(f"Item #{i+1}: Item must be selected")
        
        try:
            qty = int(pur_qtys[i])
            if qty < 1 or qty > 30:
                errors.append(f"Item #{i+1}: Quantity must be between 1 and 30")
        except ValueError:
            errors.append(f"Item #{i+1}: Invalid quantity")
        
        try:
            price = float(pur_unit_prices[i])
            if price <= 0:
                errors.append(f"Item #{i+1}: Price must be positive")
        except ValueError:
            errors.append(f"Item #{i+1}: Invalid price")
        
        try:
            weight = float(pur_unit_weights[i])
            if weight <= 0:
                errors.append(f"Item #{i+1}: Weight must be positive")
            elif weight >= 10000:  # Ensures it does not exceed 4 digits
                errors.append(f"Item #{i+1}: Weight can have a maximum of 4 digits")
        except ValueError:
            errors.append(f"Item #{i+1}: Invalid weight value")

        if not batch_nos[i] or not batch_nos[i].isalnum() or len(batch_nos[i]) > 5:
            errors.append(f"Item #{i+1}: Invalid batch number")
        
        try:
            datetime.strptime(expiry_dates[i], '%Y-%m-%d')
        except ValueError:
            errors.append(f"Item #{i+1}: Invalid expiry date format")
        
        try:
            datetime.strptime(item_doms[i], '%Y-%m-%d')
        except ValueError:
            errors.append(f"Item #{i+1}: Invalid date of manufacture format")

    return errors

def add_purchase():
    if request.method == "POST":
        if 'staff_id' not in session:
            flash("Unauthorized access!", "danger")
            return redirect(url_for("login"))  # Redirect to login if not authenticated

        staff_id = session['staff_id']  # Get staff_id of logged-in user

        vendor_id = request.form.get('vendor_id')
        pur_date = request.form.get('pur_date')
        item_ids = request.form.getlist('item_id[]')
        pur_qtys = request.form.getlist('pur_qty[]')
        pur_unit_prices = request.form.getlist('pur_unit_price[]')
        pur_unit_weights = request.form.getlist('pur_unit_weight[]')
        batch_nos = request.form.getlist('batch_no[]')
        expiry_dates = request.form.getlist('expiry_date[]')
        item_doms = request.form.getlist('item_dom[]')

        errors = validate_purchase_data(vendor_id, pur_date, item_ids, pur_qtys, 
                                     pur_unit_prices, pur_unit_weights, batch_nos, expiry_dates, item_doms)
        if errors:
            for error in errors:
                flash(error, "danger")
            return redirect(url_for('purchase_management'))

        connection = get_db_connection()
        try:
            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO tbl_purchase_master (Staff_id, Vendor_id, Pur_date, Pur_tot_amt) 
                VALUES (%s, %s, %s, 0)
            """, (staff_id,vendor_id, pur_date))
            
            pur_master_id = cursor.lastrowid
            total_amount = 0

            for i in range(len(item_ids)):
                item_id = item_ids[i]
                pur_qty = int(pur_qtys[i])
                pur_unit_price = float(pur_unit_prices[i])
                pur_unit_weight = float(pur_unit_weights[i])
                
                cursor.execute("SELECT Item_profit FROM tbl_item WHERE Item_id = %s", (item_id,))
                item_result = cursor.fetchone()
                item_profit = float(item_result['Item_profit']) / 100
                sell_price = pur_unit_price + (pur_unit_price * item_profit)
                total_amount += pur_qty * pur_unit_price

                cursor.execute("""
                    INSERT INTO tbl_purchase_child 
                    (Pur_master_id, Item_id, Pur_qty, Pur_unit_price, Pur_unit_weight, Stock, 
                     Sell_price, Batch_no, Expiry_date, Item_dom)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (pur_master_id, item_id, pur_qty, pur_unit_price, pur_unit_weight, pur_qty, 
                     sell_price, batch_nos[i], expiry_dates[i], item_doms[i]))

            cursor.execute("""
                UPDATE tbl_purchase_master 
                SET Pur_tot_amt = %s 
                WHERE Pur_master_id = %s
            """, (total_amount, pur_master_id))

            connection.commit()
            flash("Purchase added successfully!", "success")
            
        except Exception as e:
            connection.rollback()
            flash(f"Error adding purchase: {str(e)}", "danger")
        finally:
            connection.close()

        return redirect(url_for('purchase_management'))
    
def edit_purchase(pur_master_id):
    if request.method == "POST":
        vendor_id = request.form.get('vendor_id')
        pur_date = request.form.get('pur_date')
        item_ids = request.form.getlist('item_id[]')
        pur_qtys = request.form.getlist('pur_qty[]')
        pur_unit_prices = request.form.getlist('pur_unit_price[]')
        pur_unit_weights = request.form.getlist('pur_unit_weight[]')
        batch_nos = request.form.getlist('batch_no[]')
        expiry_dates = request.form.getlist('expiry_date[]')
        item_doms = request.form.getlist('item_dom[]')

        errors = validate_purchase_data(vendor_id, pur_date, item_ids, pur_qtys, 
                                     pur_unit_prices, pur_unit_weights, batch_nos, expiry_dates, item_doms)
        if errors:
            for error in errors:
                flash(error, "danger")
            return redirect(url_for('edit_purchase_route', pur_master_id=pur_master_id))

        connection = get_db_connection()
        try:
            cursor = connection.cursor()

            # Update the purchase master details
            cursor.execute("""
                UPDATE tbl_purchase_master 
                SET Vendor_id = %s, Pur_date = %s 
                WHERE Pur_master_id = %s
            """, (vendor_id, pur_date, pur_master_id))

            # Fetch existing child entries
            cursor.execute("""
                SELECT Pur_child_id, Pur_qty, Pur_unit_price FROM tbl_purchase_child WHERE Pur_master_id = %s
            """, (pur_master_id,))
            existing_children = cursor.fetchall()
            existing_child_ids = {child['Pur_child_id']: (child['Pur_qty'], child['Pur_unit_price']) for child in existing_children}

            total_amount = 0  # Variable to accumulate total amount

            for i in range(len(item_ids)):
                item_id = item_ids[i]
                pur_qty = int(pur_qtys[i])
                pur_unit_price = float(pur_unit_prices[i])
                pur_unit_weight = float(pur_unit_weights[i])

                cursor.execute("SELECT Item_profit FROM tbl_item WHERE Item_id = %s", (item_id,))
                item_result = cursor.fetchone()
                item_profit = float(item_result['Item_profit']) / 100
                sell_price = pur_unit_price + (pur_unit_price * item_profit)

                if i < len(existing_child_ids):
                    pur_child_id = list(existing_child_ids.keys())[i]
                    old_qty, old_price = existing_child_ids[pur_child_id]

                    # Check if qty or price has changed
                    if pur_qty != old_qty or pur_unit_price != old_price:
                        # Update existing purchase child records
                        cursor.execute("""
                            UPDATE tbl_purchase_child 
                            SET Item_id = %s, Pur_qty = %s, Pur_unit_price = %s, 
                                Pur_unit_weight = %s, Stock = %s, Sell_price = %s, 
                                Batch_no = %s, Expiry_date = %s, Item_dom = %s
                            WHERE Pur_child_id = %s
                        """, (item_id, pur_qty, pur_unit_price, pur_unit_weight, pur_qty, 
                              sell_price, batch_nos[i], expiry_dates[i], item_doms[i], 
                              pur_child_id))

                    # Calculate total amount incrementally
                    total_amount += pur_qty * pur_unit_price

                else:
                    # Insert new purchase child records if needed
                    cursor.execute("""
                        INSERT INTO tbl_purchase_child 
                        (Pur_master_id, Item_id, Pur_qty, Pur_unit_price, Pur_unit_weight, Stock, 
                         Sell_price, Batch_no, Expiry_date, Item_dom)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (pur_master_id, item_id, pur_qty, pur_unit_price, pur_unit_weight, pur_qty, 
                          sell_price, batch_nos[i], expiry_dates[i], item_doms[i]))
                    
                    # Calculate total amount incrementally
                    total_amount += pur_qty * pur_unit_price

            # Update the purchase total amount in the master table
            cursor.execute("""
                UPDATE tbl_purchase_master 
                SET Pur_tot_amt = %s 
                WHERE Pur_master_id = %s
            """, (total_amount, pur_master_id))

            connection.commit()
            flash("Purchase updated successfully!", "success")
        except Exception as e:
            connection.rollback()
            flash(f"Error updating purchase: {str(e)}", "danger")
        finally:
            connection.close()

        return redirect(url_for('purchase_management'))


def fetch_purchase_for_edit(pur_master_id):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()

        # Fetch master purchase details
        cursor.execute("""
            SELECT pm.Pur_master_id, pm.Vendor_id, pm.Pur_date 
            FROM tbl_purchase_master pm
            WHERE pm.Pur_master_id = %s
        """, (pur_master_id,))
        purchase_master = cursor.fetchone()

        # Fetch purchase child details
        cursor.execute("""
            SELECT pc.Pur_child_id, pc.Item_id, pc.Pur_qty, pc.Pur_unit_price, 
                   pc.Pur_unit_weight, pc.Batch_no, pc.Expiry_date, pc.Item_dom, 
                   i.Item_name 
            FROM tbl_purchase_child pc
            JOIN tbl_item i ON pc.Item_id = i.Item_id
            WHERE pc.Pur_master_id = %s
        """, (pur_master_id,))
        purchase_children = cursor.fetchall()

        return purchase_master, purchase_children
    except Exception as e:
        print(f"Error fetching purchase for edit: {str(e)}")
        return None, []
    finally:
        connection.close()

'''
def fetch_purchase_details(pur_master_id):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT pc.*, i.Item_name,
                   DATE_FORMAT(pc.Expiry_date, '%%Y-%%m-%%d') as Expiry_date,
                   DATE_FORMAT(pc.Item_dom, '%%Y-%%m-%%d') as Item_dom
            FROM tbl_purchase_child pc
            JOIN tbl_item i ON pc.Item_id = i.Item_id
            WHERE pc.Pur_master_id = %s
        """, (pur_master_id,))
        return cursor.fetchall()
    except Exception as e:
        flash(f"Error retrieving purchase details: {str(e)}", "danger")
        return redirect(url_for('purchase_management'))
    finally:
        connection.close()

def fetch_purchase_by_id(pur_master_id):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT pm.Pur_master_id, v.Vendor_name, pm.Pur_date, pm.Pur_tot_amt
            FROM tbl_purchase_master pm
            JOIN tbl_vendor v ON pm.Vendor_id = v.Vendor_id
            WHERE pm.Pur_master_id = %s
        """, (pur_master_id,))
        purchase = cursor.fetchone()
        
        if purchase:
            purchase['Pur_date'] = purchase['Pur_date'].strftime('%Y-%m-%d')
            
        return purchase
    except Exception as e:
        print(f"Error fetching purchase: {str(e)}")
        return None
    finally:
        connection.close()
'''