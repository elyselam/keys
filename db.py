import sqlite3
from pathlib import Path
import logging

# Set up logging
logger = logging.getLogger(__name__)

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
        # Create bookings table
        c.execute('''
            CREATE TABLE IF NOT EXISTS booking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                event_id INTEGER NOT NULL,
                booking_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'confirmed',
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (event_id) REFERENCES event (id)
            )
        ''')
        conn.commit()
        conn.close()
        logger.info("Database created successfully")

def check_db_exists():
    return Path(DATABASE).exists()

def get_user_by_email(email):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return user

def create_user(email, password, is_promoter):
    conn = get_db()
    try:
        conn.execute('INSERT INTO users (email, password, is_promoter) VALUES (?, ?, ?)',
                    (email, password, is_promoter))
        conn.commit()
        logger.info(f"User {email} registered successfully")
        return True
    except sqlite3.IntegrityError:
        logger.warning(f"Registration failed: Email {email} already exists")
        return False
    finally:
        conn.close()

def get_all_events():
    conn = get_db()
    events = conn.execute('SELECT * FROM event ORDER BY date, time').fetchall()
    conn.close()
    return events

def get_events_with_booking_status(user_id):
    conn = get_db()
    events = conn.execute('''
        SELECT e.*, 
               CASE WHEN b.id IS NOT NULL THEN 1 ELSE 0 END as is_booked
        FROM event e
        LEFT JOIN booking b ON e.id = b.event_id AND b.user_id = ?
        ORDER BY e.date, e.time
    ''', (user_id,)).fetchall()
    conn.close()
    return events

def create_event(title, location, description, date, time, day_night, fee, image_path):
    conn = get_db()
    try:
        conn.execute('''
            INSERT INTO event (title, location, description, date, time, day_night, fee, image_path) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, location, description, date, time, day_night, fee, image_path))
        conn.commit()
        logger.info("Event added successfully")
        return True
    except Exception as e:
        logger.error(f"Error adding event: {str(e)}")
        return False
    finally:
        conn.close()

def get_event_by_id(event_id):
    conn = get_db()
    event = conn.execute('SELECT * FROM event WHERE id = ?', (event_id,)).fetchone()
    conn.close()
    return event

def update_event(event_id, title, location, description, date, time, day_night, fee, image_path):
    conn = get_db()
    try:
        conn.execute('''
            UPDATE event 
            SET title = ?, location = ?, description = ?, date = ?, time = ?, day_night = ?, fee = ?, image_path = ?
            WHERE id = ?
        ''', (title, location, description, date, time, day_night, fee, image_path, event_id))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error updating event: {str(e)}")
        return False
    finally:
        conn.close()

def delete_event(event_id):
    conn = get_db()
    try:
        conn.execute('DELETE FROM event WHERE id = ?', (event_id,))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error deleting event: {str(e)}")
        return False
    finally:
        conn.close()

def create_booking(user_id, event_id, booking_date):
    conn = get_db()
    try:
        # Check if user already has a booking for this event
        existing_booking = conn.execute(
            'SELECT id FROM booking WHERE user_id = ? AND event_id = ?',
            (user_id, event_id)
        ).fetchone()
        
        if existing_booking:
            return False, "You have already booked this event"
        
        # Create new booking
        conn.execute(
            'INSERT INTO booking (user_id, event_id, booking_date) VALUES (?, ?, ?)',
            (user_id, event_id, booking_date)
        )
        conn.commit()
        logger.info(f"Booking created for event {event_id}")
        return True, "Event booked successfully!"
    except Exception as e:
        logger.error(f"Error creating booking: {str(e)}")
        return False, "Error booking event"
    finally:
        conn.close() 