<h1 align="center">🌶️ Spice Bazaar – Online Spices Store</h1>
<p align="center">A complete e-commerce platform for purchasing premium-quality spices with seamless management of products, customers, staff, vendors, and delivery operations.</p>

<hr/>

<h2>📌 Overview</h2>
<p>
Spice Bazaar is a fully functional online spices store designed to provide customers with a smooth and intuitive shopping experience. 
The platform enables users to explore spices through categories and subcategories, add items to the cart, complete payments, and track deliveries. 
It also features efficient tools for administrators, staff, vendors, and couriers to manage backend operations, ensuring a streamlined and well-organized system.
</p>

<hr/>

<h2>🎯 Key Features</h2>
<ul>
  <li>Role-based access control (Admin, Staff, Customer, Courier)</li>
  <li>Structured product browsing with filters</li>
  <li>Secure checkout and payment process</li>
  <li>Real-time delivery status updates</li>
  <li>Vendor and purchase tracking for smooth inventory management</li>
  <li>Efficient cart management for customers</li>
</ul>



<hr/>

<h2>👥 User Roles</h2>

<h3>1️⃣ Administrator</h3>
<ul>
  <li>Full control over all modules.</li>
  <li>Add/Edit/View categories, subcategories, products, couriers, vendors, and staff.</li>
  <li>Activate or deactivate customer accounts.</li>
  <li>Manage purchases and monitor system activities.</li>
</ul>

<h3>2️⃣ Staff</h3>
<ul>
  <li>Add/Edit/View categories, subcategories, products, and vendor details.</li>
  <li>Handle purchase information from vendors.</li>
  <li>Assist admin by managing operational tasks.</li>
</ul>

<h3>3️⃣ Customer</h3>
<ul>
  <li>Browse products based on category/subcategory.</li>
  <li>Registered users can add to cart, edit cart, and make payments.</li>
  <li>Track orders after purchase.</li>
  <li>Unregistered users may view products but cannot purchase.</li>
</ul>

<h3>4️⃣ Courier</h3>
<ul>
  <li>View assigned orders.</li>
  <li>Update delivery status (Out for Delivery / Delivered).</li>
  <li>System assigns couriers automatically upon successful payment.</li>
</ul>

<hr/>

<h2>📦 System Modules</h2>

<h3>1. Staff Management</h3>
<p>Manage staff profiles including creation, editing, and updates.</p>

<h3>2. Customer Registration</h3>
<p>Allows users to create accounts, manage their profiles, and track orders.</p>

<h3>3. Vendor Management</h3>
<p>Admin/Staff can add, edit, and track vendor information for product procurement.</p>

<h3>4. Courier Management</h3>
<p>Manage couriers, assign deliveries, and track order statuses.</p>

<h3>5. Product Management</h3>
<ul>
  <li><b>5.1 Category Management:</b> Organize products into high-level groups.</li>
  <li><b>5.2 Subcategory Management:</b> Further classification into specific groups (e.g., Whole Spices, Ground Spices).</li>
  <li><b>5.3 Item Management:</b> Add/Edit/Delete individual spice items with details and images.</li>
</ul>

<h3>6. Purchase Management</h3>
<p>Handles procurement from vendors and updates inventory levels.</p>

<h3>7. Cart Management</h3>
<p>Enables customers to add, edit, or remove items before checkout, calculating totals automatically.</p>

<h3>8. Sales Management</h3>
<ul>
  <li><b>8.1 Payment Management:</b> Secure processing of online payments.</li>
  <li><b>8.2 Courier Assignment Management:</b> Automatically assigns couriers to paid orders.</li>
  <li><b>8.3 Delivery Management:</b> Tracks order delivery from pickup to customer location.</li>
</ul>

<hr/>

<h2>Technologies Used</h2>
<ul>
  <li>Python </li>
  <li>HTML, CSS, JavaScript</li>
  <li>MySQL Database (via XAMPP)</li>
  <li><strong>Note:</strong> This project requires <strong>XAMPP</strong> to run. 
      The Apache server and MySQL services must be active for the system to work.</li>
</ul>

<hr/>

<h2>📂 Project Structure</h2>
<pre>
Spice-Bazaar/
│
├── app.py
├── loginpage.py
├── services.py
│
├── staff_management.py
├── customer_management.py
├── vendor_management.py
├── courier_management.py
├── category_management.py
├── subcategory_management.py
├── item_management.py
├── purchase_management.py
│
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│
├── templates/
│   ├── *.html (pages)
│   └── partials/ (header, footer, head)
</pre>


<hr/>

<h2>🚀 Getting Started</h2>
<ol>
  <li>Clone the repository:</li>
  <pre><code>git clone https://github.com/treesajose-dev/Spice-Bazaar-Online-Spices-Store.git</code></pre>
  <li>Configure the database and import required SQL files</li>
  <li>Update database connection credentials</li>
  <li>Run the project on a server (XAMPP/WAMP/LAMP)</li>
  <pre><code>run flask</code></pre>
</ol>

<hr/>

<h2>💡 Future Enhancements</h2>
<ul>
  <li>Advanced analytics dashboard</li>
  <li>Advanced product comparison</li>
  <li>AI enabled recipe generator</li>
</ul>

<hr/>

<h2>📞 Support</h2>
<p>For queries or support, feel free to contact the project maintainer.</p>

<h3 align="center">🌶️ <b>Spice Bazaar ⭐ If you find this project helpful, consider giving it a star!</b> 🌶️</h3>
