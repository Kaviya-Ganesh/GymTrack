from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from mysql.connector import Error
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = "mysecretkey123"  # Change to a secure, unique key

# Database connection function
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host="127.0.0.1",
            user="root",
            password="root123",  # Replace with your actual password
            database="thrift_store",
            port=3307
        )
        logger.debug("Database connection established")
        return connection
    except Error as e:
        logger.error(f"Database connection error: {e}")
        flash(f"Database connection failed: {e}", "error")
        return None

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        logger.debug(f"Attempting to login with email: {email}")
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.callproc('LoginUser', [email, password, 0, 0])
                conn.commit()  # Make sure to commit after calling the stored procedure

                # Fetch the output parameters
                cursor.execute("SELECT @user_id, @success;")
                result = cursor.fetchone()
                if result:
                    user_id, success = result
                    logger.debug(f"Login result: user_id={user_id}, success={success}")
                    if success:
                        session['user_id'] = user_id
                        session['email'] = email
                        flash('Login successful!', 'success')
                        return redirect(url_for('dashboard'))
                    else:
                        flash('Invalid credentials!', 'error')
            except Error as e:
                flash(f'Login failed: {e}', 'error')
                logger.error(f"Login error: {e}")
            finally:
                cursor.close()
                conn.close()
        else:
            flash("Database unavailable. Please try again later.", "error")
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.callproc('RegisterUser', [email, password])
                conn.commit()
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))
            except Error as e:
                flash(f'Registration failed: {e}', 'error')
                logger.error(f"Signup error: {e}")
            finally:
                cursor.close()
                conn.close()
        else:
            flash("Database unavailable. Please try again later.", 'error')
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('email', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in first!', 'error')
        return redirect(url_for('login'))
    
    logger.debug(f"User ID in session: {session['user_id']}")
    conn = get_db_connection()
    items = []
    if conn:
        cursor = conn.cursor()
        try:
            cursor.callproc('GetAllAvailableItems', [])
            items = cursor.fetchall()
        except Error as e:
            flash(f'Error fetching items: {e}', 'error')
            logger.error(f"Dashboard error: {e}")
        finally:
            cursor.close()
            conn.close()
    else:
        flash("Database unavailable. Cannot load items.", 'error')
    return render_template('dashboard.html', items=items, email=session.get('email'))

@app.route('/list_item', methods=['GET', 'POST'])
def list_item():
    if 'user_id' not in session:
        flash('Please log in first!', 'error')
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        description = request.form['description']
        price = float(request.form['price'])
        condition = request.form['condition']
        image_url = request.form.get('image_url', '')
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.callproc('AddItem', [session['user_id'], category, name, description, price, condition, image_url])
                conn.commit()
                flash('Item listed successfully!', 'success')
            except Error as e:
                flash(f'Failed to list item: {e}', 'error')
                logger.error(f"List item error: {e}")
            finally:
                cursor.close()
                conn.close()
        else:
            flash("Database unavailable. Cannot list item.", 'error')
    return render_template('list_item.html')

@app.route('/buy', methods=['GET', 'POST'])
def buy():
    if 'user_id' not in session:
        flash('Please log in first!', 'error')
        return redirect(url_for('login'))
    conn = get_db_connection()
    items = []
    if conn:
        cursor = conn.cursor()
        try:
            if request.method == 'POST' and 'category' in request.form:
                category = request.form['category']
                cursor.callproc('GetItemsByCategory', [category])
            else:
                cursor.callproc('GetAllAvailableItems', [])
            items = cursor.fetchall()
        except Error as e:
            flash(f'Error fetching items: {e}', 'error')
            logger.error(f"Buy page error: {e}")
        finally:
            cursor.close()
            conn.close()
    else:
        flash("Database unavailable. Cannot load items.", 'error')
    return render_template('buy.html', items=items)

@app.route('/buy_item/<int:item_id>', methods=['POST'])
def buy_item(item_id):
    if 'user_id' not in session:
        flash('Please log in first!', 'error')
        return redirect(url_for('login'))
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.callproc('BuyItem', [session['user_id'], item_id])
            conn.commit()
            flash('Item purchased successfully!', 'success')
        except Error as e:
            flash(f'Purchase failed: {e}', 'error')
            logger.error(f"Buy item error: {e}")
        finally:
            cursor.close()
            conn.close()
    else:
        flash("Database unavailable. Cannot process purchase.", 'error')
    return redirect(url_for('buy'))

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)