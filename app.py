from flask import Flask, render_template, request, redirect,url_for, flash, session, jsonify
from loginpage import login_route
from signupauthen import signupauthen_route
from staff_signup import *
from customer_signup import customer_signup_user,validate_user_input
from courier_management import *
from category_management import *
from subcategory_management import *
from item_management import *
from purchase_management import *
from customer_management import *
from vendor_management import *
from staff_management import *
import pymysql
from datetime import timedelta,datetime
from reports import admin_reports
from invoice_generator import download_invoice

app=Flask(__name__)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=5)
app.secret_key = "your_secret_key"

# Disable Jinja2 caching
app.jinja_env.cache = {}

@app.route('/logout')
def logout():
    # Clear the session
    session.clear()  # This removes all session data
    # Alternatively, you can just remove the username key
    # session.pop('username', None)
    
    # Redirect to the home page
    return redirect(url_for('home'))

# Home Page
@app.route('/')
def home():
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT Cat_id, Cat_name, cat_desc, Cat_image FROM tbl_category WHERE Cat_status = 1")
        categories = cursor.fetchall()
    
    connection.close()

    # Convert binary images to Base64
    for category in categories:
        if isinstance(category['Cat_image'], bytes):
            category['Cat_image'] = base64.b64encode(category['Cat_image']).decode('utf-8')

    # Fetch user data if logged in
    user_data = None
    if 'username' in session:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT cust_id FROM tbl_customer WHERE username = %s", (session['username'],))
            user_data = cursor.fetchone()

        connection.close()

    return render_template("home.html", categories=categories, user_data=user_data)

# Category Details Page
@app.route('/homecat/<int:cat_id>')
def category_details(cat_id):
    connection = get_db_connection()
    with connection.cursor() as cursor:
        # Fetch category details
        cursor.execute("SELECT Cat_name, Cat_desc, Cat_image FROM tbl_category WHERE Cat_id = %s", (cat_id,))
        category = cursor.fetchone()
        
        # Fetch subcategories
        cursor.execute("SELECT Subcat_id, Subcat_name, Subcat_image FROM tbl_subcategory WHERE Cat_id = %s AND Subcat_status = 1", (cat_id,))
        subcategories = cursor.fetchall()

    connection.close()

    if category and isinstance(category['Cat_image'], bytes):
        category['Cat_image'] = base64.b64encode(category['Cat_image']).decode('utf-8')

    for subcategory in subcategories:
        if isinstance(subcategory['Subcat_image'], bytes):
            subcategory['Subcat_image'] = base64.b64encode(subcategory['Subcat_image']).decode('utf-8')

    # Fetch user data if logged in
    user_data = None
    if 'username' in session:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT cust_id FROM tbl_customer WHERE username = %s", (session['username'],))
            user_data = cursor.fetchone()

        connection.close()

    return render_template('homecat.html', category=category, subcategories=subcategories, user_data=user_data)

@app.route('/homesubcat/<int:subcat_id>')
def subcategory_details(subcat_id):
    connection = get_db_connection()
    
    try:
        with connection.cursor() as cursor:
            # Fetch subcategory details
            cursor.execute("SELECT Subcat_name, Subcat_desc, Subcat_image FROM tbl_subcategory WHERE Subcat_id = %s", (subcat_id,))
            subcategory = cursor.fetchone()

            # Fetch items under subcategory with rating information
            cursor.execute("""
    SELECT i.Item_id, i.Item_name, i.Item_image, pc.Pur_unit_weight, pc.Sell_price,
           IFNULL(AVG(rr.Rating), 0) as avg_rating,
           COUNT(rr.Reviewrating_id) as review_count
    FROM tbl_item i
    LEFT JOIN (
        SELECT pc.Item_id, pc.Pur_unit_weight, pc.Sell_price, pc.Expiry_date
        FROM tbl_purchase_child pc
        WHERE pc.Stock > 0
        AND pc.Expiry_date > CURDATE()
        AND pc.Pur_child_id = (
            SELECT pc_inner.Pur_child_id
            FROM tbl_purchase_child pc_inner
            WHERE pc_inner.Item_id = pc.Item_id
            AND pc_inner.Pur_unit_weight = pc.Pur_unit_weight
            AND pc_inner.Stock > 0
            AND pc_inner.Expiry_date > CURDATE()
            ORDER BY pc_inner.Expiry_date ASC
            LIMIT 1
        )
    ) pc ON i.Item_id = pc.Item_id
    LEFT JOIN tbl_reviewrating rr ON i.Item_id = rr.item_id AND rr.status = 1
    WHERE i.Subcat_id = %s 
    AND i.Item_status = 1
    AND EXISTS (
        SELECT 1
        FROM tbl_purchase_child pc_check
        WHERE pc_check.Item_id = i.Item_id
        AND pc_check.Stock > 0
        AND pc_check.Expiry_date > CURDATE()
    )
    GROUP BY i.Item_id, i.Item_name, i.Item_image, pc.Pur_unit_weight, pc.Sell_price
    ORDER BY i.Item_id, pc.Pur_unit_weight
""", (subcat_id,))

            raw_items = cursor.fetchall()

            # Process the items to group by Item_id and collect weight options
            items = {}
            for item in raw_items:
                item_id = item['Item_id']
                
                # Convert binary image data
                if isinstance(item['Item_image'], bytes):
                    item['Item_image'] = base64.b64encode(item['Item_image']).decode('utf-8')
                
                # If this is the first time we're seeing this item
                if item_id not in items:
                    items[item_id] = {
                        'Item_id': item_id,
                        'Item_name': item['Item_name'],
                        'Item_image': item['Item_image'],
                        'avg_rating': item['avg_rating'],
                        'review_count': item['review_count'],
                        'weight_options': []
                    }
                
                # Add this weight option
                items[item_id]['weight_options'].append({
                    'weight': item['Pur_unit_weight'],
                    'price': item['Sell_price']
                })
            
            # Convert to list for template
            items_list = list(items.values())

        # Ensure binary image data is converted properly for subcategory
        if subcategory and isinstance(subcategory['Subcat_image'], bytes):
            subcategory['Subcat_image'] = base64.b64encode(subcategory['Subcat_image']).decode('utf-8')

    finally:
        connection.close()

    # Fetch user data if logged in
    user_data = None
    if 'username' in session:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT cust_id FROM tbl_customer WHERE username = %s", (session['username'],))
            user_data = cursor.fetchone()

        connection.close()

    return render_template('homesubcat.html', subcategory=subcategory, items=items_list, user_data=user_data)

@app.route('/homeitem/<int:item_id>')
def item_details(item_id):  
    unit_weight = request.args.get('unit_weight')
    connection = get_db_connection()
    
    try:
        cursor = connection.cursor()  # Create cursor outside the with block
        
        cursor.execute("""
            SELECT Item_name, Item_desc, Item_image, Pur_unit_weight, Sell_price 
            FROM tbl_item 
            JOIN tbl_purchase_child ON tbl_item.Item_id = tbl_purchase_child.Item_id 
            WHERE tbl_item.Item_id = %s 
            AND tbl_purchase_child.Pur_unit_weight = %s 
            AND tbl_purchase_child.Expiry_date > CURDATE()
            ORDER BY tbl_purchase_child.Expiry_date ASC
            LIMIT 1
        """, (item_id, unit_weight))

        item = cursor.fetchone()

        if item and isinstance(item['Item_image'], bytes):
            item['Item_image'] = base64.b64encode(item['Item_image']).decode('utf-8')

        can_review = False
        user_review = None
        reviews = []

        # Calculate average rating
        cursor.execute("""
            SELECT AVG(Rating) as avg_rating
            FROM tbl_reviewrating 
            WHERE Item_id = %s AND status = 1
        """, (item_id,))
        avg_rating_result = cursor.fetchone()
        avg_rating = float(avg_rating_result['avg_rating']) if avg_rating_result['avg_rating'] and avg_rating_result['avg_rating'] is not None else 0.0

        # Check if user is logged in (will be used by JS to display the message)
        is_logged_in = True if session.get('username') else False
        
        # Fetch user data if logged in
        user_data = None
        if 'username' in session:
            cursor.execute("SELECT cust_id FROM tbl_customer WHERE username = %s", (session['username'],))
            user_data = cursor.fetchone()

        if user_data:
            # Check if item is in any delivered cart
            cursor.execute("""
                SELECT c.Cart_master_id
                FROM tbl_cassign c
                JOIN tbl_cart_master cm ON c.Cart_master_id = cm.Cart_master_id
                WHERE c.Cassign_status = 'Delivered' AND cm.Cust_id = %s
            """, (user_data['cust_id'],))
            delivered_cart_ids = [row['Cart_master_id'] for row in cursor.fetchall()]

            if delivered_cart_ids:
                # Only proceed if there are delivered cart IDs
                if len(delivered_cart_ids) == 1:
                    cursor.execute("""
                        SELECT Item_id FROM tbl_cart_child
                        WHERE Cart_master_id = %s AND Item_id = %s
                    """, (delivered_cart_ids[0], item_id))
                else:
                    cursor.execute("""
                        SELECT Item_id FROM tbl_cart_child
                        WHERE Cart_master_id IN %s AND Item_id = %s
                    """, (tuple(delivered_cart_ids), item_id))
                can_review = cursor.fetchone() is not None

            if can_review:
                cursor.execute("""
                    SELECT r.Review_text, r.Rating, r.Reviewrating_date, c.Username
                    FROM tbl_reviewrating r
                    JOIN tbl_customer c ON r.Cust_id = c.Cust_id
                    WHERE r.Item_id = %s AND r.Cust_id = %s
                """, (item_id, user_data['cust_id']))
                user_review = cursor.fetchone()

        # Fetch all reviews
        cursor.execute("""
            SELECT r.Review_text, r.Rating, r.Reviewrating_date, c.Username
            FROM tbl_reviewrating r
            JOIN tbl_customer c ON r.Cust_id = c.Cust_id
            WHERE r.Item_id = %s AND r.status = 1
            ORDER BY r.Reviewrating_date DESC
        """, (item_id,))
        reviews = cursor.fetchall()
        
        cursor.close()  # Explicitly close the cursor when done
        
    finally:
        connection.close()

    return render_template('homeitem.html', item=item, is_logged_in=is_logged_in, user_data=user_data,
        can_review=can_review,
        user_review=user_review,
        reviews=reviews,
        edit_mode=True,
        avg_rating=avg_rating)

@app.route('/submit_review/<int:item_id>', methods=['POST'])
def submit_review(item_id):
    if 'username' not in session:
        flash('Please login to post a review.', 'error')
        return redirect(url_for('item_details', item_id=item_id))

    # Get unit_weight from form
    unit_weight = request.form.get('unit_weight')

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT cust_id FROM tbl_customer WHERE username = %s", (session['username'],))
            user_data = cursor.fetchone()

            if not user_data:
                flash('User not found.', 'error')
                return redirect(url_for('item_details', item_id=item_id))

            review_text = request.form['review_text']
            rating = int(request.form['rating'])

            cursor.execute("""
                SELECT Reviewrating_id FROM tbl_reviewrating
                WHERE Item_id = %s AND Cust_id = %s
            """, (item_id, user_data['cust_id']))
            existing_review = cursor.fetchone()

            if existing_review:
                cursor.execute("""
                    UPDATE tbl_reviewrating
                    SET Review_text = %s, Rating = %s, Reviewrating_date = CURRENT_TIMESTAMP
                    WHERE Item_id = %s AND Cust_id = %s
                """, (review_text, rating, item_id, user_data['cust_id']))
            else:
                cursor.execute("""
                    INSERT INTO tbl_reviewrating (Cust_id, Item_id, Review_text, Rating, Reviewrating_date)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                """, (user_data['cust_id'], item_id, review_text, rating))
            
            connection.commit()
            flash('Review submitted successfully.', 'success')
    finally:
        connection.close()

    return redirect(url_for('item_details', item_id=item_id,unit_weight=unit_weight))

