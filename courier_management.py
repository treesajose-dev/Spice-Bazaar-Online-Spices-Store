import pymysql
from flask import request, redirect, url_for, flash,session
import re

import pymysql.cursors

def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="",
        database="spice_bazaar",
        cursorclass=pymysql.cursors.DictCursor,
    )

def get_all_couriers():  # Renamed from fetch_couriers to avoid naming conflict
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        query = """
SELECT 
    Courier_id, 
    Username, 
    C_cmpy_email, 
    C_name, 
    C_city, 
    C_dist, 
    C_pin, 
    C_street, 
    C_phone, 
    C_join, 
    Courier_status
FROM tbl_courier
ORDER BY C_join DESC;
        """
        cursor.execute(query)
        couriers = cursor.fetchall()
        print(couriers)
        return couriers
    except Exception as e:
        print(f"Error fetching couriers: {str(e)}")
        return []
    finally:
        connection.close()


def get_available_courier_usernames():
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
                # Query to fetch usernames from tbl_login where Login_type is "Courier" 
        # and Username is not in tbl_courier
        query = """
            SELECT Username 
            FROM tbl_login 
            WHERE Login_type = 'Courier' 
        """
        
        cursor.execute(query)
        result = cursor.fetchall()
        
        # Return the list of available usernames
        return result
    except Exception as e:
        print(f"Error fetching available courier usernames: {str(e)}")
        return []
    finally:
        connection.close()
'''
def cmpy_email_exists(c_cmpy_email, exclude_id=None):
    """Check if company email exists, excluding the current record during edits."""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        if exclude_id is None:
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM tbl_courier
                WHERE C_cmpy_email = %s""", (c_cmpy_email,))  # Fixed syntax error
        else:
            cursor.execute("""
                SELECT COUNT(*) AS count
                FROM tbl_courier
                WHERE C_cmpy_email = %s AND Courier_id != %s
            """, (c_cmpy_email, exclude_id))
        
        result = cursor.fetchone()
        return result['count'] > 0
    except Exception as e:
        print(f"Error checking company email existence: {str(e)}")
        return False
    finally:
        connection.close()
'''
def phonenumber_exists(c_phone, exclude_id=None):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        if exclude_id is None:
            cursor.execute("SELECT COUNT(*) AS count FROM tbl_courier WHERE C_phone = %s", (c_phone,))
        else:
            cursor.execute("""
                SELECT COUNT(*) AS count
                FROM tbl_courier
                WHERE C_phone = %s AND Courier_id != %s
            """, (c_phone, exclude_id))
        
        result = cursor.fetchone()
        return result['count'] > 0
    except Exception as e:
        print(f"Error checking phone number existence: {str(e)}")
        return False
    finally:
        connection.close()

