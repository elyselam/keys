import sqlite3

# Create a test database
conn = sqlite3.connect('sqlite3_db.db')
cursor = conn.cursor()

# Create a test table
cursor.execute('''
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

# Insert a test row
cursor.execute('''
    INSERT INTO event (title, description, date, time, day_night, fee) 
    VALUES (?, ?, ?, ?, ?, ?)
''', ('Test Event', 'Test Description', '2024-03-20', '14:00', 'day', 10.00))

# Save the changes
conn.commit()

# Query the data
cursor.execute('SELECT * FROM event')
print("Data in database:", cursor.fetchall())

# Close the connection
conn.close()

print("SQLite test completed successfully!") 