@app.route('/add_to_cart/<int:item_id>', methods=['POST']) 
def add_to_cart(item_id):
    unit_weight = request.form.get('unit_weight')  # Get from form data
    # Check if the user is logged in
    if not session.get('username'):
        flash("Cannot add item to cart because you are not logged in", "error")
        return redirect(url_for('item_details', item_id=item_id,unit_weight=unit_weight))
    
    # Get the username from session and fetch the corresponding Cust_id
    username = session['username']
    
    # Get quantity from the form data instead of JSON
    quantity = int(request.form.get('quantity', 1))
    
    # Connect to the database
    connection = get_db_connection()
    cursor = connection.cursor()
    
    # Get the Cust_id from the username
    cursor.execute("SELECT Cust_id FROM tbl_customer WHERE Username = %s", (username,))
    user = cursor.fetchone()
    
    if not user:
        cursor.close()
        connection.close()
        flash("Cannot add item to cart because you are not logged in.", "error")
        return redirect(url_for('item_details', item_id=item_id,unit_weight=unit_weight))
    
    # Extract Cust_id from the result
    user_id = user['Cust_id']
    
    # Check if there is an active cart for the user
    cursor.execute(""" 
        SELECT Cart_master_id, Cart_tot_amt FROM tbl_cart_master 
        WHERE Cust_id = %s AND Cart_item_status = 'Active'
    """, (user_id,))
    cart = cursor.fetchone()

    if not cart:
        # If no active cart exists, create one
        cursor.execute(""" 
            INSERT INTO tbl_cart_master (Cust_id, Cart_item_status, Cart_tot_amt) 
            VALUES (%s, 'Active', 0) 
        """, (user_id,))
        connection.commit()
        cursor.execute("SELECT LAST_INSERT_ID() AS id")
        cart_master_id = cursor.fetchone()['id']
    else:
        # Use existing cart_master_id if found
        cart_master_id = cart['Cart_master_id']

    # Fetch Sell_price and Stock from tbl_item and tbl_purchase_child
    cursor.execute("""
            SELECT pc.Sell_price, pc.Stock
            FROM tbl_item i 
            JOIN tbl_purchase_child pc ON i.Item_id = pc.Item_id  
            WHERE i.Item_id = %s AND pc.Pur_unit_weight = %s 
            ORDER BY pc.Expiry_date ASC
            LIMIT 1
        """, (item_id, unit_weight))
    item = cursor.fetchone()

    if not item:
        cursor.close()
        connection.close()
        flash("Item not found in the database.", "error")
        return redirect(url_for('item_details', item_id=item_id,unit_weight=unit_weight))

    # Check if the item is available (stock is greater than 0)
    if item['Stock'] == 0:
        cursor.close()
        connection.close()
        flash("Item is unavailable.", "error")
        return redirect(url_for('item_details', item_id=item_id,unit_weight=unit_weight))
    
    # Check if requested quantity exceeds available stock
    if quantity > item['Stock']:
        cursor.close()
        connection.close()
        flash("Quantity exceeds available stock!", "error")
        return redirect(url_for('item_details', item_id=item_id,unit_weight=unit_weight))

    # Get the Sell_price and calculate the price based on quantity
    item_price = item['Sell_price']
    cart_price = item_price * quantity
    
    # Insert item into cart
    cursor.execute(""" 
        INSERT INTO tbl_cart_child (Cart_master_id, Item_id, Cart_qty, Cart_unit_price, Cart_price) 
        VALUES (%s, %s, %s, %s, %s) 
    """, (cart_master_id, item_id, quantity, item_price, cart_price))

    # Update the total amount in the master cart
    cursor.execute(""" 
        UPDATE tbl_cart_master 
        SET Cart_tot_amt = Cart_tot_amt + %s 
        WHERE Cart_master_id = %s 
    """, (cart_price, cart_master_id))

    connection.commit()
    cursor.close()
    connection.close()

    # Flash a success message
    flash("Item added to cart successfully", "success")
    return redirect(url_for('item_details', item_id=item_id,unit_weight=unit_weight))

# Check if user is logged in
def is_logged_in():
    return 'username' in session

@app.route('/cart_details')
def cart_details():
    # Fetch user data if logged in
    user_data = None
    if 'username' in session:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT cust_id FROM tbl_customer WHERE username = %s", (session['username'],))
            user_data = cursor.fetchone()

        connection.close()

    if not is_logged_in():
        flash('Please login to view your cart', 'danger')
        return redirect(url_for('login'))
    
    # Get customer ID from username in session
    username = session['username']
    db = get_db_connection()
    cursor = db.cursor()
    
    # Get customer ID
    cursor.execute("SELECT Cust_id FROM tbl_customer WHERE Username = %s", (username,))
    customer = cursor.fetchone()
    
    if not customer:
        flash('Customer profile not found', 'danger')
        cursor.close()
        db.close()
        return redirect(url_for('profile'))
    
    cust_id = customer['Cust_id']
    
    # Check if there's an active cart for this customer
    cursor.execute("""
        SELECT Cart_master_id, Cart_tot_amt 
        FROM tbl_cart_master 
        WHERE Cust_id = %s AND Cart_item_status = 'Active'
    """, (cust_id,))
    cart_master = cursor.fetchone()
    
    if not cart_master:
        cursor.close()
        db.close()
        return render_template('cart_details.html', cart_items=[], cart_total=0,user_data=user_data)
    
    cursor.execute("""
    SELECT cc.Cart_child_id, cc.Cart_qty, cc.Cart_unit_price, cc.Cart_price, 
           cm.Cart_tot_amt, cm.Cust_id,
           i.Item_id, i.Item_name, i.Item_desc, i.Item_image,
           pc.Pur_unit_weight  -- Extracting Pur_unit_weight from tbl_purchase_child
    FROM tbl_cart_master cm
    JOIN tbl_cart_child cc ON cm.Cart_master_id = cc.Cart_master_id
    JOIN tbl_item i ON cc.Item_id = i.Item_id
    JOIN tbl_purchase_child pc ON i.Item_id = pc.Item_id 
        AND pc.Sell_price = cc.Cart_unit_price  -- Ensuring Sell_price matches Cart_unit_price
    WHERE cm.Cart_master_id = %s
""", (cart_master['Cart_master_id'],))

    cart_items = cursor.fetchall()
    
    # Convert BLOB images to base64 for display
    for item in cart_items:
        if item['Item_image']:
            item['item_image'] = base64.b64encode(item['Item_image']).decode('utf-8')
        else:
            item['item_image'] = None
    
    cursor.close()
    db.close()
    
    return render_template('cart_details.html', 
                          cart_items=cart_items, 
                          cart_total=cart_master['Cart_tot_amt'],user_data=user_data)

# Update cart item quantity
@app.route('/update_cart_item', methods=['POST'])
def update_cart_item():
    if not is_logged_in():
        flash('Please login to update your cart', 'danger')
        return redirect(url_for('login'))
    
    cart_child_id = request.form.get('cart_child_id')
    action = request.form.get('action')
    
    db = get_db_connection()
    cursor = db.cursor()
    
    # Get current cart item details
    cursor.execute("""
        SELECT cc.Cart_master_id, cc.Item_id, cc.Cart_qty, cc.Cart_unit_price 
        FROM tbl_cart_child cc 
        WHERE cc.Cart_child_id = %s
    """, (cart_child_id,))
    
    cart_item = cursor.fetchone()
    
    if not cart_item:
        flash('Cart item not found', 'danger')
        cursor.close()
        db.close()
        return redirect(url_for('cart_details'))
    
    item_id = cart_item['Item_id']
    current_qty = cart_item['Cart_qty']

    # Fetch available stock from tbl_purchase_child
    cursor.execute("""
    SELECT SUM(Stock) AS available_stock
    FROM tbl_purchase_child 
    WHERE Item_id = %s AND Sell_price = %s
    """, (item_id, cart_item['Cart_unit_price']))

    stock_data = cursor.fetchone()
    available_stock = stock_data['available_stock'] if stock_data and stock_data['available_stock'] else 0

    # Update quantity
    new_qty = current_qty
    if action == 'increase':
        if new_qty + 1 > available_stock:
            flash(f'Quantity exceeds available stock!', f'quantity_error_{cart_child_id}')
            cursor.close()
            db.close()
            return redirect(url_for('cart_details'))
        new_qty += 1
    elif action == 'decrease':
        new_qty = max(1, new_qty - 1)  # Don't go below 1
    
    # Calculate new price
    new_price = new_qty * cart_item['Cart_unit_price']
    
    # Update cart child
    cursor.execute("""
        UPDATE tbl_cart_child 
        SET Cart_qty = %s, Cart_price = %s 
        WHERE Cart_child_id = %s
    """, (new_qty, new_price, cart_child_id))
    
    # Update cart master total
    cursor.execute("""
        SELECT SUM(Cart_price) as new_total 
        FROM tbl_cart_child 
        WHERE Cart_master_id = %s
    """, (cart_item['Cart_master_id'],))
    
    new_total = cursor.fetchone()['new_total'] or 0
    
    cursor.execute("""
        UPDATE tbl_cart_master 
        SET Cart_tot_amt = %s 
        WHERE Cart_master_id = %s
    """, (new_total, cart_item['Cart_master_id']))
    
    db.commit()
    cursor.close()
    db.close()
    
    return redirect(url_for('cart_details'))

# Remove item from cart
@app.route('/remove_cart_item', methods=['POST'])
def remove_cart_item():
    if not is_logged_in():
        flash('Please login to update your cart', 'danger')
        return redirect(url_for('login'))
    
    cart_child_id = request.form.get('cart_child_id')
    
    db = get_db_connection()
    cursor = db.cursor()
    
    # Get cart master ID
    cursor.execute("SELECT Cart_master_id FROM tbl_cart_child WHERE Cart_child_id = %s", (cart_child_id,))
    result = cursor.fetchone()
    
    if not result:
        flash('Cart item not found', 'danger')
        cursor.close()
        db.close()
        return redirect(url_for('cart_details'))
    
    cart_master_id = result['Cart_master_id']
    
    # Delete cart item
    cursor.execute("DELETE FROM tbl_cart_child WHERE Cart_child_id = %s", (cart_child_id,))
    
    # Check if cart is empty
    cursor.execute("SELECT COUNT(*) as item_count FROM tbl_cart_child WHERE Cart_master_id = %s", (cart_master_id,))
    item_count = cursor.fetchone()['item_count']
    
    if item_count == 0:
        # If no items left, delete the cart master record
        cursor.execute("DELETE FROM tbl_cart_master WHERE Cart_master_id = %s", (cart_master_id,))
    else:
        # Otherwise, update cart total
        cursor.execute("""
            SELECT SUM(Cart_price) as new_total 
            FROM tbl_cart_child 
            WHERE Cart_master_id = %s
        """, (cart_master_id,))
        
        result = cursor.fetchone()
        new_total = result['new_total'] if result['new_total'] else 0
        
        cursor.execute("""
            UPDATE tbl_cart_master 
            SET Cart_tot_amt = %s 
            WHERE Cart_master_id = %s
        """, (new_total, cart_master_id))
    
    db.commit()
    cursor.close()
    db.close()
    
    flash('Item removed from cart', 'success')
    return redirect(url_for('cart_details'))