#function to validate courier data before editing courier profile 
def validate_user_input(data, current_phone=None, courier_id=None):
    """Validate the user input data and return field-specific errors."""
    errors = {}

    # Phone validation
    if not data.get('c_phone'):
        errors['c_phone'] = "Phone number is required."
    elif not data['c_phone'].isdigit() or len(data['c_phone']) != 10:
        errors['c_phone'] = "Phone number must be 10 digits."
    elif data['c_phone'] != current_phone:  # Only check existence if phone number changed
        if phonenumber_exists(data['c_phone'], exclude_id=courier_id):
            errors['c_phone'] = "Phone number already exists."

    # Pin code validation
    if not data.get('c_pin'):
        errors['c_pin'] = "Pin code is required."
    elif not data['c_pin'].isdigit() or len(data['c_pin']) != 6:
        errors['c_pin'] = "Pin code must be 6 digits."

    # Other required fields with regex validation
    required_fields = ['c_name', 'c_cmpy_email','c_city', 'c_dist', 'c_street']
    field_regex = {
        'c_name': r"^[A-Za-z\s]+$",
        'c_cmpy_email': r"[^@]+@[^@]+\.[^@]+",
        'c_city': r"^[A-Za-z\s]+$",
        'c_dist': r"^[A-Za-z\s]+$",
        'c_street': r"^[A-Za-z\s]+$",
    }

    for field in required_fields:
        if not data.get(field):
            errors[field] = f"{field.replace('_', ' ').title()} is required."
        elif field in field_regex:
            # Validate using regex for specific fields
            if not re.match(field_regex[field], data[field]):
                errors[field] = f"Invalid {field.replace('_', ' ')} format."
                
            # Add length validation
            if field == 'c_name':
                if len(data[field]) > 10:
                    errors[field] = f"{field.replace('_', ' ').title()} must not exceed 10 characters."
                elif len(data[field]) < 1:
                    errors[field] = f"{field.replace('_', ' ').title()} must be at least 1 characters long."

            if field == 'c_cmpy_email':
                if len(data[field]) < 6:
                    errors[field] = f"{field.replace('_', ' ').title()} must be at least 6 characters long."
                elif len(data[field]) > 30:
                    errors[field] = f"{field.replace('_', ' ').title()} must not exceed 30 characters."

            if field in ['c_city', 'c_dist']:
                if len(data[field]) > 12:
                    errors[field] = f"{field.replace('_', ' ').title()} must not exceed 12 characters."
                elif len(data[field]) < 3:
                    errors[field] = f"{field.replace('_', ' ').title()} must be at least 3 characters long."

            if field == 'c_street':
                if len(data[field]) > 15:
                    errors[field] = f"{field.replace('_', ' ').title()} must not exceed 15 characters."
                elif len(data[field]) < 5:
                    errors[field] = f"{field.replace('_', ' ').title()} must be at least 5 characters long."

    return errors


def username_exists_in_courier(username, exclude_id=None):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        if exclude_id is None:
            cursor.execute("SELECT COUNT(*) AS count FROM tbl_courier WHERE Username = %s", (username,))
        else:
            cursor.execute("""
                SELECT COUNT(*) AS count 
                FROM tbl_courier 
                WHERE Username = %s AND Courier_id != %s
            """, (username, exclude_id))

        result = cursor.fetchone()
        return result['count'] > 0
    except Exception as e:
        print(f"Error checking courier username existence: {str(e)}")
        return False
    finally:
        connection.close()


def validate_courier_input(data, courier_id=None):
    """
    Validate courier input data, with special handling for edit operations.
    """
    errors = {}

    # Username validation
    if not data.get('username'):
        errors['username'] = "Username is required."


    # Existing validations
    if not data.get('c_phone'):
        errors['c_phone'] = "Phone number is required."
    elif not data['c_phone'].isdigit() or len(data['c_phone']) != 10:
        errors['c_phone'] = "Phone number must be 10 digits."


    # Pin code validation
    if not data.get('c_pin'):
        errors['c_pin'] = "Pin code is required."
    elif not data['c_pin'].isdigit() or len(data['c_pin']) != 6:
        errors['c_pin'] = "Pin code must be 6 digits."

    # Email validation
    if not data.get('c_cmpy_email'):
        errors['c_cmpy_email'] = "Company email is required."
    # cmpy_email validation
    elif not re.match(r"[^@]+@[^@]+\.[^@]+", data['c_cmpy_email']):
        errors['c_cmpy_email'] = "Invalid email address format."
    elif len(data["c_cmpy_email"]) < 6:
        errors['c_cmpy_email'] = "Company email must be at least 6 characters long."
    elif len(data["c_cmpy_email"]) > 20:
        errors['c_cmpy_email'] = "Company email must not exceed 20 characters."   

 
    # Company name validation
    if not data.get('c_name'):
        errors['c_name'] = "Company name is required."


    # Other required fields with regex validation
    required_fields = ['c_name', 'c_city', 'c_dist', 'c_street']
    field_regex = {
    'c_name': r"^[A-Za-z\s]+$",
    'c_city': r"^[A-Za-z\s]+$",
    'c_dist': r"^[A-Za-z\s]+$",
    'c_street': r"^[A-Za-z\s]+$"
    }

    for field in required_fields:
        if not data.get(field):
            errors[field] = f"{field.replace('c_', '').replace('_', ' ').title()} is required."
        elif field in field_regex:
            if not re.match(field_regex[field], data[field]):
                errors[field] = f"Invalid {field.replace('c_', '').replace('_', ' ')} format."
            
            if field == 'c_name':
                if len(data[field]) > 15:
                    errors[field] = "Company name must not exceed 15 characters."
                elif len(data[field]) < 1:
                    errors[field] = "Company name must be at least 1 character long."

            if field in ['c_city', 'c_dist']:
                if len(data[field]) > 12:
                    errors[field] = f"{field.replace('c_', '').replace('_', ' ').title()} must not exceed 12 characters."
                elif len(data[field]) < 3:
                    errors[field] = f"{field.replace('c_', '').replace('_', ' ').title()} must be at least 3 characters long."

            if field == 'c_street':
                if len(data[field]) > 15:
                    errors[field] = "Street must not exceed 15 characters."
                elif len(data[field]) < 5:
                    errors[field] = "Street must be at least 5 characters long."

    return errors

