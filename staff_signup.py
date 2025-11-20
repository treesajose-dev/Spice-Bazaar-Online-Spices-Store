import pymysql
from datetime import datetime
import re

def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="",
        database="spice_bazaar",
        cursorclass=pymysql.cursors.DictCursor,
    )

def phonenumber_exists(phone, exclude_id=None):
    """Check if the phone number already exists in the tbl_staff table."""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            if exclude_id is None:
                sql = "SELECT COUNT(*) as count FROM tbl_staff WHERE Staff_phone = %s"
                cursor.execute(sql, (phone,))
            else:
                sql = "SELECT COUNT(*) as count FROM tbl_staff WHERE Staff_phone = %s AND Staff_id != %s"
                cursor.execute(sql, (phone, exclude_id))

            result = cursor.fetchone()
            return result['count'] > 0
    finally:
        connection.close()

def validate_user_input(data, current_phone=None, staff_id=None):
    """Validate the user input data and return field-specific errors."""
    errors = {}

    # Phone validation
    if not data.get('phone'):
        errors['phone'] = "Phone number is required."
    elif not data['phone'].isdigit() or len(data['phone']) != 10:
        errors['phone'] = "Phone number must be 10 digits."
    elif data['phone'] != current_phone:  # Only check existence if phone number changed
        if phonenumber_exists(data['phone'], exclude_id=staff_id):
            errors['phone'] = "Phone number already exists."

    # Pin code validation
    if not data.get('pin'):
        errors['pin'] = "Pin code is required."
    elif not data['pin'].isdigit() or len(data['pin']) != 6:
        errors['pin'] = "Pin code must be 6 digits."

    # Other required fields with regex validation
    required_fields = ['fname', 'lname', 'city', 'district', 'street', 'dob', 'gender', 'security_answer']
    field_regex = {
        'fname': r"^[A-Za-z\s]+$",
        'lname': r"^[A-Za-z\s]+$",
        'city': r"^[A-Za-z\s]+$",
        'district': r"^[A-Za-z\s]+$",
        'street': r"^[A-Za-z\s]+$",
        'security_answer': r"^[A-Za-z]+$"
    }

    for field in required_fields:
        if not data.get(field):
            errors[field] = f"{field.replace('_', ' ').title()} is required."
        elif field in field_regex:
            # Validate using regex for specific fields
            if not re.match(field_regex[field], data[field]):
                errors[field] = f"Invalid {field.replace('_', ' ')} format."
                
            # Add length validation
            if field in ['fname', 'lname']:
                if len(data[field]) > 10:
                    errors[field] = f"{field.replace('_', ' ').title()} must not exceed 10 characters."
                elif len(data[field]) < 1:
                    errors[field] = f"{field.replace('_', ' ').title()} must be at least 1 characters long."

            if field in ['city', 'district']:
                if len(data[field]) > 12:
                    errors[field] = f"{field.replace('_', ' ').title()} must not exceed 12 characters."
                elif len(data[field]) < 3:
                    errors[field] = f"{field.replace('_', ' ').title()} must be at least 3 characters long."

            if field == 'street':
                if len(data[field]) > 15:
                    errors[field] = f"{field.replace('_', ' ').title()} must not exceed 15 characters."
                elif len(data[field]) < 5:
                    errors[field] = f"{field.replace('_', ' ').title()} must be at least 5 characters long."

            if field == 'security_answer':
                if len(data[field]) > 20:
                    errors[field] = f"Security answer must not exceed 20 characters."
                elif len(data[field]) < 3:
                    errors[field] = f"Security answer must be at least 3 characters long."
                elif not re.match(field_regex[field], data[field]):
                    errors[field] = f"Security answer must contain only alphabetic characters (no spaces, numbers, or special symbols)."

    # Date of Birth validation
    dob = data.get('dob')
    if not dob:
        errors['dob'] = "Date of Birth is required."
    else:
        # Check if DOB matches the format YYYY-MM-DD
        try:
            dob_date = datetime.strptime(dob, '%Y-%m-%d')  # For YYYY-MM-DD format
        except ValueError:
            errors['dob'] = "Invalid date format. Use YYYY-MM-DD."
            return errors
        
        # Check if DOB is not in the future
        if dob_date > datetime.now():
            errors['dob'] = "Date of Birth cannot be in the future."

        # Check if the person is at least 18 years old
        age = (datetime.now() - dob_date).days // 365  # Approximate age in years
        if age < 18:
            errors['dob'] = "You must be at least 18 years old to sign up."

    return errors

def staff_signup_user(form_data):
    connection = None  # Initialize the connection variable
    try:
        # Validate input
        errors = validate_user_input(form_data)
        if not form_data.get('security_answer'):
            errors['security_answer'] = "Security answer is required."
        elif len(form_data['security_answer']) > 20:
            errors['security_answer'] = "Security answer must not exceed 20 characters."
        if errors:
            return False, errors

        # Collect form data
        username = form_data['username']
        fname = form_data['fname']
        lname = form_data['lname']
        city = form_data['city']
        district = form_data['district']
        pin = form_data['pin']
        street = form_data['street']
        phone = form_data['phone']
        dob = form_data['dob']
        gender = form_data['gender']
        security_answer = form_data['security_answer']
        join_date = datetime.now().strftime('%Y-%m-%d')
        status = 0  # InActive by default

        # Insert data into the database
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO tbl_staff (
                Username, Staff_fname, Staff_lname, Staff_city, Staff_dist,
                Staff_pin, Staff_street, Staff_phone, Staff_dob, Staff_gender,Favorite_Food,
                Staff_join, Staff_status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s)
            """
            cursor.execute(sql, (
                username, fname, lname, city, district, pin, street,
                phone, dob, gender,security_answer, join_date, status
            ))
            connection.commit()
        return True, {}
    except Exception as e:
        return False, {"general": str(e)}
    finally:
        # Close the connection if it was successfully opened
        if connection:
            connection.close()