# Proceed to checkout
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    # Fetch user data if logged in
    user_data = None
    if 'username' in session:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT cust_id FROM tbl_customer WHERE username = %s", (session['username'],))
            user_data = cursor.fetchone()
        connection.close()

    if not is_logged_in():
        flash('Please login to checkout', 'danger')
        return redirect(url_for('login'))
    
    username = session['username']
    db = get_db_connection()
    cursor = db.cursor()
    
    # Get customer details
    cursor.execute("""
        SELECT Cust_id, Cust_fname, Cust_lname, Cust_phone, Cust_street, 
               Cust_city, Cust_dist, Cust_pin 
        FROM tbl_customer 
        WHERE Username = %s
    """, (username,))
    customer = cursor.fetchone()
    
    print(f"username: {username}, customer: {customer}, type: {type(customer)}")
    
    if not customer:
        flash('Customer profile not found for this username', 'danger')
        cursor.close()
        db.close()
        return redirect(url_for('profile'))
    
    cust_id = customer['Cust_id']
    cust_fname = customer['Cust_fname']
    cust_lname = customer['Cust_lname']
    cust_phone = customer['Cust_phone']
    cust_street = customer['Cust_street']
    cust_city = customer['Cust_city']
    cust_dist = customer['Cust_dist']
    cust_pin = customer['Cust_pin']
    
    # Get active cart
    cursor.execute("""
        SELECT Cart_master_id 
        FROM tbl_cart_master 
        WHERE Cust_id = %s AND Cart_item_status = 'Active'
    """, (cust_id,))
    cart_result = cursor.fetchone()

    if not cart_result:
        flash('No active cart found', 'danger')
        cursor.close()
        db.close()
        return redirect(url_for('cart_details'))

    if isinstance(cart_result, dict):
        cart_master_id = cart_result['Cart_master_id']
    elif isinstance(cart_result, tuple):
        cart_master_id = cart_result[0]
    else:
        cart_master_id = cart_result
    
# Get saved cards (max 3)
    cursor.execute("""
        SELECT Card_id, Card_no, Card_name, Exp_month, Exp_year 
        FROM tbl_card 
        WHERE Cust_id = %s 
        LIMIT 3
    """, (cust_id,))
    saved_cards = cursor.fetchall()
    
    # Convert Card_no to string in each card
    for card in saved_cards:
        card['Card_no'] = str(card['Card_no'])
        # Ensure Exp_month and Exp_year are strings for the template
        card['Exp_month'] = str(card['Exp_month']).zfill(2)  # e.g., "03" instead of 3
        card['Exp_year'] = str(card['Exp_year'])  # e.g., "2025"
    
    print(f"saved_cards: {saved_cards}, type: {type(saved_cards)}")
    
    cursor.close()
    db.close()
    
    customer_dict = {
        'Cust_id': cust_id,
        'Cust_fname': cust_fname,
        'Cust_lname': cust_lname,
        'Cust_phone': cust_phone,
        'Cust_street': cust_street,
        'Cust_city': cust_city,
        'Cust_dist': cust_dist,
        'Cust_pin': cust_pin
    }
    
    return render_template('checkout.html', 
                          customer=customer_dict, 
                          cart_master_id=cart_master_id,
                          saved_cards=saved_cards, 
                          user_data=user_data)

@app.route('/process_payment', methods=['POST'])
def process_payment():
    # Fetch user data if logged in
    user_data = None
    if 'username' in session:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT cust_id FROM tbl_customer WHERE username = %s", (session['username'],))
            user_data = cursor.fetchone()
        connection.close()
    if not is_logged_in():
        flash('Please login to checkout', 'danger')
        return redirect(url_for('login'))
    
    db = get_db_connection()
    cursor = db.cursor()
    
    username = session['username']
    cursor.execute("SELECT Cust_id FROM tbl_customer WHERE Username = %s", (username,))
    cust_result = cursor.fetchone()
    
    # Handle cust_result as dict
    if isinstance(cust_result, dict):
        cust_id = cust_result['Cust_id']
    elif isinstance(cust_result, tuple):
        cust_id = cust_result[0]
    else:
        cust_id = cust_result
    
    cart_master_id = request.form.get('cart_master_id')
    selected_card_id = request.form.get('selected_card_id')
    save_card = 'save_card' in request.form
    
    if selected_card_id:
        card_id = selected_card_id
    else:
        # Validate and save new card
        card_no = request.form.get('card_no')
        card_name = request.form.get('card_name')
        exp_month = request.form.get('exp_month')
        exp_year = request.form.get('exp_year')
        cvv = request.form.get('cvv')
        
        if not (card_no and card_name and exp_month and exp_year and cvv):
            flash('Please fill all card details', 'danger')
            cursor.close()
            db.close()
            return redirect(url_for('checkout'))
        
        # Check card count
        cursor.execute("SELECT COUNT(*) as card_count FROM tbl_card WHERE Cust_id = %s", (cust_id,))
        card_count_result = cursor.fetchone()
        card_count = card_count_result['card_count'] if isinstance(card_count_result, dict) else card_count_result[0]
        
        if card_count >= 3 and save_card:
            flash('Maximum 3 cards can be saved', 'danger')
            cursor.close()
            db.close()
            return redirect(url_for('checkout'))
        
        if save_card:
            cursor.execute("""
                INSERT INTO tbl_card (Cust_id, Card_no, Card_name, Exp_month, Exp_year)
                VALUES (%s, %s, %s, %s, %s)
            """, (cust_id, card_no, card_name, exp_month, exp_year))
            card_id = cursor.lastrowid
        else:
            card_id = None  # Temporary payment without saving
    
