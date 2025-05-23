from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from pathlib import Path
from functools import wraps
import logging
import os
import time as time_module
from werkzeug.utils import secure_filename

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key

# File upload configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'heic'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Database configuration
DATABASE = 'sqlite3_db.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db_path = Path(DATABASE)
    if not db_path.exists():
        logger.info("Creating new database...")
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        # Create users table
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                is_promoter BOOLEAN DEFAULT 0
            )
        ''')
        # Create events table
        c.execute('''
            CREATE TABLE IF NOT EXISTS event (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                location TEXT NOT NULL,
                description TEXT,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                day_night TEXT NOT NULL,
                fee REAL,
                image_path TEXT
            )
        ''')
        conn.commit()
        conn.close()
        logger.info("Database created successfully")

# Initialize database before each request if it doesn't exist
@app.before_request
def before_request():
    if not Path(DATABASE).exists():
        init_db()
        logger.info("Database initialized on first request")

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Promoter required decorator
def promoter_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        conn = get_db()
        user = conn.execute('SELECT is_promoter FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        conn.close()
        if not user or not user['is_promoter']:
            flash('Access denied. Promoter privileges required.')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    conn = get_db()
    events = conn.execute('SELECT * FROM event ORDER BY date, time').fetchall()
    conn.close()
    return render_template('index.html', events=events)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
        
    email = request.form['email']
    password = request.form['password']
    
    # Check if email is mainkeysmiami@gmail.com
    is_promoter = email == 'mainkeysmiami@gmail.com'
    logger.info(f"Registering user: {email}, is_promoter: {is_promoter}")
    
    conn = get_db()
    try:
        conn.execute('INSERT INTO users (email, password, is_promoter) VALUES (?, ?, ?)',
                    (email, password, is_promoter))
        conn.commit()
        flash('Registration successful! Please login.')
        logger.info(f"User {email} registered successfully")
    except sqlite3.IntegrityError:
        flash('Email already registered.')
        logger.warning(f"Registration failed: Email {email} already exists")
    finally:
        conn.close()
    
    return redirect(url_for('login'))

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    email = request.form['email']
    password = request.form['password']
    
    logger.info(f"Login attempt for: {email}")
    
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE email = ? AND password = ?',
                       (email, password)).fetchone()
    conn.close()
    
    if user:
        session['user_id'] = user['id']
        session['is_promoter'] = user['is_promoter']
        logger.info(f"User {email} logged in successfully, is_promoter: {user['is_promoter']}")
        if user['is_promoter']:
            return redirect(url_for('promoter'))
        return redirect(url_for('index'))
    
    flash('Invalid email or password')
    logger.warning(f"Login failed for: {email}")
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/promoter')
@promoter_required
def promoter():
    logger.info(f"Accessing promoter page, user_id: {session.get('user_id')}")
    conn = get_db()
    events = conn.execute('SELECT * FROM event ORDER BY date, time').fetchall()
    conn.close()
    return render_template('promoter.html', events=events)

@app.route('/promoter/add', methods=['POST'])
@promoter_required
def add():
    logger.info(f"Adding new event, user_id: {session.get('user_id')}")
    title = request.form['title']
    location = request.form['location']
    description = request.form['description']
    date = request.form['date']
    time = request.form['time']
    day_night = request.form['day_night']
    fee = request.form['fee'].replace(',', '') if request.form['fee'] else None
    
    # Handle image upload
    image_path = None
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Add timestamp to filename to make it unique
            filename = f"{int(time_module.time())}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            image_path = os.path.join('uploads', filename)
            logger.info(f"Image saved: {image_path}")
    
    logger.info(f"Event details - Title: {title}, Location: {location}, Date: {date}, Time: {time}, Fee: {fee}")
    
    conn = get_db()
    try:
        conn.execute('''
            INSERT INTO event (title, location, description, date, time, day_night, fee, image_path) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, location, description, date, time, day_night, fee, image_path))
        conn.commit()
        logger.info("Event added successfully")
    except Exception as e:
        logger.error(f"Error adding event: {str(e)}")
        flash('Error adding event')
    finally:
        conn.close()
    return redirect(url_for('promoter'))

@app.route('/promoter/delete/<int:event_id>', methods=['POST'])
def delete(event_id):
    conn = get_db()
    # Get the event's image path before deleting
    event = conn.execute('SELECT image_path FROM event WHERE id = ?', (event_id,)).fetchone()
    if event and event['image_path']:
        delete_image_file(event['image_path'])
    
    conn.execute('DELETE FROM event WHERE id = ?', (event_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('promoter'))

@app.route('/promoter/edit/<int:event_id>', methods=['GET'])
def edit(event_id):
    conn = get_db()
    event = conn.execute('SELECT * FROM event WHERE id = ?', (event_id,)).fetchone()
    conn.close()
    if event is None:
        return redirect(url_for('promoter'))
    return render_template('edit.html', event=event)

def delete_image_file(image_path):
    if image_path:
        try:
            full_path = os.path.join(app.static_folder, image_path)
            if os.path.exists(full_path):
                os.remove(full_path)
                logger.info(f"Deleted image file: {full_path}")
        except Exception as e:
            logger.error(f"Error deleting image file: {str(e)}")

@app.route('/promoter/update/<int:event_id>', methods=['POST'])
def update(event_id):
    title = request.form['title']
    location = request.form['location']
    description = request.form['description']
    date = request.form['date']
    time = request.form['time']
    day_night = request.form['day_night']
    fee = request.form['fee'].replace(',', '') if request.form['fee'] else None
    
    # Get current event data
    conn = get_db()
    current_event = conn.execute('SELECT image_path FROM event WHERE id = ?', (event_id,)).fetchone()
    current_image_path = current_event['image_path'] if current_event else None
    
    # Handle image upload or removal
    image_path = current_image_path
    if 'remove_image' in request.form:
        # Delete the current image file
        delete_image_file(current_image_path)
        image_path = None
    elif 'image' in request.files:
        file = request.files['image']
        if file and file.filename and allowed_file(file.filename):
            # Delete the current image file if it exists
            delete_image_file(current_image_path)
            
            # Save the new image
            filename = secure_filename(file.filename)
            filename = f"{int(time_module.time())}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            image_path = os.path.join('uploads', filename)
            logger.info(f"New image saved: {image_path}")
    
    # Update the event
    conn.execute('''
        UPDATE event 
        SET title = ?, location = ?, description = ?, date = ?, time = ?, day_night = ?, fee = ?, image_path = ?
        WHERE id = ?
    ''', (title, location, description, date, time, day_night, fee, image_path, event_id))
    conn.commit()
    conn.close()
    return redirect(url_for('promoter'))

# @app.route('/about')
# def about():
#     return 'About Page'

if __name__ == '__main__':
    app.run(debug=True, port=5001)