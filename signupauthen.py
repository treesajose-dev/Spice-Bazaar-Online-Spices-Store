from flask import request, render_template, flash, redirect, url_for,session
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
            sql = "SELECT COUNT(1) FROM tbl_login WHERE Username = %s"
            cursor.execute(sql, (username,))
            result = cursor.fetchone()
            return result['COUNT(1)'] > 0
    finally:
        connection.close()

def signupauthen_route():
    # Clear any existing flash messages at the start of the route
    session.pop('_flashes', None)

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        login_type = request.form.get("login_type")
        
        errors = {}
        
        # Validate username (email)
        if not username:
            errors['username'] = "Email is required."
        elif not re.match(r"[^@]+@[^@]+\.[^@]+", username):
            errors['username'] = "Invalid email address format."
        elif len(username) < 6:
            errors['username'] = "Email must be at least 6 characters long."
        elif len(username) > 30:
            errors['username'] = "Email must not exceed 30 characters."
        elif username_exists(username):
            errors['username'] = "Username already taken."
        
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
        elif not re.search(r"[!@#]", password):  # Check for at least one special character (!, @, or #)
            errors['password'] = "Password must contain at least one special character (!, @, or #)."

        
        if errors:
            for field, error in errors.items():
                flash(f"{field}: {error}", "error")
        else:
            # Determine the login status
            login_status = 1  # Default active status
            if login_type == 'Courier':
                login_status = 0  # Set to pending approval for couriers
            if login_type == 'Staff':
                login_status = 0  # Set to pending approval for staff

            # Insert into tbl_login
            connection = get_db_connection()
            try:
                with connection.cursor() as cursor:
                    sql = "INSERT INTO tbl_login (Username, Login_password, Login_type, Login_status) VALUES (%s, %s, %s, %s)"
                    cursor.execute(sql, (username, password, login_type, login_status))
                    connection.commit()
                    
                    # Store a flag in session to show the message only once
                    session['show_reg_success'] = True
                    
                    # Redirect based on Login_type
                    if login_type == 'Staff':
                        session['username'] = username
                        return redirect(url_for('staff_signup'))  # Staff redirect
                    elif login_type == 'Customer':
                        flash("Registration successful!", "success")
                        session['username'] = username
                        return redirect(url_for('customer_signup'))  # Customer redirect
                    elif login_type == 'Courier':
                        flash("Courier signup successful, pending approval", "success")

            except Exception as e:
                flash(f"Error: {e}", "error")
            finally:
                connection.close()
    
    return render_template("signupauthen.html")

