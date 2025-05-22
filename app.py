from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from pathlib import Path
from functools import wraps
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key

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
                description TEXT,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                day_night TEXT NOT NULL,
                fee REAL
            )
        ''')
        conn.commit()
        conn.close()
        logger.info("Database created successfully")

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
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register():
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
    return render_template('index.html', events=events)

@app.route('/promoter/add', methods=['POST'])
@promoter_required
def add():
    logger.info(f"Adding new event, user_id: {session.get('user_id')}")
    title = request.form['title']
    description = request.form['description']
    date = request.form['date']
    time = request.form['time']
    day_night = request.form['day_night']
    fee = request.form['fee'].replace(',', '') if request.form['fee'] else None
    
    logger.info(f"Event details - Title: {title}, Date: {date}, Time: {time}, Fee: {fee}")
    
    conn = get_db()
    try:
        conn.execute('''
            INSERT INTO event (title, description, date, time, day_night, fee) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (title, description, date, time, day_night, fee))
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

@app.route('/promoter/update/<int:event_id>', methods=['POST'])
def update(event_id):
    title = request.form['title']
    description = request.form['description']
    date = request.form['date']
    time = request.form['time']
    day_night = request.form['day_night']
    fee = request.form['fee'].replace(',', '') if request.form['fee'] else None
    
    conn = get_db()
    conn.execute('''
        UPDATE event 
        SET title = ?, description = ?, date = ?, time = ?, day_night = ?, fee = ?
        WHERE id = ?
    ''', (title, description, date, time, day_night, fee, event_id))
    conn.commit()
    conn.close()
    return redirect(url_for('promoter'))

# @app.route('/about')
# def about():
#     return 'About Page'

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5001)