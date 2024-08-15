import sqlite3

def create_database():
    conn = sqlite3.connect('tojsokhtmon.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS residential_complex (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT,
            finishing TEXT,
            improvement TEXT,
            smart_home TEXT,
            architecture TEXT,
            infrastructure TEXT,
            ecology TEXT,
            description TEXT,
            photo BLOB
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS apartments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            photo BLOB,
            rooms INTEGER,
            description TEXT,
            price REAL,
            residential_complex_id INTEGER,
            FOREIGN KEY (residential_complex_id) REFERENCES residential_complex(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS promotions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            photo BLOB,
            description TEXT
        )
        ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faq (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL
        )
        ''')
    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_database()