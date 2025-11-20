import pymysql
from flask import request, redirect, url_for, flash

def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="",
        database="spice_bazaar",
        cursorclass=pymysql.cursors.DictCursor,
    )

def fetch_customers():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM tbl_customer")
        customers = cursor.fetchall()
        return customers
    except Exception as e:
        print(f"Error fetching customers: {str(e)}")
        return []
    finally:
        connection.close()

def change_customer_status(username, status):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Update both Customer Status and Login Status
        cursor.execute("UPDATE tbl_customer SET Cust_status = %s WHERE Username = %s", (status, username))
        cursor.execute("UPDATE tbl_login SET Login_status = %s WHERE Username = %s", (status, username))
        
        connection.commit()
        flash("Customer status updated successfully!", "success")
    except Exception as e:
        connection.rollback()  # Rollback in case of an error
        flash(f"Error updating customer status: {str(e)}", "danger")
    finally:
        cursor.close()
        connection.close()