import pymysql
from flask import request, redirect, url_for, flash, session
import re

def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="",
        database="spice_bazaar",
        cursorclass=pymysql.cursors.DictCursor,
    )

def get_all_vendors():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        query = """
            SELECT 
                Vendor_id, Vendor_name, Vendor_email, 
                Vendor_city, Vendor_dist, Vendor_pin, Vendor_street, Vendor_phone, 
                Vendor_status
            FROM tbl_vendor 
            ORDER BY Vendor_id DESC
        """
        cursor.execute(query)
        vendors = cursor.fetchall()
        return vendors
    except Exception as e:
        print(f"Error fetching vendors: {str(e)}")
        return []
    finally:
        connection.close()

def vendor_email_exists(vendor_email, exclude_id=None):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        if exclude_id is None:
            cursor.execute("SELECT COUNT(*) AS count FROM tbl_vendor WHERE Vendor_email = %s", (vendor_email,))
        else:
            cursor.execute("SELECT COUNT(*) AS count FROM tbl_vendor WHERE Vendor_email = %s AND Vendor_id != %s", (vendor_email, exclude_id))
        
        result = cursor.fetchone()
        return result['count'] > 0
    except Exception as e:
        print(f"Error checking vendor email existence: {str(e)}")
        return False
    finally:
        connection.close()

def vendor_phone_exists(vendor_phone, exclude_id=None):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        if exclude_id is None:
            cursor.execute("SELECT COUNT(*) AS count FROM tbl_vendor WHERE Vendor_phone = %s", (vendor_phone,))
        else:
            cursor.execute("SELECT COUNT(*) AS count FROM tbl_vendor WHERE Vendor_phone = %s AND Vendor_id != %s", (vendor_phone, exclude_id))
        
        result = cursor.fetchone()
        return result['count'] > 0
    except Exception as e:
        print(f"Error checking vendor phone existence: {str(e)}")
        return False
    finally:
        connection.close()

#vendor name exists
def vendor_exists(vendor_name, exclude_id=None):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        if exclude_id is None:
            cursor.execute("SELECT COUNT(*) AS count FROM tbl_vendor WHERE Vendor_name = %s", (vendor_name,))
        else:
            cursor.execute("""
                SELECT COUNT(*) AS count 
                FROM tbl_vendor
                WHERE Vendor_name = %s AND vendor_id != %s
            """, (vendor_name, exclude_id))
            
        result = cursor.fetchone()
        return result['count'] > 0
    except Exception as e:
        print(f"Error checking vendor existence: {str(e)}")
        return False
    finally:
        connection.close()

def validate_vendor_input(data):
    errors = {}

    if not data.get('vendor_name'):
        errors['vendor_name'] = "Vendor name is required."
    elif len(data['vendor_name']) > 15:
        errors['vendor_name'] = "Vendor name must not exceed 15 characters."

    # Pin code validation
    if not data.get('vendor_pin'):
        errors['vendor_pin'] = "Pin code is required."
    elif not data['vendor_pin'].isdigit() or len(data['vendor_pin']) != 6:
        errors['vendor_pin'] = "Pin code must be 6 digits."
    
    if not data.get('vendor_email'):
        errors['vendor_email'] = "Vendor email is required."
    elif not re.match(r"[^@]+@[^@]+\.[^@]+", data['vendor_email']):
        errors['vendor_email'] = "Invalid email address format."
    
    if not data.get('vendor_phone'):
        errors['vendor_phone'] = "Phone number is required."
    elif not data['vendor_phone'].isdigit() or len(data['vendor_phone']) != 10:
        errors['vendor_phone'] = "Phone number must be 10 digits."

    required_fields = ['vendor_city', 'vendor_dist', 'vendor_pin', 'vendor_street']
    field_regex = {
        'vendor_name': r"^[A-Za-z\s]+$",  # Only letters & spaces
        'vendor_city': r"^[A-Za-z\s]+$",  # Only letters & spaces
        'vendor_dist': r"^[A-Za-z\s]+$",  # Only letters & spaces
        'vendor_street': r"^[A-Za-z\s]+$", # Only letters & spaces
    }

    for field in required_fields:
        if not data.get(field):
            errors[field] = f"{field.replace('_', ' ').title()} is required."
            continue  # Skip further validation if field is missing

        # Apply regex validation
        if field in field_regex and not re.match(field_regex[field], data[field]):
            errors[field] = f"Invalid {field.replace('_', ' ').title()} format."

        if field == 'vendor_city' or field == 'vendor_dist':
            if len(data[field]) > 12:
                errors[field] = f"{field.replace('vendor_', '').replace('_', ' ').title()} must not exceed 12 characters."
            elif len(data[field]) < 3:
                errors[field] = f"{field.replace('vendor_', '').replace('_', ' ').title()} must be at least 3 characters long."

        if field == 'vendor_street':
            if len(data[field]) > 15:
                errors[field] = "Street must not exceed 15 characters."
            elif len(data[field]) < 5:
                errors[field] = "Street must be at least 5 characters long."
    
    return errors

