from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from pathlib import Path

app = Flask(__name__)

# Database configuration
DATABASE = 'sqlite3_db.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db_path = Path(DATABASE)
    if not db_path.exists():
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
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

@app.route('/')
def index():
    conn = get_db()
    events = conn.execute('SELECT * FROM event ORDER BY date, time').fetchall()
    conn.close()
    return render_template('index.html', events=events)

@app.route('/add', methods=['POST'])
def add():
    title = request.form['title']
    description = request.form['description']
    date = request.form['date']
    time = request.form['time']
    day_night = request.form['day_night']
    fee = request.form['fee']
    
    conn = get_db()
    conn.execute('''
        INSERT INTO event (title, description, date, time, day_night, fee) 
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (title, description, date, time, day_night, fee))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/delete/<int:event_id>', methods=['POST'])
def delete(event_id):
    conn = get_db()
    conn.execute('DELETE FROM event WHERE id = ?', (event_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# @app.route('/about')
# def about():
#     return 'About Page'

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5001)