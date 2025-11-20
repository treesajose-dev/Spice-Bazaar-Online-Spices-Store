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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'jpg', 'jpeg'}

def validate_category(cat_name, cat_desc):
    name_pattern = r"^[A-Za-z0-9][A-Za-z0-9\s-]{0,18}[A-Za-z0-9]$"
    #desc_pattern = r"^[A-Za-z0-9][A-Za-z0-9\s.,'’!?-]{0,88}[A-Za-z0-9.,'’!?-]$"
    desc_pattern = r"^[^\s][\s\S]{0,498}[^\s]$|^[^\s]$"
    if not re.match(name_pattern, cat_name):
        return "Category name must be 1-20 characters long and can contain letters, numbers, spaces, and hyphens. No leading/trailing spaces."
    if not re.match(desc_pattern, cat_desc):
        return "Category description must be 1-500 characters long and can contain letters, numbers, spaces, and punctuation. No leading/trailing spaces."
    return None

def category_exists(cat_name, exclude_id=None):
    """
    Check if category name exists, optionally excluding a specific category ID
    (useful for edit operations)
    """
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        if exclude_id is None:
            # Check for any category with this name
            cursor.execute("SELECT COUNT(*) AS count FROM tbl_category WHERE Cat_name = %s", (cat_name,))
        else:
            # Check for any category with this name, excluding the current category
            cursor.execute("""
                SELECT COUNT(*) AS count 
                FROM tbl_category 
                WHERE Cat_name = %s AND Cat_id != %s
            """, (cat_name, exclude_id))

        result = cursor.fetchone()
        return result['count'] > 0
    except Exception as e:
        print(f"Error checking category existence: {str(e)}")
        return False
    finally:
        connection.close()

def add_category():
    if request.method == "POST":
        cat_name = request.form.get("cat_name")
        cat_desc = request.form.get("cat_desc")
        cat_image = request.files.get("cat_image")

        if not cat_name or not cat_desc or not cat_image:
            flash("All fields are required!", "danger")
            return redirect(url_for("category_management"))

        validation_error = validate_category(cat_name, cat_desc)
        if validation_error:
            flash(validation_error, "danger")
            return redirect(url_for("category_management"))
                
        # Check for existing category name
        if category_exists(cat_name):
            flash(f"Category name '{cat_name}' already exists!", "danger")
            return redirect(url_for("category_management"))

        if cat_image and allowed_file(cat_image.filename):
            image_data = cat_image.read()
        else:
            flash("Invalid image format! Only JPG/JPEG images are allowed.", "danger")
            return redirect(url_for("category_management"))

        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            query = "INSERT INTO tbl_category (Cat_name, Cat_desc, Cat_image) VALUES (%s, %s, %s)"
            cursor.execute(query, (cat_name, cat_desc, image_data))
            connection.commit()
            flash("Category added successfully!", "success")
        except Exception as e:
            flash(f"Error adding category: {str(e)}", "danger")
        finally:
            connection.close()

        return redirect(url_for("category_management"))


def fetch_categories():
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
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


def fetch_edit_category(cat_id):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        query = "SELECT Cat_id, Cat_name, Cat_desc, Cat_image FROM tbl_category WHERE Cat_id = %s"
        cursor.execute(query, (cat_id,))
        category = cursor.fetchone()
        
        print("Debug - Fetched category data:", category)  # Debug print
        
        if category:
            if category["Cat_image"]:
                category["Cat_image"] = base64.b64encode(category["Cat_image"]).decode("utf-8")
            return category
        return None
        
    except Exception as e:
        print(f"Error fetching category for editing: {str(e)}")
        return None
    finally:
        connection.close()

def edit_category(cat_id):
    if request.method == "POST":
        cat_name = request.form.get("cat_name")
        cat_desc = request.form.get("cat_desc")
        cat_image = request.files.get("cat_image")

        if not cat_name or not cat_desc:
            flash("Name and Description are required!", "danger")
            return redirect(url_for("category_management"))

        validation_error = validate_category(cat_name, cat_desc)
        if validation_error:
            flash(validation_error, "danger")
            return redirect(url_for("category_management"))
        
        # Check if the new name exists, excluding the current category
        if category_exists(cat_name, exclude_id=cat_id):
            flash(f"Category name '{cat_name}' already exists!", "danger")
            return redirect(url_for("category_management"))

        try:
            connection = get_db_connection()
            cursor = connection.cursor()

            if cat_image and cat_image.filename:
                if allowed_file(cat_image.filename):
                    image_data = cat_image.read()
                    query = "UPDATE tbl_category SET Cat_name = %s, Cat_desc = %s, Cat_image = %s WHERE Cat_id = %s"
                    cursor.execute(query, (cat_name, cat_desc, image_data, cat_id))
                else:
                    flash("Invalid image format! Only JPG/JPEG images are allowed.", "danger")
                    return redirect(url_for("category_management"))
            else:
                query = "UPDATE tbl_category SET Cat_name = %s, Cat_desc = %s WHERE Cat_id = %s"
                cursor.execute(query, (cat_name, cat_desc, cat_id))

            connection.commit()
            flash("Category updated successfully!", "success")
        except Exception as e:
            flash(f"Error updating category: {str(e)}", "danger")
        finally:
            connection.close()

        return redirect(url_for("category_management"))


def change_category_status(cat_id, status):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("UPDATE tbl_category SET Cat_status = %s WHERE Cat_id = %s", (status, cat_id))
        connection.commit()
        flash("Category status updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating category status: {str(e)}", "danger")
    finally:
        connection.close()