# Create payment record
    pay_date = datetime.now()
    cursor.execute("""
        INSERT INTO tbl_payment (Cart_master_id, Card_id, Pay_date, Pay_status)
        VALUES (%s, %s, %s, 1)
    """, (cart_master_id, card_id, pay_date))  # Use card_id directly, None becomes NULL
    pay_id = cursor.lastrowid
    
    # Update cart status to 'Paid' after successful payment
    cursor.execute("""
        UPDATE tbl_cart_master 
        SET Cart_item_status = 'Paid' 
        WHERE Cart_master_id = %s
    """, (cart_master_id,))

    exp_month = int(request.form.get('exp_month'))
    exp_year = int(request.form.get('exp_year'))
    current_date = datetime.now()
    if exp_year < current_date.year or (exp_year == current_date.year and exp_month < current_date.month):
        flash('Card has expired', 'danger')
        return redirect(url_for('checkout'))
    
    # Reduce stock in tbl_purchase_child
    try:
        # Fetch items in the cart
        cursor.execute("""
            SELECT Item_id, Cart_qty 
            FROM tbl_cart_child 
            WHERE Cart_master_id = %s
        """, (cart_master_id,))
        cart_items = cursor.fetchall()

        # For each item in the cart, reduce stock in tbl_purchase_child
        for item in cart_items:
            item_id = item['Item_id'] if isinstance(item, dict) else item[0]
            cart_qty = item['Cart_qty'] if isinstance(item, dict) else item[1]

            # Find the corresponding purchase record (use the latest batch or a specific logic)
            cursor.execute("""
                SELECT Pur_child_id, Stock 
                FROM tbl_purchase_child 
                WHERE Item_id = %s AND Stock >= %s 
                ORDER BY Expiry_date ASC 
                LIMIT 1
            """, (item_id, cart_qty))
            purchase_record = cursor.fetchone()

            if not purchase_record:
                flash(f'Insufficient stock for Item ID {item_id}', 'danger')
                db.rollback()
                cursor.close()
                db.close()
                return redirect(url_for('checkout'))

            pur_child_id = purchase_record['Pur_child_id'] if isinstance(purchase_record, dict) else purchase_record[0]
            current_stock = purchase_record['Stock'] if isinstance(purchase_record, dict) else purchase_record[1]

            # Reduce stock
            new_stock = current_stock - cart_qty
            cursor.execute("""
                UPDATE tbl_purchase_child 
                SET Stock = %s 
                WHERE Pur_child_id = %s
            """, (new_stock, pur_child_id))

    except Exception as e:
        flash(f'Error updating stock: {str(e)}', 'danger')
        db.rollback()
        cursor.close()
        db.close()
        return redirect(url_for('checkout'))
    
    # Assign a courier after successful payment
    try:
        # Check if cart_master_id is already assigned to a courier
        cursor.execute("""
            SELECT Cassign_id FROM tbl_cassign WHERE Cart_master_id = %s
        """, (cart_master_id,))
        existing_assignment = cursor.fetchone()
        
        if existing_assignment:
            flash('This order is already assigned to a courier.', 'warning')
        else:
            # Fetch a random available courier (one with no active assignments)
            cursor.execute("""
                SELECT c.Courier_id 
                FROM tbl_courier c 
                LEFT JOIN tbl_cassign ca ON c.Courier_id = ca.Courier_id 
                WHERE c.Courier_status = 1 
                AND (ca.Courier_id IS NULL OR ca.Cassign_status = 'Delivered')
                ORDER BY RAND() 
                LIMIT 1
            """)
            available_courier = cursor.fetchone()
            
            if available_courier:
                courier_id = available_courier['Courier_id']
                assign_date = datetime.now().date()
                max_date_arrival = assign_date + timedelta(days=3)  # Example: 3 days for delivery
                
                cursor.execute("""
                    INSERT INTO tbl_cassign (Cart_master_id, Courier_id, Cassign_date, Max_date_arrival, Cassign_count, Cassign_status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (cart_master_id, courier_id, assign_date, max_date_arrival, 1, 'Assigned'))
                flash('Order successfully assigned to a courier!', 'success')
            else:
                flash('No available couriers at the moment.', 'warning')
    
    except Exception as e:
        flash(f'Error assigning courier: {str(e)}', 'danger')
        db.rollback()
        cursor.close()
        db.close()
        return redirect(url_for('checkout'))
    
    db.commit()
    cursor.close()
    db.close()
    
    #flash('Payment successful! Your order has been placed.', 'success')
    return redirect(url_for('order_confirmation', order_id=pay_id,user_data=user_data))
 
@app.route('/order_confirmation')
def order_confirmation():
    # Fetch user data if logged in
    user_data = None
    if 'username' in session:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT cust_id FROM tbl_customer WHERE username = %s", (session['username'],))
            user_data = cursor.fetchone()
        connection.close()
    
    if not is_logged_in():
        return redirect(url_for('login'))
    
    pay_id = request.args.get('order_id')  # This is pay_id from process_payment
    if not pay_id:
        flash('No order ID provided', 'danger')
        return redirect(url_for('home'))

    # Convert pay_id to cart_master_id
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("""
        SELECT Cart_master_id
        FROM tbl_payment
        WHERE Pay_id = %s AND Pay_status = 1
    """, (pay_id,))
    payment = cursor.fetchone()

    if not payment:
        flash('Invalid or unpaid order', 'danger')
        cursor.close()
        db.close()
        return redirect(url_for('home'))

    cart_master_id = payment['Cart_master_id'] if isinstance(payment, dict) else payment[0]
    cursor.close()
    db.close()

    return render_template('order_confirmation.html', order_id=cart_master_id, user_data=user_data)

# Register the download_invoice route
@app.route('/download_invoice/<int:order_id>')
def download_invoice_route(order_id):
    return download_invoice(order_id, is_logged_in, get_db_connection)

@app.route('/start_delivery/<int:cassign_id>', methods=['POST'])
def start_delivery(cassign_id):
    if not is_logged_in():
        flash('Please login to start delivery', 'danger')
        return redirect(url_for('login'))
    
    db = get_db_connection()
    cursor = db.cursor()
    
    # Fetch Cart_master_id from tbl_cassign
    cursor.execute("""
        SELECT Cart_master_id FROM tbl_cassign WHERE Cassign_id = %s
    """, (cassign_id,))
    assignment = cursor.fetchone()
    
    if not assignment:
        flash('Assignment not found.', 'danger')
        cursor.close()
        db.close()
        return redirect(url_for('courierdash'))
    
    cart_master_id = assignment['Cart_master_id']
    
    # Update tbl_cassign status to 'Out for Delivery'
    cursor.execute("""
        UPDATE tbl_cassign 
        SET Cassign_status = 'Out for Delivery' 
        WHERE Cassign_id = %s AND Cassign_status = 'Assigned'
    """, (cassign_id,))
    
    # Update tbl_cart_master status to 'Out for Delivery'
    cursor.execute("""
        UPDATE tbl_cart_master 
        SET Cart_item_status = 'Out for Delivery'
        WHERE Cart_master_id = %s
    """, (cart_master_id,))
    
    # Insert into tbl_delivery
    del_date = datetime.now().date()
    cursor.execute("""
        INSERT INTO tbl_delivery (Cassign_id, Cart_master_id, Del_date, Delivery_status)
        VALUES (%s, %s, %s, %s)
    """, (cassign_id, cart_master_id, del_date, 0))
    
    if cursor.rowcount > 0:
        flash('Delivery started successfully!', 'success')
    else:
        flash('Could not start delivery. Order might already be in progress.', 'danger')
    
    db.commit()
    cursor.close()
    db.close()
    
    return redirect(url_for('courierdash'))

@app.route('/mark_delivered/<int:cassign_id>', methods=['POST'])
def mark_delivered(cassign_id):
    if not is_logged_in():
        flash('Please login to mark delivery', 'danger')
        return redirect(url_for('login'))
    
    db = get_db_connection()
    cursor = db.cursor()
    
    # Update tbl_cassign status to 'Delivered'
    cursor.execute("""
        UPDATE tbl_cassign 
        SET Cassign_status = 'Delivered' 
        WHERE Cassign_id = %s AND Cassign_status = 'Out for Delivery'
    """, (cassign_id,))
    
    # Update tbl_cart_master status to 'Delivered'
    cursor.execute("""
        UPDATE tbl_cart_master cm
        JOIN tbl_cassign ca ON cm.Cart_master_id = ca.Cart_master_id
        SET cm.Cart_item_status = 'Delivered'
        WHERE ca.Cassign_id = %s
    """, (cassign_id,))
    
    # Update tbl_delivery status to 1 and set Del_date to current date
    del_date = datetime.now().date()
    cursor.execute("""
        UPDATE tbl_delivery 
        SET Delivery_status = 1, Del_date = %s
        WHERE Cassign_id = %s AND Delivery_status = 0
    """, (del_date, cassign_id))
    
    if cursor.rowcount > 0:
        flash('Order marked as delivered successfully!', 'success')
    else:
        flash('Could not mark as delivered. Ensure the order is out for delivery.', 'danger')
    
    db.commit()
    cursor.close()
    db.close()
    
    return redirect(url_for('courierdash'))

#All products page
@app.route('/products')
def products():
    db = get_db_connection()
    cursor = db.cursor()

    # Query to fetch only in-stock products (Stock > 0 and not expired)
    query = """
        SELECT i.Item_id, i.Item_name, i.Item_image, pc.Pur_unit_weight, pc.Sell_price,
           IFNULL(AVG(rr.Rating), 0) as avg_rating,
           COUNT(rr.Reviewrating_id) as review_count
        FROM tbl_item i
        LEFT JOIN (
            SELECT pc.Item_id, pc.Pur_unit_weight, pc.Sell_price, pc.Expiry_date
            FROM tbl_purchase_child pc
            WHERE pc.Stock > 0
            AND pc.Expiry_date > CURDATE()
            AND pc.Pur_child_id = (
                SELECT pc_inner.Pur_child_id
                FROM tbl_purchase_child pc_inner
                WHERE pc_inner.Item_id = pc.Item_id
                AND pc_inner.Pur_unit_weight = pc.Pur_unit_weight
                AND pc_inner.Stock > 0
                AND pc_inner.Expiry_date > CURDATE()
                ORDER BY pc_inner.Expiry_date ASC
                LIMIT 1
            )
        ) pc ON i.Item_id = pc.Item_id
        LEFT JOIN tbl_reviewrating rr ON i.Item_id = rr.item_id AND rr.status = 1
        WHERE i.Item_status = 1
        AND EXISTS (
            SELECT 1
            FROM tbl_purchase_child pc_check
            WHERE pc_check.Item_id = i.Item_id
            AND pc_check.Stock > 0
            AND pc_check.Expiry_date > CURDATE()
        )
    """

    params = ()
    filters = request.args.to_dict()

    # Apply filters based on request parameters
    if filters:
        conditions = []
        if 'category' in filters and filters['category']:
            # Split the category parameter into a list
            cat_list = filters['category'].split(',')
            cat_list = [cat.strip() for cat in cat_list if cat.strip()]  # Clean empty values
            if cat_list:
                # Fetch subcat_ids for all selected categories
                placeholders = ','.join(['%s'] * len(cat_list))
                cursor.execute(f"SELECT Subcat_id FROM tbl_subcategory WHERE Cat_id IN ({placeholders})", tuple(cat_list))
                subcat_ids = [row['Subcat_id'] for row in cursor.fetchall()]
                if subcat_ids:
                    placeholders = ','.join(['%s'] * len(subcat_ids))
                    conditions.append(f"i.Subcat_id IN ({placeholders})")
                    params += tuple(subcat_ids)

        if 'subcategory' in filters and filters['subcategory']:
            subcat_list = filters['subcategory'].split(',')
            placeholders = ','.join(['%s'] * len(subcat_list))
            conditions.append(f"i.Subcat_id IN (SELECT Subcat_id FROM tbl_subcategory WHERE Subcat_name IN ({placeholders}))")
            params += tuple(subcat_list)

        if 'price_max' in filters:  # Single price range filter
            conditions.append("pc.Sell_price <= %s")
            params += (filters['price_max'],)

        if conditions:
            query += " AND " + " AND ".join(conditions)

    query += " GROUP BY i.Item_id, pc.Pur_unit_weight, pc.Sell_price, pc.Expiry_date"
    query += " ORDER BY i.Item_id, pc.Pur_unit_weight"
    cursor.execute(query, params)
    raw_items = cursor.fetchall()

    # Process the items to group by Item_id and collect weight options
    items_dict = {}
    for item in raw_items:
        if not item:
            continue
            
        item_id = item['Item_id']
        
        # Convert binary image data
        if isinstance(item['Item_image'], bytes):
            item['Item_image'] = base64.b64encode(item['Item_image']).decode('utf-8')
        
        # If this is the first time we're seeing this item
        if item_id not in items_dict:
            items_dict[item_id] = {
                'Item_id': item_id,
                'Item_name': item['Item_name'],
                'Item_image': item['Item_image'],
                'Pur_unit_weight': item['Pur_unit_weight'],  # Default weight
                'Sell_price': item['Sell_price'],            # Default price
                'avg_rating': item['avg_rating'],            
                'review_count': item['review_count'], 
                'weight_options': []
            }
        
        # Add this weight option
        items_dict[item_id]['weight_options'].append({
            'weight': item['Pur_unit_weight'],
            'price': item['Sell_price']
        })
    
    # Convert dictionary to list for template
    items = list(items_dict.values())

    # Fetch all categories and subcategories for the filter sidebar
    cursor.execute("SELECT Cat_id, Cat_name FROM tbl_category WHERE Cat_status = 1")
    categories = cursor.fetchall()

    cursor.execute("SELECT Subcat_id, Cat_id, Subcat_name FROM tbl_subcategory WHERE Subcat_status = 1")
    subcategories = cursor.fetchall()
    category_subcat_map = {}
    for subcat in subcategories:
        cat_id, subcat_name = subcat['Cat_id'], subcat['Subcat_name']
        if cat_id not in category_subcat_map:
            category_subcat_map[cat_id] = []
        category_subcat_map[cat_id].append(subcat_name)

    cursor.close()

    # Fetch user data if logged in
    user_data = None
    if 'username' in session:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT cust_id FROM tbl_customer WHERE username = %s", (session['username'],))
            user_data = cursor.fetchone()

        connection.close()
    return render_template('products.html', items=items, categories=categories, category_subcat_map=category_subcat_map, filters=filters,user_data=user_data)


@app.route('/about')
def about():
    # Fetch user data if logged in
    user_data = None
    if 'username' in session:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT cust_id FROM tbl_customer WHERE username = %s", (session['username'],))
            user_data = cursor.fetchone()

        connection.close()
    return render_template("about.html",user_data=user_data)

@app.route('/contact')
def contact():
    # Fetch user data if logged in
    user_data = None
    if 'username' in session:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT cust_id FROM tbl_customer WHERE username = %s", (session['username'],))
            user_data = cursor.fetchone()

        connection.close()
    return render_template("contact.html",user_data=user_data)

@app.route('/admindash')
def admindash():
    # Connect to the database
    conn = pymysql.connect(host='localhost', user='root', password='', database='spice_bazaar')
    cursor = conn.cursor()
    
    # Query to count the number of categories
    cursor.execute("SELECT COUNT(*) FROM tbl_category")
    category_count = cursor.fetchone()[0]  # Get the count value
    
    # Query to count the number of subcategories
    cursor.execute("SELECT COUNT(*) FROM tbl_subcategory")
    subcategory_count = cursor.fetchone()[0]  # Get the count value

    # Query to count the number of items
    cursor.execute("SELECT COUNT(*) FROM tbl_item")
    item_count = cursor.fetchone()[0]  # Get the count value

    # Query to count the number of couriers
    cursor.execute("SELECT COUNT(*) FROM tbl_courier")
    courier_count = cursor.fetchone()[0]  # Get the count value

    # Query to count the number of staff
    cursor.execute("SELECT COUNT(*) FROM tbl_staff")
    staff_count = cursor.fetchone()[0]  # Get the count value

    # Query to count the number of vendor
    cursor.execute("SELECT COUNT(*) FROM tbl_vendor")
    vendor_count = cursor.fetchone()[0]  # Get the count value

    # Query to count the number of purchases
    cursor.execute("SELECT COUNT(*) FROM tbl_purchase_master")
    purchase_count = cursor.fetchone()[0]  # Get the count value

    # Query to count the number of customer
    cursor.execute("SELECT COUNT(*) FROM tbl_customer")
    customer_count = cursor.fetchone()[0]  # Get the count value
    conn.close()
    
    # Pass category_count to the template
    return render_template('admindash.html', category_count=category_count,
                           subcategory_count=subcategory_count,courier_count=courier_count,
                           customer_count=customer_count,item_count=item_count,
                           vendor_count=vendor_count,staff_count=staff_count,purchase_count=purchase_count)

# Category management
@app.route("/category_management")
def category_management():
    user_data = None
    if 'username' in session:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT staff_id, username FROM tbl_staff WHERE username = %s", (session['username'],))
            user_data = cursor.fetchone()
        connection.close()
    categories = fetch_categories()
    return render_template("category_management.html", categories=categories,user_data=user_data)

@app.route("/add_category", methods=["POST"])
def add_category_route():
    return add_category()

@app.route("/edit_category/<int:cat_id>", methods=["POST", "GET"])
def edit_category_route(cat_id):
    user_data = None
    if 'username' in session:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT staff_id, username FROM tbl_staff WHERE username = %s", (session['username'],))
            user_data = cursor.fetchone()
        connection.close()
    category = fetch_edit_category(cat_id)
    
    categories = fetch_categories()
    if request.method == "POST":
        return edit_category(cat_id)
    
    return render_template("category_management.html", category=category, categories=categories,user_data=user_data)

@app.route("/change_category_status/<int:cat_id>/<int:status>", methods=["POST"])
def change_category_status_route(cat_id, status):
    change_category_status(cat_id, status)
    return redirect(url_for("category_management"))

def fetch_subcategories(): 
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT s.Subcat_id, s.Subcat_name, s.Subcat_desc, s.Subcat_image, s.Subcat_status, c.Cat_name  
            FROM tbl_subcategory s
            JOIN tbl_category c ON s.Cat_id = c.Cat_id
        """)
        subcategories = cursor.fetchall()

        # Convert BLOB images to Base64
        for subcategory in subcategories:
            if subcategory["Subcat_image"]:  # Check if image exists
                subcategory["Subcat_image"] = base64.b64encode(subcategory["Subcat_image"]).decode("utf-8")
        
        return subcategories
    except Exception as e:
        print(f"Error fetching subcategories: {str(e)}")
        return []
    finally:
        connection.close()