def add_courier():
    if request.method == "POST":
        if 'staff_id' not in session:
            flash("Unauthorized access!", "danger")
            return redirect(url_for("login"))  # Redirect to login if not authenticated

        staff_id = session['staff_id']  # Get staff_id of logged-in user
        data = {
            'username': request.form.get("username"),
            'c_cmpy_email': request.form.get("c_cmpy_email"),
            'c_name': request.form.get("c_name"),
            'c_city': request.form.get("c_city"),
            'c_dist': request.form.get("c_dist"),
            'c_pin': request.form.get("c_pin"),
            'c_street': request.form.get("c_street"),
            'c_phone': request.form.get("c_phone")
        }

        # Validate the courier data
        errors = validate_courier_input(data)
                
        # Check if validation failed
        if errors:
            for field, error in errors.items():
                flash(error, "danger")
            return redirect(url_for("courier_management"))
        '''
        # Check for existing company email 
        if cmpy_email_exists(data['c_cmpy_email']):
            flash(f"Company Email '{data['c_cmpy_email']}' already exists!", "danger")
            return redirect(url_for("courier_management"))'''
    
        # Check for existing company phone number 
        if phonenumber_exists(data['c_phone']):
            flash(f"Company phone number '{data['c_phone']}' already exists!", "danger")
            return redirect(url_for("courier_management"))
        '''
        # Check if courier company name already exists
        if courier_exists(data['c_name']):
            flash(f"Company name '{data['c_name']}' already exists!", "danger")
            return redirect(url_for("courier_management"))'''
    
        # Check if courier username already exists
        if username_exists_in_courier(data['username']):
            flash(f"Username '{data['username']}' already exists!", "danger")
            return redirect(url_for("courier_management"))

        try:
            connection = get_db_connection()
            cursor = connection.cursor()

            # Insert courier data into the tbl_courier
            query = """
                INSERT INTO tbl_courier 
                (Staff_id, Username, C_cmpy_email, C_name, C_city, C_dist, C_pin, C_street, C_phone, C_join, Courier_status) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), 1)
            """
            cursor.execute(query, (
                staff_id, 
                data['username'],
                data['c_cmpy_email'],
                data['c_name'],
                data['c_city'],
                data['c_dist'],
                data['c_pin'],
                data['c_street'],
                data['c_phone']
            ))
            connection.commit()

            # ✅ Update login_status to 1 in tbl_login for the username
            update_query = "UPDATE tbl_login SET Login_status = 1 WHERE Username = %s"
            cursor.execute(update_query, (data['username'],))
            connection.commit()  # Commit the update

            flash("Courier added successfully!", "success")
        except Exception as e:
            flash(f"Error adding courier: {str(e)}", "danger")
        finally:
            connection.close()

        return redirect(url_for("courier_management"))

def change_courier_status(Courier_id, status):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Update courier status in tbl_courier
        cursor.execute("UPDATE tbl_courier SET Courier_status = %s WHERE Courier_id = %s", (status, Courier_id))

        # Update login status in tbl_login based on Username
        cursor.execute("""
            UPDATE tbl_login 
            SET Login_status = %s 
            WHERE Username = (SELECT Username FROM tbl_courier WHERE Courier_id = %s)
        """, (status, Courier_id))

        connection.commit()
        flash("Courier status updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating courier status: {str(e)}", "danger")
    finally:
        connection.close()

