import sqlite3
import logging
from datetime import date


class Database:
    """
    Class to handle all database interactions.
    """

    def __init__(self, db_name='packages.db'):
        self.db_name = db_name
        self.create_packages_table()

    def create_packages_table(self):
        """
        Creates the packages table if it does not exist.
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL,
            payment REAL DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER,
            username TEXT,
            first_name TEXT,
            last_name TEXT
        )
        ''')
        conn.commit()
        conn.close()

    def barcode_exists(self, barcode: str) -> bool:
        """
        Checks if a barcode already exists in the database.
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM packages WHERE barcode = ?', (barcode,))
        result = cursor.fetchone()
        conn.close()
        return result is not None

    def save_package(self, barcode: str, status: str, payment: float = 0, user_data: dict = None):
        """
        Saves package information to the database.
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        try:
            cursor.execute('''
            INSERT INTO packages (barcode, status, payment, user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                barcode,
                status,
                payment,
                user_data.get('user_id'),
                user_data.get('username'),
                user_data.get('first_name'),
                user_data.get('last_name')
            ))
            conn.commit()
        except sqlite3.IntegrityError as e:
            logging.error(f"Failed to insert data: {e}")
        finally:
            conn.close()

    def get_today_data(self):
        """
        Retrieves all records from the database where the timestamp is from today.
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # Get today's date in YYYY-MM-DD format
        today = date.today().isoformat()

        cursor.execute('''
        SELECT * FROM packages
        WHERE DATE(timestamp) = ?
        ''', (today,))
        data = cursor.fetchall()
        conn.close()
        return data