#Subcategory management
@app.route("/subcategory_management")
def subcategory_management():
    user_data = None
    if 'username' in session:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT staff_id, username FROM tbl_staff WHERE username = %s", (session['username'],))
            user_data = cursor.fetchone()
        connection.close()
    categories = fetch_categories()  # Fetch categories from the database
    subcategories = fetch_subcategories()
    print("Subcategories Data:", subcategories)
    return render_template("subcategory_management.html", categories=categories,subcategories=subcategories,user_data=user_data)

@app.route("/add_subcategory", methods=["POST"])
def add_subcategory_route():
    return add_subcategory()

@app.route("/edit_subcategory/<int:subcat_id>", methods=["POST", "GET"])
def edit_subcategory_route(subcat_id):
    user_data = None
    if 'username' in session:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT staff_id, username FROM tbl_staff WHERE username = %s", (session['username'],))
            user_data = cursor.fetchone()
        connection.close()
    subcategory = fetch_edit_subcategory(subcat_id)
    categories = fetch_categories()
    subcategories = fetch_subcategories()
    if request.method == "POST":
        return edit_subcategory(subcat_id)
    
    return render_template("subcategory_management.html", subcategory=subcategory, subcategories=subcategories,categories=categories,user_data=user_data)

@app.route("/change_subcategory_status/<int:subcat_id>/<int:status>", methods=["POST"])
def change_subcategory_status_route(subcat_id, status):
    change_subcategory_status(subcat_id, status)
    return redirect(url_for("subcategory_management"))

def fetch_items():
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT i.Item_id, i.Item_name, i.Item_desc, i.Item_image, i.Item_profit, i.Item_status, s.Subcat_name
            FROM tbl_item i
            JOIN tbl_subcategory s ON i.Subcat_id = s.Subcat_id
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

#Item management
@app.route("/item_management")
def item_management():
    user_data = None
    if 'username' in session:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT staff_id, username FROM tbl_staff WHERE username = %s", (session['username'],))
            user_data = cursor.fetchone()
        connection.close()
    subcategories = fetch_subcategories() # Fetch subcategories from the database
    items = fetch_items()
    return render_template("item_management.html", subcategories=subcategories, items=items,user_data=user_data)

@app.route("/add_item", methods=["POST"])
def add_item_route():
    return add_item()

@app.route("/edit_item/<int:item_id>", methods=["POST", "GET"])
def edit_item_route(item_id):
    user_data = None
    if 'username' in session:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT staff_id, username FROM tbl_staff WHERE username = %s", (session['username'],))
            user_data = cursor.fetchone()
        connection.close()
    item = fetch_edit_item(item_id)
    subcategories = fetch_subcategories()
    items = fetch_items()
    if request.method == "POST":
        return edit_item(item_id)
    
    return render_template("item_management.html", item=item, subcategories=subcategories, items=items,user_data=user_data)

@app.route("/change_item_status/<int:item_id>/<int:status>", methods=["POST"])
def change_item_status_route(item_id, status):
    change_item_status(item_id, status)
    return redirect(url_for("item_management"))

def fetch_purchases():
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT pm.Pur_master_id, v.Vendor_name, pm.Pur_date, pm.Pur_tot_amt
            FROM tbl_purchase_master pm
            JOIN tbl_vendor v ON pm.Vendor_id = v.Vendor_id
            ORDER BY pm.Pur_date DESC
        """)
        purchases = cursor.fetchall()
        
        # Format dates
        for purchase in purchases:
            purchase['Pur_date'] = purchase['Pur_date'].strftime('%Y-%m-%d')
            
        return purchases
    except Exception as e:
        print(f"Error fetching purchases: {str(e)}")
        return []
    finally:
        connection.close()

#Purchase Management
@app.route("/purchase_management")
def purchase_management():
    user_data = None
    if 'username' in session:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT staff_id, username FROM tbl_staff WHERE username = %s", (session['username'],))
            user_data = cursor.fetchone()
        connection.close()
    
    session['staff_id'] = user_data['staff_id']

    if not session.get('username'):
        return redirect(url_for('loginpage'))
    vendors = fetch_vendors()
    items = fetch_items()
    purchases = fetch_purchases()
    
    return render_template('purchase_management.html', 
                         vendors=vendors, 
                         items=items, 
                         purchases=purchases,
                         edit_mode=False,user_data=user_data)

@app.route("/add_purchase", methods=["POST"])
def add_purchase_route():
    if not session.get('username'):
        return redirect(url_for('loginpage'))
    return add_purchase()

@app.route('/purchase/edit/<int:pur_master_id>', methods=['GET', 'POST'])
def edit_purchase_route(pur_master_id):
    user_data = None
    if 'username' in session:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT staff_id, username FROM tbl_staff WHERE username = %s", (session['username'],))
            user_data = cursor.fetchone()
        connection.close()
    if request.method == 'POST':
        return edit_purchase(pur_master_id)
    
    purchase_master, purchase_children = fetch_purchase_for_edit(pur_master_id)
    vendors = fetch_vendors()
    items = fetch_items()
    purchases = fetch_purchases()
    return render_template('purchase_management.html', 
                           edit_mode=True, 
                           purchase_master=purchase_master, 
                           purchase_children=purchase_children,
                           vendors=vendors,purchases=purchases,
                           items=items,user_data=user_data)

'''
@app.route("/purchase_details/<int:pur_master_id>")
def purchase_details_route(pur_master_id):
    if not session.get('username'):
        return redirect(url_for('loginpage'))
    
    purchase = fetch_purchase_by_id(pur_master_id)
    if not purchase:
        return "Purchase not found", 404
    
    return render_template("purchase_details.html", purchase=purchase)
'''
#to display deatils when clicking on view details button (individual purchase details)
@app.route('/purchase/details/<int:pur_id>')
def purchase_details(pur_id):
    # Extract staff_id from query parameters
    #staff_id = request.args.get('staff_id')

    #if not staff_id:
        #return "Staff ID is missing", 400  # You can add a fallback message or handle this differently
    
    # Connect to the database
    connection = pymysql.connect(host='localhost',
                                 user='root',
                                 password='',
                                 database='spice_bazaar',
                                 cursorclass=pymysql.cursors.DictCursor)
    try:
        # Get purchase master details
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT Pur_master_id, Vendor_id, Pur_date, Pur_tot_amt
                FROM tbl_purchase_master
                WHERE Pur_master_id = %s
            """, (pur_id,))
            purchase = cursor.fetchone()

            if purchase is None:
                return "Purchase not found", 404

            # Get vendor name
            cursor.execute("""
                SELECT Vendor_name
                FROM tbl_vendor
                WHERE Vendor_id = %s
            """, (purchase['Vendor_id'],))
            vendor_name = cursor.fetchone()
            vendor_name = vendor_name['Vendor_name'] if vendor_name else "Unknown Vendor"
            '''
            # Get the staff name
            cursor.execute("""
                SELECT Staff_name
                FROM tbl_staff
                WHERE Staff_id = %s
            """, (staff_id,))
            staff_name = cursor.fetchone()
            staff_name = staff_name['Staff_name'] if staff_name else "Unknown Staff"
            '''


            # Get the items for the purchase
            cursor.execute("""
                SELECT i.Item_name, p.Pur_qty, p.Pur_unit_price, p.Stock, p.Sell_price, p.Batch_no, p.Expiry_date, p.Item_dom
                ,p.Pur_unit_weight FROM tbl_purchase_child p
                JOIN tbl_item i ON p.Item_id = i.Item_id
                WHERE p.Pur_master_id = %s
            """, (pur_id,))
            purchase_items = cursor.fetchall()

    finally:
        connection.close()

    return render_template('purchase_details.html', 
                           purchase=purchase, 
                           purchase_items=purchase_items, 
                           vendor_name=vendor_name, 
                           )

#Courier Management
@app.route("/courier_management")
def courier_management():
    user_data = None
    if 'username' in session:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT staff_id, username FROM tbl_staff WHERE username = %s", (session['username'],))
            user_data = cursor.fetchone()
        connection.close()
    
    session['staff_id'] = user_data['staff_id']
    usern = get_available_courier_usernames()
    all_couriers = get_all_couriers()  
    return render_template("courier_management.html", usern=usern,
            couriers=all_couriers,user_data=user_data)

@app.route("/add_courier", methods=["POST"])
def add_courier_route():
    return add_courier()

@app.route("/edit_courier/<int:courier_id>", methods=["POST", "GET"])
def edit_courier_route(courier_id):
    user_data = None
    if 'username' in session:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT staff_id, username FROM tbl_staff WHERE username = %s", (session['username'],))
            user_data = cursor.fetchone()
        connection.close()
    # Fetch the courier details for editing
    courier = fetch_edit_courier(courier_id)

    # Fetch all couriers for the table
    couriers = get_all_couriers()

    #to get all available courier usernames
    usern=get_available_courier_usernames()

    # Handle POST requests (form submission)
    if request.method == "POST":
        return edit_courier(courier_id)

    # Render the courier management template with the courier data
    return render_template("courier_management.html", courier=courier, couriers=couriers,usern=usern,user_data=user_data)

@app.route("/change_courier_status/<int:courier_id>/<int:status>", methods=["POST"])
def change_courier_status_route(courier_id, status):
    change_courier_status(courier_id, status)
    return redirect(url_for("courier_management"))

#vendor management
@app.route("/vendor_management")
def vendor_management():
    user_data = None
    if 'username' in session:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT staff_id, username FROM tbl_staff WHERE username = %s", (session['username'],))
            user_data = cursor.fetchone()
        connection.close()
    
    session['staff_id'] = user_data['staff_id']
    all_vendors = get_all_vendors()  
    return render_template("vendor_management.html",
            vendors=all_vendors,user_data=user_data)

@app.route("/add_vendor", methods=["POST"])
def add_vendor_route():
    return add_vendor()

@app.route("/edit_vendor/<int:vendor_id>", methods=["POST", "GET"])
def edit_vendor_route(vendor_id):
    user_data = None
    if 'username' in session:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT staff_id, username FROM tbl_staff WHERE username = %s", (session['username'],))
            user_data = cursor.fetchone()
        connection.close()
    # Fetch the vendor details for editing
    vendor = fetch_edit_vendor(vendor_id)

    # Fetch all vendors for the table
    vendors = get_all_vendors()
   
    # Handle POST requests (form submission)
    if request.method == "POST":
        return edit_vendor(vendor_id)

    # Render the vendor management template with the vendor data
    return render_template("vendor_management.html", vendor=vendor, vendors=vendors,user_data=user_data)

