import pymysql
from flask import request, redirect, url_for, flash
import base64
import re

def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="",
        database="spice_bazaar",
        cursorclass=pymysql.cursors.DictCursor,
    )

def fetch_categories():
    connection = get_db_connection()
    try:
        cursor = connection.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM tbl_category")
        categories = cursor.fetchall()

        # Convert BLOB images to Base64
        for category in categories:
            if category["Cat_image"]:  # Check if image exists
                category["Cat_image"] = base64.b64encode(category["Cat_image"]).decode("utf-8")
        
        return categories
    except Exception as e:
        print(f"Error fetching categories: {str(e)}")
        return []
    finally:
        connection.close()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'jpg', 'jpeg'}

def validate_subcategory(subcat_name, subcat_desc):
    name_pattern = r"^[A-Za-z0-9][A-Za-z0-9\s-]{0,18}[A-Za-z0-9]$"
    #desc_pattern = r"^[A-Za-z0-9][A-Za-z0-9\s.,'’!?-]{0,88}[A-Za-z0-9.,'’!?-]$"
    desc_pattern = r"^[^\s][\s\S]{0,498}[^\s]$|^[^\s]$"

    if not re.match(name_pattern, subcat_name):
        return "Subcategory name must be 1-20 characters long and can contain letters, numbers, spaces, and hyphens. No leading/trailing spaces."
    if not re.match(desc_pattern, subcat_desc):
        return "Subcategory description must be 1-500 characters long and can contain letters, numbers, spaces, and punctuation. No leading/trailing spaces."
    return None

def subcategory_exists(subcat_name, exclude_id=None):
    """
    Check if subcategory name exists, optionally excluding a specific subcategory ID
    (useful for edit operations)
    """
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        if exclude_id is None:
            # Check for any subcategory with this name
            cursor.execute("SELECT COUNT(*) AS count FROM tbl_subcategory WHERE Subcat_name = %s", (subcat_name,))
        else:
            # Check for any subcategory with this name, excluding the current subcategory
            cursor.execute("""
                SELECT COUNT(*) AS count 
                FROM tbl_subcategory 
                WHERE Subcat_name = %s AND Subcat_id != %s
            """, (subcat_name, exclude_id))
            
        result = cursor.fetchone()
        return result['count'] > 0
    except Exception as e:
        print(f"Error checking subcategory existence: {str(e)}")
        return False
    finally:
        connection.close()



def add_subcategory():
    if request.method == "POST":
        category_id = request.form.get("cat_id")
        subcat_name = request.form.get("subcat_name")
        subcat_desc = request.form.get("subcat_desc")
        subcat_image = request.files.get("subcat_image")
        
        if not category_id or not subcat_name or not subcat_desc or not subcat_image:
            flash("All fields are required!", "danger")
            return redirect(url_for("subcategory_management"))

        validation_error = validate_subcategory(subcat_name, subcat_desc)
        if validation_error:
            flash(validation_error, "danger")
            return redirect(url_for("subcategory_management"))
        
        # Check for existing subcategory name
        if subcategory_exists(subcat_name):
            flash(f"Subcategory name '{subcat_name}' already exists!", "danger")
            return redirect(url_for("subcategory_management"))

        if subcat_image and allowed_file(subcat_image.filename):
            image_data = subcat_image.read()
        else:
            flash("Invalid image format! Only JPG/JPEG images are allowed.", "danger")
            return redirect(url_for("subcategory_management"))

        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            query = "INSERT INTO tbl_subcategory (Cat_id,Subcat_name, Subcat_desc, Subcat_image) VALUES (%s,%s, %s, %s)"
            cursor.execute(query, (category_id,subcat_name, subcat_desc, image_data))
            connection.commit()
            flash("Subcategory added successfully!", "success")
        except Exception as e:
            flash(f"Error adding subcategory: {str(e)}", "danger")
        finally:
            connection.close()

        return redirect(url_for("subcategory_management"))

'''
def fetch_subcategories():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT s.Subcat_id, c.Cat_name, s.Subcat_name, s.Subcat_desc, s.Subcat_status
                FROM tbl_subcategory s
                JOIN tbl_category c ON s.Cat_id = c.Cat_id
            """)
            subcategories = cursor.fetchall()
            print(subcategories)
        return subcategories
    except Exception as e:
        print(f"Error fetching subcategories: {str(e)}")
        return []
    finally:
        connection.close()
'''

def fetch_edit_subcategory(subcat_id):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        query = "SELECT Subcat_id,Cat_id, Subcat_name, Subcat_desc, Subcat_image FROM tbl_subcategory WHERE Subcat_id = %s"
        cursor.execute(query, (subcat_id,))
        subcategory = cursor.fetchone()
        
        print("Debug - Fetched subcategory data:", subcategory)  # Debug print
        
        if subcategory:
            if subcategory["Subcat_image"]:
                subcategory["Subcat_image"] = base64.b64encode(subcategory["Subcat_image"]).decode("utf-8")
            return subcategory
        return None
        
    except Exception as e:
        print(f"Error fetching subcategory for editing: {str(e)}")
        return None
    finally:
        connection.close()

def edit_subcategory(subcat_id):
    if request.method == "POST":
        category_id = request.form.get("cat_id")
        subcat_name = request.form.get("subcat_name")
        subcat_desc = request.form.get("subcat_desc")
        subcat_image = request.files.get("subcat_image")

        if not category_id or not subcat_name or not subcat_desc:
            flash("Name and Description are required!", "danger")
            return redirect(url_for("subcategory_management"))

        validation_error = validate_subcategory(subcat_name, subcat_desc)
        if validation_error:
            flash(validation_error, "danger")
            return redirect(url_for("subcategory_management"))

        # Check if the new name exists, excluding the current subcategory
        if subcategory_exists(subcat_name, exclude_id=subcat_id):
            flash(f"Subcategory name '{subcat_name}' already exists!", "danger")
            return redirect(url_for("subcategory_management"))

        try:
            connection = get_db_connection()
            cursor = connection.cursor()

            if subcat_image and subcat_image.filename:
                if allowed_file(subcat_image.filename):
                    image_data = subcat_image.read()
                    query = "UPDATE tbl_subcategory SET Cat_id= %s, Subcat_name = %s, Subcat_desc = %s, Subcat_image = %s WHERE Subcat_id = %s"
                    cursor.execute(query, (category_id,subcat_name, subcat_desc, image_data, subcat_id))
                else:
                    flash("Invalid image format! Only JPG/JPEG images are allowed.", "danger")
                    return redirect(url_for("subcategory_management"))
            else:
                query = "UPDATE tbl_subcategory SET Cat_id= %s, Subcat_name = %s, Subcat_desc = %s WHERE Subcat_id = %s"
                cursor.execute(query, (category_id,subcat_name, subcat_desc, subcat_id))

            connection.commit()
            flash("Subcategory updated successfully!", "success")
        except Exception as e:
            flash(f"Error updating subcategory: {str(e)}", "danger")
        finally:
            connection.close()

        return redirect(url_for("subcategory_management"))


def change_subcategory_status(subcat_id, status):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("UPDATE tbl_subcategory SET Subcat_status = %s WHERE Subcat_id = %s", (status, subcat_id))
        connection.commit()
        flash("Subcategory status updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating subcategory status: {str(e)}", "danger")
    finally:
        connection.close()