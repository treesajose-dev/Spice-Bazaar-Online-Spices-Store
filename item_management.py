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

def fetch_subcategories():
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM tbl_subcategory WHERE Subcat_status = 1")
        subcategories = cursor.fetchall()
        return subcategories
    except Exception as e:
        print(f"Error fetching subcategories: {str(e)}")
        return []
    finally:
        connection.close()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'jpg', 'jpeg'}

def validate_item(item_name, item_desc, item_profit):
    name_pattern = r"^[A-Za-z0-9][A-Za-z0-9\s-]{0,28}[A-Za-z0-9]$"
    #desc_pattern = r"^[A-Za-z0-9][A-Za-z0-9\s.,'’!?-]{0,88}[A-Za-z0-9.,'’!?-]$"
    # Simpler, more accurate pattern for your requirements
    desc_pattern = r"^[^\s][\s\S]{0,798}[^\s]$|^[^\s]$"
    
    if not re.match(name_pattern, item_name):
        return "Item name must be 1-30 characters long and can contain letters, numbers, spaces, and hyphens. No leading/trailing spaces."
    if not re.match(desc_pattern, item_desc):
        return "Item description must be 1-800 characters long and can contain letters, numbers, spaces, and punctuation. No leading/trailing spaces."
    
    
    # Check for newlines within the description (if you want to ensure it's well-formatted)
    lines = item_desc.split('\n')
    if len(lines) < 1 or len(lines) > 10:
        return "Description should contain between 1 and 10 lines."

    # Validation for item_profit (DECIMAL(5,2) and positive only)
    try:
        profit = float(item_profit)
        if profit < 0 or profit > 999.99:
            return "Profit must be a positive decimal number between 0.00 and 999.99"
        if not re.match(r"^\d{1,3}(\.\d{1,2})?$", item_profit):
            return "Profit must be in DECIMAL(5,2) format (up to 5 digits total, with 2 decimal places)."
    except ValueError:
        return "Profit must be a valid decimal number."
    
    return None  # No errors

def item_exists(item_name, exclude_id=None):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        if exclude_id is None:
            cursor.execute("SELECT COUNT(*) AS count FROM tbl_item WHERE Item_name = %s", (item_name,))
        else:
            cursor.execute("""
                SELECT COUNT(*) AS count 
                FROM tbl_item 
                WHERE Item_name = %s AND Item_id != %s
            """, (item_name, exclude_id))
            
        result = cursor.fetchone()
        return result['count'] > 0
    except Exception as e:
        print(f"Error checking item existence: {str(e)}")
        return False
    finally:
        connection.close()

def add_item():
    if request.method == "POST":
        subcat_id = request.form.get("subcat_id")
        item_name = request.form.get("item_name")
        item_desc = request.form.get("item_desc")
        item_profit = request.form.get("item_profit")
        item_image = request.files.get("item_image")

        if not subcat_id or not item_name or not item_desc or not item_profit or not item_image:
            flash("All fields are required!", "danger")
            return redirect(url_for("item_management"))

        validation_error = validate_item(item_name, item_desc, item_profit)
        if validation_error:
            flash(validation_error, "danger")
            return redirect(url_for("item_management"))

        # Check for existing item name
        if item_exists(item_name):
            flash(f"Item name '{item_name}' already exists!", "danger")
            return redirect(url_for("item_management"))

        if item_image and allowed_file(item_image.filename):
            image_data = item_image.read()
        else:
            flash("Invalid image format! Only JPG/JPEG images are allowed.", "danger")
            return redirect(url_for("item_management"))

        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            query = """
                INSERT INTO tbl_item (Subcat_id, Item_name, Item_desc, Item_image, Item_profit) 
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (subcat_id, item_name, item_desc, image_data, item_profit))
            connection.commit()
            flash("Item added successfully!", "success")
        except Exception as e:
            flash(f"Error adding item: {str(e)}", "danger")
        finally:
            connection.close()

        return redirect(url_for("item_management"))
'''
def fetch_items():
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT Item_id, Item_name, Item_desc, Item_image, Item_profit, Item_status, Subcat_id
            FROM tbl_item
        """)
        items = cursor.fetchall()

        for item in items:
            if item["Item_image"]:
                item["Item_image"] = base64.b64encode(item["Item_image"]).decode("utf-8")
        
        return items
    except Exception as e:
        print(f"Error fetching items: {str(e)}")
        return []
    finally:
        connection.close()
'''


def fetch_edit_item(item_id):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM tbl_item WHERE Item_id = %s", (item_id,))
        return cursor.fetchone()
    except Exception as e:
        print(f"Error fetching item for edit: {str(e)}")
        return None
    finally:
        connection.close()
 
def edit_item(item_id):
    if request.method == "POST":
        item_name = request.form.get("item_name")
        item_desc = request.form.get("item_desc")
        item_profit = request.form.get("item_profit")
        item_image = request.files.get("item_image")

        validation_error = validate_item(item_name, item_desc, item_profit)
        if validation_error:
            flash(validation_error, "danger")
            return redirect(url_for("item_management"))
        
        # Check if the new name exists, excluding the current item
        if item_exists(item_name, exclude_id=item_id):
            flash(f"Item name '{item_name}' already exists!", "danger")
            return redirect(url_for("item_management"))

        try:
            connection = get_db_connection()
            cursor = connection.cursor()

            if item_image and item_image.filename:
                if allowed_file(item_image.filename):
                    image_data = item_image.read()
                    query = "UPDATE tbl_item SET Item_name = %s, Item_desc = %s, Item_profit = %s, Item_image = %s WHERE Item_id = %s"
                    cursor.execute(query, (item_name, item_desc, item_profit, image_data, item_id))
                else:
                    flash("Invalid image format! Only JPG/JPEG images are allowed.", "danger")
                    return redirect(url_for("item_management"))
            else:
                query = "UPDATE tbl_item SET Item_name = %s, Item_desc = %s, Item_profit = %s WHERE Item_id = %s"
                cursor.execute(query, (item_name, item_desc, item_profit, item_id))

            connection.commit()
            flash("Item updated successfully!", "success")
        except Exception as e:
            flash(f"Error updating item: {str(e)}", "danger")
        finally:
            connection.close()

        return redirect(url_for("item_management"))
        
        

def change_item_status(item_id, status):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("UPDATE tbl_item SET Item_status = %s WHERE Item_id = %s", (status, item_id))
        connection.commit()
        flash("Item status updated successfully!", "success")
    except Exception as e:
        flash(f"Error changing item status: {str(e)}", "danger")
    finally:
        connection.close()
    return redirect(url_for("item_management"))