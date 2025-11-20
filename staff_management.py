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

def fetch_staff():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("""
            SELECT * 
            FROM tbl_staff where staff_id!=5
        """)
        staff_members = cursor.fetchall()
        return staff_members
    except Exception as e:
        print(f"Error fetching staff members: {str(e)}")
        return []
    finally:
        connection.close()


def change_staff_status(username, status):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Update both Staff Status and Login Status
        cursor.execute("UPDATE tbl_staff SET Staff_status = %s WHERE Username = %s", (status, username))
        cursor.execute("UPDATE tbl_login SET Login_status = %s WHERE Username = %s", (status, username))
        
        connection.commit()
        flash("Staff status updated successfully!", "success")
    except Exception as e:
        connection.rollback()  # Rollback in case of an error
        flash(f"Error updating staff status: {str(e)}", "danger")
    finally:
        cursor.close()
        connection.close()