from flask import Flask, render_template_string, request, redirect
from flask_sqlalchemy import SQLAlchemy

# Flask app setup
app = Flask(__name__)

# Configure the SQLAlchemy database URI
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/testdb'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db = SQLAlchemy(app)

# Define the User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    phone = db.Column(db.String(10), nullable=False)

# HTML form as a template
html_form = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Python MySQL Form</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f4f4f4;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        .form-container {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        }
        input[type="text"], input[type="number"] {
            width: 100%;
            padding: 10px;
            margin: 10px 0;
            border: 1px solid #ccc;
            border-radius: 5px;
        }
        button {
            background: #007bff;
            color: white;
            border: none;
            padding: 10px 15px;
            cursor: pointer;
            border-radius: 5px;
        }
        button:hover {
            background: #0056b3;
        }
    </style>
</head>
<body>
    <div class="form-container">
        <h2>Enter Your Details</h2>
        <form method="POST" action="/submit">
            <label for="name">Name:</label>
            <input type="text" id="name" name="name" required>
            
            <label for="age">Age:</label>
            <input type="number" id="age" name="age" required>
            
            <label for="phone">Phone Number:</label>
            <input type="text" id="phone" name="phone" maxlength="10" required>
            
            <button type="submit">Submit</button>
        </form>
    </div>
</body>
</html>
"""

# Flask route for the form
@app.route('/')
def index():
    return render_template_string(html_form)

# Flask route for form submission
@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    age = request.form['age']
    phone = request.form['phone']

    # Insert data into the database using SQLAlchemy
    try:
        new_user = User(name=name, age=age, phone=phone)
        db.session.add(new_user)
        db.session.commit()
        return "<h1>Data submitted successfully!</h1><a href='/'>Go Back</a>"
    except Exception as e:
        db.session.rollback()
        return f"<h1>Error: {e}</h1><a href='/'>Go Back</a>"

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)