def add_vendor():
    if request.method == "POST":
        if 'staff_id' not in session:
            flash("Unauthorized access!", "danger")
            return redirect(url_for("login"))  # Redirect to login if not authenticated

        staff_id = session['staff_id']  # Get staff_id of logged-in user
        data = {
            'vendor_name': request.form.get("vendor_name"),
            'vendor_email': request.form.get("vendor_email"),
            'vendor_city': request.form.get("vendor_city"),
            'vendor_dist': request.form.get("vendor_dist"),
            'vendor_pin': request.form.get("vendor_pin"),
            'vendor_street': request.form.get("vendor_street"),
            'vendor_phone': request.form.get("vendor_phone")
        }

        errors = validate_vendor_input(data)
        if errors:
            for error in errors.values():
                flash(error, "danger")
            return redirect(url_for("vendor_management"))

        if vendor_email_exists(data['vendor_email']):
            flash(f"Vendor email '{data['vendor_email']}' already exists!", "danger")
            return redirect(url_for("vendor_management"))

        if vendor_phone_exists(data['vendor_phone']):
            flash(f"Vendor phone '{data['vendor_phone']}' already exists!", "danger")
            return redirect(url_for("vendor_management"))
        
        # Check if vendor name already exists
        if vendor_exists(data['vendor_name']):
            flash(f"Vendor name '{data['vendor_name']}' already exists!", "danger")
            return redirect(url_for("vendor_management"))
        
        try:
            connection = get_db_connection()
            cursor = connection.cursor()

            query = """
                INSERT INTO tbl_vendor 
                (Staff_id, Vendor_name, Vendor_email, Vendor_city, Vendor_dist, Vendor_pin, Vendor_street, Vendor_phone, Vendor_status) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1)
            """
            cursor.execute(query, (
                staff_id,  # Staff_id (hardcoded as 1 for now)
                data['vendor_name'],
                data['vendor_email'],
                data['vendor_city'],
                data['vendor_dist'],
                data['vendor_pin'],
                data['vendor_street'],
                data['vendor_phone']
            ))
            connection.commit()
            flash("Vendor added successfully!", "success")
        except Exception as e:
            flash(f"Error adding vendor: {str(e)}", "danger")
        finally:
            connection.close()

        return redirect(url_for("vendor_management"))

def change_vendor_status(vendor_id, status):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("UPDATE tbl_vendor SET Vendor_status = %s WHERE Vendor_id = %s", (status, vendor_id))
        connection.commit()
        flash("Vendor status updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating vendor status: {str(e)}", "danger")
    finally:
        connection.close()

def fetch_edit_vendor(vendor_id):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        query = """
            SELECT Vendor_id, Vendor_name, Vendor_email, Vendor_city, 
                   Vendor_dist, Vendor_pin, Vendor_street, Vendor_phone, Vendor_status 
            FROM tbl_vendor WHERE Vendor_id = %s
        """
        cursor.execute(query, (vendor_id,))
        vendor = cursor.fetchone()
        
        print("Debug - Fetched vendor data:", vendor)  # Debug print
        
        if vendor:
            return vendor 
        else: 
            return None
        
    except Exception as e:
        print(f"Error fetching vendor for editing: {str(e)}")
        return None
    finally:
        connection.close()

def edit_vendor(vendor_id):
    if request.method == "POST":
        data = {
            'vendor_name': request.form.get("vendor_name"),
            'vendor_email': request.form.get("vendor_email"),
            'vendor_city': request.form.get("vendor_city"),
            'vendor_dist': request.form.get("vendor_dist"),
            'vendor_pin': request.form.get("vendor_pin"),
            'vendor_street': request.form.get("vendor_street"),
            'vendor_phone': request.form.get("vendor_phone")
        }

        # Validate required fields
        errors = validate_vendor_input(data)
        if errors:
            for field, error in errors.items():
                flash(error, "danger")
            return redirect(url_for("vendor_management"))

        # Check for existing vendor email 
        if vendor_email_exists(data['vendor_email'], exclude_id=vendor_id):
            flash(f"Vendor email '{data['vendor_email']}' already exists!", "danger")
            return redirect(url_for("vendor_management"))
    
        # Check for existing vendor phone number 
        if vendor_phone_exists(data['vendor_phone'], exclude_id=vendor_id):
            flash(f"Vendor phone '{data['vendor_phone']}' already exists!", "danger")
            return redirect(url_for("vendor_management"))

        # Check if vendor company name already exists
        if vendor_exists(data['vendor_name'], exclude_id=vendor_id):
            flash(f"Vendor name '{data['vendor_name']}' already exists!", "danger")
            return redirect(url_for("vendor_management"))
        
        try:
            # Connect to the database
            connection = get_db_connection()
            cursor = connection.cursor()

            # Update the vendor details
            query = """
                UPDATE tbl_vendor 
                SET Vendor_name = %s, Vendor_email = %s, Vendor_city = %s, 
                    Vendor_dist = %s, Vendor_pin = %s, Vendor_street = %s, Vendor_phone = %s
                WHERE Vendor_id = %s
            """
            cursor.execute(query, (
                data['vendor_name'], data['vendor_email'],
                data['vendor_city'], data['vendor_dist'],
                data['vendor_pin'], data['vendor_street'], data['vendor_phone'], vendor_id
            ))

            # Commit the transaction
            connection.commit()
            flash("Vendor details updated successfully!", "success")
        except Exception as e:
            # Log the error and show a user-friendly message
            print(f"Error updating vendor: {str(e)}")  # Log the full error for debugging
            flash(f"Error updating vendor: {str(e)}", "danger")
        finally:
            # Close the database connection
            if connection:
                connection.close()

        # Redirect to the vendor management page
        return redirect(url_for("vendor_management"))