@app.route("/change_vendor_status/<int:vendor_id>/<int:status>", methods=["POST"])
def change_vendor_status_route(vendor_id, status):
    change_vendor_status(vendor_id, status)
    return redirect(url_for("vendor_management"))

#Signup Management
@app.route('/signupauthen', methods=['GET', 'POST'])
def signup_route():
    return signupauthen_route()

@app.route('/staff_signup', methods=['GET', 'POST'])
def staff_signup():
    # Get username from session
    staff_username = session.get('username')
    
    if not staff_username:
        # Redirect if no username in session
        flash('Please complete initial signup first', 'error')
        return redirect(url_for('signupauthen'))
    
    if request.method == 'POST':
        # Add the username to the form data
        form_data = request.form.copy()
        form_data['username'] = staff_username
        
        success, result = staff_signup_user(form_data)
        if not success:
            # Preserve username when re-rendering
            return render_template('staff_signup.html', 
                                   errors=result, 
                                   username=staff_username)
        
        # Clear session after successful signup
        session.pop('username', None)
        
        flash('Staff Signup successful!', 'success')
        return redirect(url_for('loginpage'))  
    
    return render_template('staff_signup.html', 
                           errors={}, 
                           username=staff_username)

@app.route('/customer_signup', methods=['GET', 'POST'])
def customer_signup():
    # Get username from session
    customer_username = session.get('username')
    
    if not customer_username:
        # Redirect if no username in session
        flash('Please complete initial signup first', 'error')
        return redirect(url_for('signupauthen'))
    
    if request.method == 'POST':
        # Add the username to the form data
        form_data = request.form.copy()
        form_data['username'] = customer_username
        
        success, result = customer_signup_user(form_data)
        if not success:
            # Preserve username when re-rendering
            return render_template('customer_signup.html', 
                                   errors=result, 
                                   username=customer_username)
        
        # Clear session after successful signup
        session.pop('username', None)
        
        flash('Customer Signup successful!', 'success')
        return redirect(url_for('loginpage'))  
    
    return render_template('customer_signup.html', 
                           errors={}, 
                           username=customer_username)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == "GET":
        return render_template("loginpage.html", show_forgot_password=True)

    step = request.form.get("step")
    username = request.form.get("username") or request.form.get("forgot-username")

    if step == "check_email":
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # Check if the username exists in tbl_login and get Login_type
                sql = "SELECT Login_type FROM tbl_login WHERE Username = %s"
                cursor.execute(sql, (username,))
                login_result = cursor.fetchone()

                if not login_result:
                    flash("Email not found!", "error")
                    return render_template("loginpage.html", show_forgot_password=True, username=username)

                login_type = login_result["Login_type"]

                # Determine the table to query based on Login_type
                if login_type == "Customer":
                    sql = "SELECT Favorite_Food FROM tbl_customer WHERE Username = %s"
                elif login_type == "Staff":
                    sql = "SELECT Favorite_Food FROM tbl_staff WHERE Username = %s"
                elif login_type == "Courier":
                    sql = "SELECT Favorite_Food FROM tbl_courier WHERE Username = %s"
                else:
                    flash("Invalid user type!", "error")
                    return render_template("loginpage.html", show_forgot_password=True, username=username)

                cursor.execute(sql, (username,))
                result = cursor.fetchone()

                if not result:
                    flash("User details not found!", "error")
                    return render_template("loginpage.html", show_forgot_password=True, username=username)

                # If we reach here, the user exists and we can show the security question
                return render_template("loginpage.html", show_forgot_password=True, security_question_shown=True, username=username)
        finally:
            connection.close()

    elif step == "check_answer":
        security_answer = request.form.get("security-answer")
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # Get Login_type from tbl_login
                sql = "SELECT Login_type FROM tbl_login WHERE Username = %s"
                cursor.execute(sql, (username,))
                login_result = cursor.fetchone()

                if not login_result:
                    flash("Email not found!", "error")
                    return render_template("loginpage.html", show_forgot_password=True, security_question_shown=True, username=username)

                login_type = login_result["Login_type"]

                # Fetch Favorite_Food based on Login_type
                if login_type == "Customer":
                    sql = "SELECT Favorite_Food FROM tbl_customer WHERE Username = %s"
                elif login_type == "Staff":
                    sql = "SELECT Favorite_Food FROM tbl_staff WHERE Username = %s"
                elif login_type == "Courier":
                    sql = "SELECT Favorite_Food FROM tbl_courier WHERE Username = %s"
                else:
                    flash("Invalid user type!", "error")
                    return render_template("loginpage.html", show_forgot_password=True, security_question_shown=True, username=username)

                cursor.execute(sql, (username,))
                result = cursor.fetchone()

                if not result or result["Favorite_Food"].lower() != security_answer.lower():
                    flash("Incorrect security answer!", "error")
                    return render_template("loginpage.html", show_forgot_password=True, security_question_shown=True, username=username)

                # If the answer is correct, show the password reset form
                return render_template("loginpage.html", show_forgot_password=True, password_reset_shown=True, username=username)
        finally:
            connection.close()

    elif step == "update_password":
        new_password = request.form.get("new-password")
        confirm_password = request.form.get("confirm-password")

        # Password validation
        errors = {}
        if not new_password:
            errors['password'] = "Password is required."
        elif not (8 <= len(new_password) <= 10):
            errors['password'] = "Password must be between 8 and 10 characters."
        elif not re.search(r"[A-Z]", new_password):
            errors['password'] = "Password must contain at least one uppercase letter."
        elif not re.search(r"[a-z]", new_password):
            errors['password'] = "Password must contain at least one lowercase letter."
        elif not re.search(r"[0-9]", new_password):
            errors['password'] = "Password must contain at least one number."
        elif not re.search(r"[!@#]", new_password):
            errors['password'] = "Password must contain at least one special character (!, @, or #)."
        elif new_password != confirm_password:
            errors['password'] = "Passwords do not match."

        if errors:
            for error in errors.values():
                flash(error, "error")
            return render_template("loginpage.html", show_forgot_password=True, password_reset_shown=True, username=username)

        # Update the password in tbl_login
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                sql = "UPDATE tbl_login SET Login_password = %s WHERE Username = %s"
                cursor.execute(sql, (new_password, username))
                connection.commit()
            flash("Password updated successfully!", "success")
            return redirect(url_for("loginpage"))
        except Exception as e:
            flash(f"Error updating password: {str(e)}", "error")
            return render_template("loginpage.html", show_forgot_password=True, password_reset_shown=True, username=username)
        finally:
            connection.close()

    return render_template("loginpage.html", show_forgot_password=True)

@app.route('/loginpage', methods=['GET', 'POST'])
def loginpage():
    return login_route()

@app.route('/staffdash')
def staffdash():
    # Connect to the database
    conn = pymysql.connect(host='localhost', user='root', password='', database='spice_bazaar')
    cursor = conn.cursor()
    
    # Query to count the number of categories
    cursor.execute("SELECT COUNT(*) FROM tbl_category")
    category_count = cursor.fetchone()[0]  # Get the count value
    
    # Query to count the number of subcategories
    cursor.execute("SELECT COUNT(*) FROM tbl_subcategory")
    subcategory_count = cursor.fetchone()[0]  # Get the count value

    # Query to count the number of couriers
    cursor.execute("SELECT COUNT(*) FROM tbl_courier")
    courier_count = cursor.fetchone()[0]  # Get the count value

    # Query to count the number of staff
    cursor.execute("SELECT COUNT(*) FROM tbl_staff")
    staff_count = cursor.fetchone()[0]  # Get the count value

    # Query to count the number of vendor
    cursor.execute("SELECT COUNT(*) FROM tbl_vendor")
    vendor_count = cursor.fetchone()[0]  # Get the count value

    # Query to count the number of staff
    cursor.execute("SELECT COUNT(*) FROM tbl_customer")
    customer_count = cursor.fetchone()[0]  # Get the count value

    # Query to count the number of purchases
    cursor.execute("SELECT COUNT(*) FROM tbl_purchase_master")
    purchase_count = cursor.fetchone()[0]  # Get the count value

    # Query to count the number of items
    cursor.execute("SELECT COUNT(*) FROM tbl_item")
    item_count = cursor.fetchone()[0]  # Get the count value

    conn.close()
    
    # Pass category_count to the template
    return render_template('staffdash.html', category_count=category_count,subcategory_count=subcategory_count,
                           courier_count=courier_count,
                           staff_count=staff_count,customer_count=customer_count,
                           vendor_count=vendor_count,item_count=item_count,purchase_count=purchase_count)

@app.route('/customerdash')
def customerdash():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    db = get_db_connection()
    cursor = db.cursor()
    
    # Get cust_id
    cursor.execute("SELECT Cust_id FROM tbl_customer WHERE Username = %s", (session['username'],))
    customer_row = cursor.fetchone()
    
    if not customer_row:
        flash('Customer profile not found.', 'danger')
        cursor.close()
        db.close()
        return redirect(url_for('login'))
    
    cust_id = customer_row[0] if isinstance(customer_row, tuple) else customer_row['Cust_id']
    
    cursor.execute("""
                SELECT 
                    cm.Cart_master_id, 
                    cm.Cart_item_status, 
                    ca.Max_date_arrival,
                    cm.Cart_tot_amt,
                    GROUP_CONCAT(
                        CONCAT(
                            i.Item_id, ':', 
                            i.Item_name, ':', 
                            pc.Pur_unit_weight, ':', 
                            cc.Cart_qty, ':', 
                            cc.Cart_price, ':',
                            IFNULL(HEX(i.Item_image), 'NULL')
                        ) SEPARATOR '|'
                    ) AS order_items
                FROM tbl_cart_master cm
                LEFT JOIN tbl_cart_child cc ON cm.Cart_master_id = cc.Cart_master_id
                LEFT JOIN tbl_item i ON cc.Item_id = i.Item_id
                LEFT JOIN tbl_cassign ca ON cm.Cart_master_id = ca.Cart_master_id
                LEFT JOIN tbl_purchase_child pc ON i.Item_id = pc.Item_id 
                    AND pc.Sell_price = cc.Cart_unit_price 
                WHERE cm.Cust_id = %s 
                   AND cm.Cart_item_status != 'Active'
                GROUP BY cm.Cart_master_id, cm.Cart_item_status, cm.Cart_tot_amt
                ORDER BY cm.Cart_master_id DESC
            """, (cust_id,))
    orders = cursor.fetchall()

    processed_orders = []
    for order in orders:
        order_dict = {
            'order_id': order['Cart_master_id'],
            'status': order['Cart_item_status'],
            'total_amount': order['Cart_tot_amt'],
            'max_date_arrival': order['Max_date_arrival'],
            'order_items': []
        }
        
        if order['order_items']:
            items = order['order_items'].split('|')
            for item in items:
                parts = item.split(':')
                if len(parts) == 6:
                    item_id, item_name, unit_weight, qty, price, item_image = parts
                    
                    # Convert HEX-encoded image back to bytes and then to base64
                    image_base64 = None
                    if item_image != 'NULL':
                        try:
                            image_bytes = bytes.fromhex(item_image)
                            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                        except Exception as e:
                            print(f"Error decoding image for item {item_id}: {e}")
                            
                    order_dict['order_items'].append({
                        'item_id': item_id,
                        'item_name': item_name,
                        'unit_weight': unit_weight,
                        'quantity': qty,
                        'price': price,
                        'item_image': image_base64
                    })
            
            processed_orders.append(order_dict)
    
    cursor.close()
    db.close()
    return render_template('customerdash.html', orders=processed_orders)

