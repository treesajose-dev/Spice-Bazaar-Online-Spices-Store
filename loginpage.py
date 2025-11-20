from flask import request, render_template, flash, redirect, url_for, session
import pymysql
import re

def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="",
        database="spice_bazaar",
        cursorclass=pymysql.cursors.DictCursor
    )

def username_exists(username):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM tbl_login WHERE Username = %s"
            cursor.execute(sql, (username,))
            result = cursor.fetchone()
            print(f"Database query result: {result}")  # Debug print
            return result
    except Exception as e:
        print(f"Database error: {str(e)}")  # Debug print
        return None
    finally:
        connection.close()

def login_route():
    session.pop('_flashes', None)
    
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        errors = {}
        
        # Validate username (email)
        if not username:
            errors['username'] = "Email is required."
        elif not re.match(r"[^@]+@[^@]+\.[^@]+", username):
            errors['username'] = "Invalid email address format."
        
        # Validate password
        if not password:
            errors['password'] = "Password is required."
        elif not (8 <= len(password) <= 10):
            errors['password'] = "Password must be between 8 and 10 characters."
        elif not re.search(r"[A-Z]", password):
            errors['password'] = "Password must contain at least one uppercase letter."
        elif not re.search(r"[a-z]", password):
            errors['password'] = "Password must contain at least one lowercase letter."
        elif not re.search(r"[0-9]", password):
            errors['password'] = "Password must contain at least one number."
        elif not re.search(r"[!@#]", password):
            errors['password'] = "Password must contain at least one special character (!, @, or #)."
        
        if errors:
            for field, error in errors.items():
                flash(f"{error}", "error")
        else:
            # Check for admin login first
            if username == "ossmanager123@gmail.com" and password == "Root@123":
                print("Admin login successful - Redirecting to admin dashboard")
                session['username'] = username
                return redirect(url_for('admindash'))

            user = username_exists(username)
            if user:
                print(f"User found: {user}")  # Shows full user data
                if user['Login_password'] == password:
                    print("Password matches")
                    print(f"Login_type: {user['Login_type']}")  # Debug login type
                    print(f"Login_status: {user['Login_status']}")  # Debug login status

                    # Check each condition separately
                    is_staff = user['Login_type'] == 'Staff'
                    is_customer = user['Login_type'] == 'Customer'
                    is_courier = user['Login_type'] == 'Courier'
                    is_active = user['Login_status'] == 1

                    print(f"Is staff: {is_staff}")
                    print(f"Is customer: {is_customer}")
                    print(f"Is active: {is_active}")

                    if is_staff and is_active:
                        print("Staff status verified - Redirecting to staff dashboard")
                        session['username'] = username
                        return redirect(url_for('staffdash'))
                    elif is_customer and is_active:
                        print("Customer status verified - Redirecting to customer dashboard")
                        session['username'] = username
                        return redirect(url_for('customerdash'))
                    elif is_courier and is_active:
                        print("Courier status verified - Redirecting to courier dashboard")
                        session['username'] = username
                        return redirect(url_for('courierdash'))
                    else:
                        if not is_active:
                            flash("Access denied: Account is inactive.", "error")
                        else:
                            flash("Access denied: Unknown reason.", "error")
                else:
                    flash("Invalid username or password.", "error")
            else:
                flash("Invalid username or password.", "error")

    user_data = None
    if 'username' in session:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT cust_id FROM tbl_customer WHERE username = %s", (session['username'],))
            user_data = cursor.fetchone()

        connection.close()
    return render_template("loginpage.html",user_data=user_data)