def fetch_edit_courier(courier_id):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        query = """
            SELECT Courier_id, Username, C_cmpy_email, C_name, C_city, C_dist, C_pin, 
                   C_street, C_phone, C_join, Courier_status 
            FROM tbl_courier WHERE Courier_id = %s
        """
        cursor.execute(query, (courier_id,))
        courier = cursor.fetchone()
        
        print("Debug - Fetched courier data:", courier)  # Debug print
        
        if courier:
            return courier 
        else: 
            None
        
    except Exception as e:
        print(f"Error fetching courier for editing: {str(e)}")
        return None
    finally:
        connection.close()

def edit_courier(courier_id):
    if request.method == "POST":
        # Retrieve form data
        '''
        username = request.form.get("username")
        c_cmpy_email = request.form.get("c_cmpy_email")
        c_name = request.form.get("c_name")
        c_city = request.form.get("c_city")
        c_dist = request.form.get("c_dist")
        c_pin = request.form.get("c_pin")
        c_street = request.form.get("c_street")
        c_phone = request.form.get("c_phone")'''

        data = {
            'username': request.form.get("username"),
            'c_cmpy_email': request.form.get("c_cmpy_email"),
            'c_name': request.form.get("c_name"),
            'c_city': request.form.get("c_city"),
            'c_dist': request.form.get("c_dist"),
            'c_pin': request.form.get("c_pin"),
            'c_street': request.form.get("c_street"),
            'c_phone': request.form.get("c_phone")
        }

        # Validate required fields
        if not data['username'] or not data['c_cmpy_email'] or not data['c_name'] or not data['c_phone']:
            flash("All required fields must be filled!", "danger")
            return redirect(url_for("courier_management"))
        
        # Validate the courier data
        errors = validate_courier_input(data)

        # Check if validation failed
        if errors:
            for field, error in errors.items():
                flash(error, "danger")
            return redirect(url_for("courier_management"))
        '''
        # Check for existing company email 
        if cmpy_email_exists(data['c_cmpy_email'], exclude_id=courier_id):
            flash(f"Company Email '{data['c_cmpy_email']}' already exists!", "danger")
            return redirect(url_for("courier_management"))'''
    
        # Check for existing company phone number 
        if phonenumber_exists(data['c_phone'], exclude_id=courier_id):
            flash(f"Company phone number '{data['c_phone']}' already exists!", "danger")
            return redirect(url_for("courier_management"))
        '''
        # Check if courier company name already exists
        if courier_exists(data['c_name'], exclude_id=courier_id):
            flash(f"Company name '{data['c_name']}' already exists!", "danger")
            return redirect(url_for("courier_management"))'''
    
        # Check if courier username already exists
        if username_exists_in_courier(data['username'], exclude_id=courier_id):
            flash(f"Username '{data['username']}' already exists!", "danger")
            return redirect(url_for("courier_management"))

        try:
            # Connect to the database
            connection = get_db_connection()
            cursor = connection.cursor()

            # Update the courier details
            query = """
                UPDATE tbl_courier 
                SET Username = %s, C_cmpy_email = %s, C_name = %s, C_city = %s, 
                    C_dist = %s, C_pin = %s, C_street = %s, C_phone = %s
                WHERE Courier_id = %s
            """
            cursor.execute(query, (data['username'], data['c_cmpy_email'], data['c_name'], 
                                   data['c_city'], data['c_dist'], 
                                   data['c_pin'], data['c_street'], data['c_phone'], courier_id))

            # Commit the transaction
            connection.commit()
            flash("Courier details updated successfully!", "success")
        except Exception as e:
            # Log the error and show a user-friendly message
            print(f"Error updating courier: {str(e)}")  # Log the full error for debugging
            flash(f"Error updating courier: {str(e)}", "danger")
        finally:
            # Close the database connection
            if connection:
                connection.close()

        # Redirect to the courier management page
        return redirect(url_for("courier_management"))