def validate_security_answer(security_answer):
    errors = {}
    
    # Check if answer is None or empty
    if not security_answer or security_answer.strip() == '':
        errors['security_answer'] = "Security answer is required."
        return errors
    
    # Trim whitespace
    security_answer = security_answer.strip()
    
    # Length checks
    if len(security_answer) < 3:
        errors['security_answer'] = "Security answer must be at least 3 characters long."
    elif len(security_answer) > 20:
        errors['security_answer'] = "Security answer must not exceed 20 characters."
    
    # Alphabetic check with case-insensitive regex
    if not re.match(r'^[A-Za-z]+$', security_answer):
        errors['security_answer'] = "Security answer must contain only alphabetic characters (no spaces, numbers, or special symbols)."
    
    return errors

@app.route('/courierdash')
def courierdash():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    db = get_db_connection()
    cursor = db.cursor()  # Use dictionary cursor for easier access
    
    try:

        
        # Fetch courier details
        cursor.execute(
            "SELECT Courier_id, Favorite_Food FROM tbl_courier WHERE Username = %s", 
            (session['username'],)
        )
        courier = cursor.fetchone()
        
        # More detailed debugging
        if not courier:
            flash('Courier profile not found.', 'danger')
            return redirect(url_for('login'))
        
        # Check if security answer exists
        has_security_answer = courier['Favorite_Food'] is not None
        print(f"Has Security Answer: {has_security_answer}")
        
        # Fetch assigned orders
        cursor.execute("""
            SELECT 
                ca.Cassign_id, 
                ca.Cart_master_id, 
                ca.Cassign_date, 
                ca.Max_date_arrival, 
                ca.Cassign_status, 
                c.Cust_fname, 
                c.Cust_lname, 
                c.Cust_street, 
                c.Cust_city, 
                c.Cust_dist, 
                c.Cust_pin, 
                c.Cust_phone, 
                COUNT(cc.Item_id) as item_count, 
                d.Del_date, 
                d.Delivery_status 
            FROM tbl_cassign ca 
            JOIN tbl_cart_master cm ON ca.Cart_master_id = cm.Cart_master_id 
            JOIN tbl_customer c ON cm.Cust_id = c.Cust_id 
            LEFT JOIN tbl_cart_child cc ON cm.Cart_master_id = cc.Cart_master_id 
            LEFT JOIN tbl_delivery d ON ca.Cassign_id = d.Cassign_id 
            WHERE ca.Courier_id = %s 
            GROUP BY 
                ca.Cassign_id, ca.Cart_master_id, ca.Cassign_date, 
                ca.Max_date_arrival, ca.Cassign_status, c.Cust_fname, 
                c.Cust_lname, c.Cust_street, c.Cust_city, c.Cust_dist, 
                c.Cust_pin, c.Cust_phone, d.Del_date, d.Delivery_status
        """, (courier['Courier_id'],))
        
        assigned_orders = cursor.fetchall()
        
        return render_template(
            'courierdash.html', 
            assigned_orders=assigned_orders, 
            has_security_answer=has_security_answer
        )
    
    except Exception as e:
        # Comprehensive error logging
        flash(f"Error loading dashboard: {str(e)}", "error")
        return redirect(url_for('login'))
    
    finally:
        cursor.close()
        db.close()

@app.route('/set_security_answer', methods=['POST'])
def set_security_answer():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    security_answer = request.form.get('security_answer', '').strip()
    
    # Validate security answer
    errors = validate_security_answer(security_answer)
    if errors:
        for error in errors.values():
            flash(error, "error")
        return redirect(url_for('courierdash'))
    
    db = get_db_connection()
    try:
        with db.cursor() as cursor:
            
            sql = "UPDATE tbl_courier SET Favorite_Food = %s WHERE Username = %s"
            cursor.execute(sql, (security_answer, session['username']))
            
            # Check if update was successful
            if cursor.rowcount == 0:
                flash("Failed to update security answer. User not found.", "error")
            else:
                db.commit()
                flash("Security answer saved successfully!", "success")
    
    except Exception as e:
        # Comprehensive error handlings
        flash(f"Error saving security answer: {str(e)}", "error")
        db.rollback()
    
    finally:
        db.close()
    
    return redirect(url_for('courierdash'))

@app.route('/customer_management')
def customer_management():
    customers = fetch_customers()
    return render_template("customer_management.html", customers=customers)

@app.route("/change_customer_status/<string:username>/<int:status>", methods=["POST"])
def change_customer_status_route(username, status):
    change_customer_status(username, status)
    return redirect(url_for("customer_management"))

@app.route('/staffmanagement')
def staff_management():
    staffs = fetch_staff() 
    return render_template("staff_management.html", staff_members=staffs)

@app.route("/change_staff_status/<string:username>/<int:status>", methods=["POST"])
def change_staff_status_route(username, status):
    change_staff_status(username, status)
    return redirect(url_for("staff_management"))

# Register the admin_reports route directly
@app.route('/admin_reports', methods=['GET', 'POST'])
def admin_reports_route():
    return admin_reports(app, session)  # Call the function from reports.py

#Search bar
@app.route('/search_items')
def search_items():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Search items by name or description,or weight (pur_unit_weight) only showing active items with stock
            cursor.execute("""
                SELECT DISTINCT i.Item_id, i.Item_name, i.Item_image, pc.Pur_unit_weight
                FROM tbl_item i
                LEFT JOIN tbl_purchase_child pc ON i.Item_id = pc.Item_id
                WHERE (i.Item_name LIKE %s OR i.Item_desc LIKE %s OR pc.Pur_unit_weight LIKE %s)
                AND i.Item_status = 1
                AND pc.Stock > 0
                AND pc.Expiry_date > CURDATE()
                ORDER BY i.Item_name
                LIMIT 10
            """, (f"{query}%", f"%{query}%", f"{query}%"))
            items = cursor.fetchall()

            # Convert Item_image (BLOB) to Base64
            for item in items:
                if item['Item_image'] and isinstance(item['Item_image'], bytes):
                    item['Item_image'] = base64.b64encode(item['Item_image']).decode('utf-8')
                else:
                    item['Item_image'] = None  # Handle cases where there is no image

            return jsonify(items)
    finally:
        connection.close()

# Customer Profile View and edit
@app.route('/profile', methods=['GET'])
def profile():
    if not is_logged_in():
        flash('Please login to view your profile', 'danger')
        return redirect(url_for('loginpage'))
    
    db = get_db_connection()
    cursor = db.cursor()
    
    # Fetch customer details
    cursor.execute("""
        SELECT Cust_fname, Cust_lname, Cust_city, Cust_dist, Cust_pin, 
               Cust_street, Cust_phone, Cust_gender, Cust_dob, Cust_join, Username
        FROM tbl_customer 
        WHERE Username = %s
    """, (session['username'],))
    customer = cursor.fetchone()
    
    cursor.close()
    db.close()
    
    if not customer:
        flash('Customer profile not found', 'danger')
        return redirect(url_for('home'))
    
    return render_template('profile.html', customer=customer)

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if not is_logged_in():
        flash('Please login to edit your profile', 'danger')
        return redirect(url_for('loginpage'))
    
    if request.method == 'POST':
        # Fetch current customer data
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("""
            SELECT Cust_id, Cust_phone 
            FROM tbl_customer 
            WHERE Username = %s
        """, (session['username'],))
        current_data = cursor.fetchone()
        cursor.close()
        db.close()
        
        if not current_data:
            flash('Customer profile not found', 'danger')
            return redirect(url_for('profile'))
        
        cust_id = current_data['Cust_id']
        current_phone = current_data['Cust_phone']

        form_data = {
            'fname': request.form.get('fname'),
            'lname': request.form.get('lname'),
            'city': request.form.get('city'),
            'district': request.form.get('district'),
            'pin': request.form.get('pin'),
            'street': request.form.get('street'),
            'phone': request.form.get('phone'),
            'gender': request.form.get('gender'),
            'dob': request.form.get('dob')
        }
        
        # Validate with current phone and cust_id, remove security_answer from validation
        errors = {k: v for k, v in validate_user_input(form_data, current_phone=current_phone, cust_id=cust_id).items() 
                  if k != 'security_answer'}
        
        if errors:
            for field, error in errors.items():
                flash(f"{field}: {error}", "error")
            return redirect(url_for('profile'))
        
        # Update profile
        db = get_db_connection()
        cursor = db.cursor()
        try:
            cursor.execute("""
                UPDATE tbl_customer 
                SET Cust_fname = %s, Cust_lname = %s, Cust_city = %s, Cust_dist = %s, 
                    Cust_pin = %s, Cust_street = %s, Cust_phone = %s, Cust_gender = %s, Cust_dob = %s
                WHERE Username = %s
            """, (form_data['fname'], form_data['lname'], form_data['city'], form_data['district'],
                  form_data['pin'], form_data['street'], form_data['phone'], form_data['gender'],
                  form_data['dob'], session['username']))
            db.commit()
            flash('Profile updated successfully!', 'success')
        except Exception as e:
            flash(f'Error updating profile: {str(e)}', 'error')
            db.rollback()
        finally:
            cursor.close()
            db.close()
        
        return redirect(url_for('profile'))
    
    return redirect(url_for('profile'))

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if not is_logged_in():
        flash('Please login to change your password', 'danger')
        return redirect(url_for('loginpage'))
    
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Password validations
        errors = {}
        if not old_password or not new_password or not confirm_password:
            errors['password'] = "All password fields are required."
        elif new_password != confirm_password:
            errors['password'] = "New password and confirm password do not match."
        elif not (8 <= len(new_password) <= 10):
            errors['password'] = "New password must be between 8 and 10 characters."
        elif not re.search(r"[A-Z]", new_password):
            errors['password'] = "New password must contain at least one uppercase letter."
        elif not re.search(r"[a-z]", new_password):
            errors['password'] = "New password must contain at least one lowercase letter."
        elif not re.search(r"[0-9]", new_password):
            errors['password'] = "New password must contain at least one number."
        elif not re.search(r"[!@#]", new_password):
            errors['password'] = "New password must contain at least one special character (!, @, or #)."
        
        # Verify old password
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("SELECT Login_password FROM tbl_login WHERE Username = %s", (session['username'],))
        result = cursor.fetchone()
        
        if not result or result['Login_password'] != old_password:
            errors['old_password'] = 'Incorrect old password'
        
        if errors:
            for field, error in errors.items():
                flash(f"{field}: {error}", "error")
            cursor.close()
            db.close()
            return redirect(url_for('profile'))
        
        # Update password
        try:
            cursor.execute("UPDATE tbl_login SET Login_password = %s WHERE Username = %s", 
                          (new_password, session['username']))
            db.commit()
            flash('Password changed successfully!', 'success')
        except Exception as e:
            flash(f'Error changing password: {str(e)}', 'error')
            db.rollback()
        finally:
            cursor.close()
            db.close()
        
        return redirect(url_for('profile'))
    
    return redirect(url_for('profile'))

