from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
import logging
import os
import time as time_module
from werkzeug.utils import secure_filename
from datetime import datetime
import db

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

# Initialize database before each request if it doesn't exist
@app.before_request
def before_request():
    if not db.check_db_exists():
        db.init_db()
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
        user = db.get_user_by_id(session['user_id'])
        if not user or not user['is_promoter']:
            flash('Access denied. Promoter privileges required.')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    events = db.get_events_with_booking_status(session.get('user_id'))
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
    
    if db.create_user(email, password, is_promoter):
        flash('Registration successful! Please login.')
    else:
        flash('Email already registered.')
    
    return redirect(url_for('login'))

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    email = request.form['email']
    password = request.form['password']
    
    logger.info(f"Login attempt for: {email}")
    
    user = db.get_user_by_email(email)
    
    if user and user['password'] == password:
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
    events = db.get_all_events()
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
    
    if db.create_event(title, location, description, date, time, day_night, fee, image_path):
        flash('Event added successfully')
    else:
        flash('Error adding event')
    
    return redirect(url_for('promoter'))

@app.route('/promoter/delete/<int:event_id>', methods=['POST'])
def delete(event_id):
    event = db.get_event_by_id(event_id)
    if event and event['image_path']:
        delete_image_file(event['image_path'])
    
    if db.delete_event(event_id):
        flash('Event deleted successfully')
    else:
        flash('Error deleting event')
    
    return redirect(url_for('promoter'))

@app.route('/promoter/edit/<int:event_id>', methods=['GET'])
def edit(event_id):
    event = db.get_event_by_id(event_id)
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
    current_event = db.get_event_by_id(event_id)
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
    
    if db.update_event(event_id, title, location, description, date, time, day_night, fee, image_path):
        flash('Event updated successfully')
    else:
        flash('Error updating event')
    
    return redirect(url_for('promoter'))

@app.route('/book/<int:event_id>', methods=['POST'])
@login_required
def book_event(event_id):
    logger.info(f"Booking event {event_id} for user {session.get('user_id')}")
    
    # Get current date for booking
    booking_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    success, message = db.create_booking(session['user_id'], event_id, booking_date)
    flash(message)
    
    return redirect(url_for('index'))

# @app.route('/about')
# def about():
#     return 'About Page'

if __name__ == '__main__':
    app.run(debug=True, port=5001)