import sqlite3
from werkzeug.security import generate_password_hash

DB = 'finance.db'

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS customers (
                         customer_id INTEGER PRIMARY KEY, 
                         name TEXT, 
                         email TEXT UNIQUE, 
                         password TEXT, 
                         currency TEXT,
                         totp_secret TEXT,
                         is_2fa_enabled BOOL DEFAULT 0 );

            CREATE TABLE IF NOT EXISTS advisers (
                         adviser_id INTEGER PRIMARY KEY, 
                         name TEXT, 
                         email TEXT UNIQUE, 
                         password TEXT, 
                         currency TEXT, 
                         is_manager BOOL DEFAULT 0,
                         totp_secret TEXT,
                         is_2fa_enabled BOOL DEFAULT 0 );

            CREATE TABLE IF NOT EXISTS budgets (
                         budget_id INTEGER PRIMARY KEY,
                         customer_id INTEGER,
                         maximum_amount REAL,
                         start_date DATETIME,
                         end_date DATETIME,
                         FOREIGN KEY (customer_id) REFERENCES customers(customer_id) );

            CREATE TABLE IF NOT EXISTS goals (
                         goal_id INTEGER PRIMARY KEY,
                         customer_id INTEGER,
                         account_id INTEGER,
                         name TEXT,
                         target_amount REAL,
                         deadline DATETIME,
                         FOREIGN KEY (customer_id) REFERENCES customers(customer_id) );
            
            CREATE TABLE IF NOT EXISTS accounts (
                         account_id INTEGER PRIMARY KEY,
                         customer_id INTEGER,
                         name TEXT,
                         type TEXT,
                         balance REAL,
                         currency TEXT,
                         FOREIGN KEY (customer_id) REFERENCES customers(customer_id) );

            CREATE TABLE IF NOT EXISTS transactions (
                         transaction_id INTEGER PRIMARY KEY,
                         account_id INTEGER,
                         category TEXT,
                         name TEXT,
                         description TEXT,
                         amount REAL,
                         transaction_date DATETIME,
                         FOREIGN KEY (account_id) REFERENCES accounts(account_id) );

            CREATE TABLE IF NOT EXISTS recurring_transactions (
                         recurring_id INTEGER PRIMARY KEY,
                         account_id INTEGER,
                         category TEXT,
                         name TEXT,
                         description TEXT,
                         amount REAL,
                         start_date DATETIME,
                         next_date DATETIME,
                         frequency INTEGER,
                         frequency_type TEXT,
                         is_active BOOL DEFAULT 1,
                         FOREIGN KEY (account_id) REFERENCES accounts(account_id) );
            
            CREATE TABLE IF NOT EXISTS teams (
                         team_id INTEGER PRIMARY KEY,
                         manager_id INTEGER,
                         name TEXT,
                         description TEXT,
                         FOREIGN KEY (manager_id) REFERENCES advisers(adviser_id) );
            
            CREATE TABLE IF NOT EXISTS user_assignments (
                         adviser_id INTEGER,
                         customer_id INTEGER,
                         FOREIGN KEY (adviser_id) REFERENCES advisers(adviser_id),
                         FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
                         PRIMARY KEY (adviser_id, customer_id) );
            
            CREATE TABLE IF NOT EXISTS team_members (
                         team_id INTEGER,
                         adviser_id INTEGER,
                         FOREIGN KEY (team_id) REFERENCES teams(team_id),
                         FOREIGN KEY (adviser_id) REFERENCES advisers(adviser_id),
                         PRIMARY KEY (team_id, adviser_id) );
        ''')

        try:
            if db.execute('SELECT 1 FROM customers WHERE email = ?', ('customer@example.com',)).fetchone() is None:
                db.execute(
                    'INSERT INTO customers (name, email, password, currency) VALUES (?, ?, ?, ?)',
                    ('Test Customer', 'customer@example.com', generate_password_hash('cust123'), 'GBP')
                )

            if db.execute('SELECT 1 FROM advisers WHERE email = ?', ('adviser@example.com',)).fetchone() is None:
                db.execute(
                    'INSERT INTO advisers (name, email, password, currency, is_manager) VALUES (?, ?, ?, ?, ?)',
                    ('Test Adviser', 'adviser@example.com', generate_password_hash('adv123'), 'GBP', 0)
                )

            if db.execute('SELECT 1 FROM advisers WHERE email = ?', ('manager@example.com',)).fetchone() is None:
                db.execute(
                    'INSERT INTO advisers (name, email, password, currency, is_manager) VALUES (?, ?, ?, ?, ?)',
                    ('Test Manager', 'manager@example.com', generate_password_hash('mgr123'), 'GBP', 1)
                )

            db.commit()
        except sqlite3.IntegrityError:
            pass