#Staff Profile view and edit
@app.route('/staff_profile', methods=['GET'])
def staff_profile():
    if not is_logged_in():
        flash('Please login to view your profile', 'danger')
        return redirect(url_for('loginpage'))
    
    db = get_db_connection()
    cursor = db.cursor()
    
    # Fetch staff details
    cursor.execute("""
        SELECT Staff_fname, Staff_lname, Staff_city, Staff_dist, Staff_pin, 
               Staff_street, Staff_phone, Staff_gender, Staff_dob, Staff_join, Username
        FROM tbl_staff 
        WHERE Username = %s
    """, (session['username'],))
    staff = cursor.fetchone()
    
    cursor.close()
    db.close()
    
    if not staff:
        flash('Staff profile not found', 'danger')
        return redirect(url_for('home'))
    
    return render_template('staff_profile.html', staff=staff)

@app.route('/edit_staff_profile', methods=['GET', 'POST'])
def edit_staff_profile():
    if not is_logged_in():
        flash('Please login to edit your profile', 'danger')
        return redirect(url_for('loginpage'))
    
    if request.method == 'POST':
        # Fetch current staff data
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("""
            SELECT Staff_id, Staff_phone 
            FROM tbl_staff 
            WHERE Username = %s
        """, (session['username'],))
        current_data = cursor.fetchone()
        cursor.close()
        db.close()
        
        if not current_data:
            flash('Staff profile not found', 'danger')
            return redirect(url_for('staff_profile'))
        
        staff_id = current_data['Staff_id']
        current_phone = current_data['Staff_phone']

        form_data = {
            'fname': request.form.get('fname'),
            'lname': request.form.get('lname'),
            'city': request.form.get('city'),
            'district': request.form.get('district'),
            'pin': request.form.get('pin'),
            'street': request.form.get('street'),
            'phone': request.form.get('phone'),
            'gender': request.form.get('gender'),
            'dob': request.form.get('dob')
        }
        
        from staff_signup import validate_user_input

        # Validate with current phone and cust_id, remove security_answer from validation
        errors = {k: v for k, v in validate_user_input(form_data, current_phone=current_phone, staff_id=staff_id).items() 
                  if k != 'security_answer'}
        
        if errors:
            for field, error in errors.items():
                flash(f"{field}: {error}", "error")
            return redirect(url_for('staff_profile'))
        
        # Update profile
        db = get_db_connection()
        cursor = db.cursor()
        try:
            cursor.execute("""
                UPDATE tbl_staff 
                SET Staff_fname = %s, Staff_lname = %s, Staff_city = %s, Staff_dist = %s, 
                    Staff_pin = %s, Staff_street = %s, Staff_phone = %s, Staff_gender = %s, Staff_dob = %s
                WHERE Username = %s
            """, (form_data['fname'], form_data['lname'], form_data['city'], form_data['district'],
                  form_data['pin'], form_data['street'], form_data['phone'], form_data['gender'],
                  form_data['dob'], session['username']))
            db.commit()
            flash('Profile updated successfully!', 'success')
        except Exception as e:
            flash(f'Error updating profile: {str(e)}', 'error')
            db.rollback()
        finally:
            cursor.close()
            db.close()
        
        return redirect(url_for('staff_profile'))
    
    return redirect(url_for('staff_profile'))

@app.route('/change_staff_password', methods=['GET', 'POST'])
def change_staff_password():
    if not is_logged_in():
        flash('Please login to change your password', 'danger')
        return redirect(url_for('loginpage'))
    
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Password validations
        errors = {}
        if not old_password or not new_password or not confirm_password:
            errors['password'] = "All password fields are required."
        elif new_password != confirm_password:
            errors['password'] = "New password and confirm password do not match."
        elif not (8 <= len(new_password) <= 10):
            errors['password'] = "New password must be between 8 and 10 characters."
        elif not re.search(r"[A-Z]", new_password):
            errors['password'] = "New password must contain at least one uppercase letter."
        elif not re.search(r"[a-z]", new_password):
            errors['password'] = "New password must contain at least one lowercase letter."
        elif not re.search(r"[0-9]", new_password):
            errors['password'] = "New password must contain at least one number."
        elif not re.search(r"[!@#]", new_password):
            errors['password'] = "New password must contain at least one special character (!, @, or #)."
        
        # Verify old password
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("SELECT Login_password FROM tbl_login WHERE Username = %s", (session['username'],))
        result = cursor.fetchone()
        
        if not result or result['Login_password'] != old_password:
            errors['old_password'] = 'Incorrect old password'
        
        if errors:
            for field, error in errors.items():
                flash(f"{field}: {error}", "error")
            cursor.close()
            db.close()
            return redirect(url_for('staff_profile'))
        
        # Update password
        try:
            cursor.execute("UPDATE tbl_login SET Login_password = %s WHERE Username = %s", 
                          (new_password, session['username']))
            db.commit()
            flash('Password changed successfully!', 'success')
        except Exception as e:
            flash(f'Error changing password: {str(e)}', 'error')
            db.rollback()
        finally:
            cursor.close()
            db.close()
        
        return redirect(url_for('staff_profile'))
    
    return redirect(url_for('staff_profile'))

#Courier Profile view and edit
@app.route('/courier_profile', methods=['GET'])
def courier_profile():
    if not is_logged_in():
        flash('Please login to view your profile', 'danger')
        return redirect(url_for('loginpage'))
    
    db = get_db_connection()
    cursor = db.cursor()
    
    # Fetch courier details
    cursor.execute("""
        SELECT C_name, C_cmpy_email, C_city, C_dist, C_pin, 
               C_street, C_phone, C_join, Username
        FROM tbl_courier 
        WHERE Username = %s
    """, (session['username'],))
    courier = cursor.fetchone()
    
    cursor.close()
    db.close()
    
    if not courier:
        flash('Courier profile not found', 'danger')
        return redirect(url_for('home'))
    
    return render_template('courier_profile.html', courier=courier)

@app.route('/edit_courier_profile', methods=['GET', 'POST'])
def edit_courier_profile():
    if not is_logged_in():
        flash('Please login to edit your profile', 'danger')
        return redirect(url_for('loginpage'))
    
    if request.method == 'POST':
        # Fetch current courier data
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("""
            SELECT Courier_id, C_phone 
            FROM tbl_courier 
            WHERE Username = %s
        """, (session['username'],))
        current_data = cursor.fetchone()
        cursor.close()
        db.close()
        
        if not current_data:
            flash('Courier profile not found', 'danger')
            return redirect(url_for('courier_profile'))
        
        courier_id = current_data['Courier_id']
        current_phone = current_data['C_phone']

        form_data = {
            'c_name': request.form.get('c_name'),
            'c_cmpy_email': request.form.get('c_cmpy_email'),
            'c_city': request.form.get('c_city'),
            'c_dist': request.form.get('c_dist'),
            'c_pin': request.form.get('c_pin'),
            'c_street': request.form.get('c_street'),
            'c_phone': request.form.get('c_phone')
        }
        
        from courier_management import validate_user_input

        # Validate with current phone and cust_id, remove security_answer from validation
        errors = {k: v for k, v in validate_user_input(form_data, current_phone=current_phone, courier_id=courier_id).items() 
                  if k != 'security_answer'}
        
        if errors:
            for field, error in errors.items():
                flash(f"{field}: {error}", "error")
            return redirect(url_for('courier_profile'))
        
        # Update profile
        db = get_db_connection()
        cursor = db.cursor()
        try:
            cursor.execute("""
                UPDATE tbl_courier 
                SET C_name = %s, C_cmpy_email = %s, C_city = %s, C_dist = %s, 
                    C_pin = %s, C_street = %s, C_phone = %s
                WHERE Username = %s
            """, (form_data['c_name'], form_data['c_cmpy_email'], form_data['c_city'], form_data['c_dist'],
                  form_data['c_pin'], form_data['c_street'], form_data['c_phone'], session['username']))
            db.commit()
            flash('Profile updated successfully!', 'success')
        except Exception as e:
            flash(f'Error updating profile: {str(e)}', 'error')
            db.rollback()
        finally:
            cursor.close()
            db.close()
        
        return redirect(url_for('courier_profile'))
    
    return redirect(url_for('courier_profile'))

@app.route('/change_courier_password', methods=['GET', 'POST'])
def change_courier_password():
    if not is_logged_in():
        flash('Please login to change your password', 'danger')
        return redirect(url_for('loginpage'))
    
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Password validations
        errors = {}
        if not old_password or not new_password or not confirm_password:
            errors['password'] = "All password fields are required."
        elif new_password != confirm_password:
            errors['password'] = "New password and confirm password do not match."
        elif not (8 <= len(new_password) <= 10):
            errors['password'] = "New password must be between 8 and 10 characters."
        elif not re.search(r"[A-Z]", new_password):
            errors['password'] = "New password must contain at least one uppercase letter."
        elif not re.search(r"[a-z]", new_password):
            errors['password'] = "New password must contain at least one lowercase letter."
        elif not re.search(r"[0-9]", new_password):
            errors['password'] = "New password must contain at least one number."
        elif not re.search(r"[!@#]", new_password):
            errors['password'] = "New password must contain at least one special character (!, @, or #)."
        
        # Verify old password
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("SELECT Login_password FROM tbl_login WHERE Username = %s", (session['username'],))
        result = cursor.fetchone()
        
        if not result or result['Login_password'] != old_password:
            errors['old_password'] = 'Incorrect old password'
        
        if errors:
            for field, error in errors.items():
                flash(f"{field}: {error}", "error")
            cursor.close()
            db.close()
            return redirect(url_for('courier_profile'))
        
        # Update password
        try:
            cursor.execute("UPDATE tbl_login SET Login_password = %s WHERE Username = %s", 
                          (new_password, session['username']))
            db.commit()
            flash('Password changed successfully!', 'success')
        except Exception as e:
            flash(f'Error changing password: {str(e)}', 'error')
            db.rollback()
        finally:
            cursor.close()
            db.close()
        
        return redirect(url_for('courier_profile'))
    
    return redirect(url_for('courier_profile'))

#Courier Assignment in user(admin) panel
@app.route('/courier_assignments', methods=['GET', 'POST'])
def courier_assignments():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Fetch usernames of active couriers (Login_type = 'Courier' and Login_status = 1)
            cursor.execute("""
                SELECT c.Courier_id, l.Username 
                FROM tbl_courier c
                JOIN tbl_login l ON c.Username = l.Username
                WHERE c.Courier_status = 1 AND l.Login_type = 'Courier' AND l.Login_status = 1
            """)
            couriers = cursor.fetchall()

            selected_courier_id = None
            assignments = []
            if request.method == 'POST':
                selected_courier_id = request.form.get('courier_id')
                if selected_courier_id:
                    # Fetch assignments for the selected courier
                    cursor.execute("""
                        SELECT 
                            ca.Cassign_id,
                            ca.Cart_master_id,
                            ca.Cassign_date,
                            ca.Max_date_arrival,
                            ca.Cassign_status,
                            i.Item_name,
                            cc.Cart_qty,
                            cc.Cart_price,
                            pc.Pur_unit_weight
                        FROM tbl_cassign ca
                        JOIN tbl_cart_master cm ON ca.Cart_master_id = cm.Cart_master_id
                        JOIN tbl_cart_child cc ON cm.Cart_master_id = cc.Cart_master_id
                        JOIN tbl_item i ON cc.Item_id = i.Item_id
                        JOIN tbl_purchase_child pc ON i.Item_id = pc.Item_id AND pc.Sell_price = cc.Cart_unit_price
                        WHERE ca.Courier_id = %s
                        ORDER BY ca.Cassign_date DESC
                    """, (selected_courier_id,))
                    assignments = cursor.fetchall()

    finally:
        connection.close()

    return render_template('courier_assignments.html', couriers=couriers, assignments=assignments, selected_courier_id=selected_courier_id)


if __name__ == "__main__":
    app.run(debug=True, use_reloader=True)
        