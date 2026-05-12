import sqlite3

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
                         end_date DATETIME );

            CREATE TABLE IF NOT EXISTS goals (
                         goal_id INTEGER PRIMARY KEY,
                         account_id INTEGER,
                         name TEXT,
                         target_amount REAL,
                         deadline DATETIME,
                         FOREIGN KEY (account_id) REFERENCES accounts(account_id) );
            
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
                         category_id INTEGER,
                         name TEXT,
                         description TEXT,
                         amount REAL,
                         transaction_date DATETIME,
                         FOREIGN KEY (account_id) REFERENCES accounts(account_id),
                         FOREIGN KEY (category_id) REFERENCES categories(category_id) );

            CREATE TABLE IF NOT EXISTS recurring_transactions (
                         recurring_id INTEGER PRIMARY KEY,
                         account_id INTEGER,
                         category_id INTEGER,
                         name TEXT,
                         description TEXT,
                         amount REAL,
                         start_date DATETIME,
                         next_date DATETIME,
                         frequency INTEGER,
                         frequency_type TEXT,
                         is_active BOOL DEFAULT 1,
                         FOREIGN KEY (account_id) REFERENCES accounts(account_id),
                         FOREIGN KEY (category_id) REFERENCES categories(category_id) );
            
            CREATE TABLE IF NOT EXISTS teams (
                         team_id INTEGER PRIMARY KEY,
                         manager_id INTEGER,
                         name TEXT,
                         description TEXT,
                         FOREIGN KEY (manager_id) REFERENCES advisers(adviser_id) );

            CREATE TABLE IF NOT EXISTS categories (
                         category_id INTEGER PRIMARY KEY,
                         name TEXT UNIQUE,
                         colour TEXT,
                         description TEXT );
            
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
            
            -- Insert default categories if not exist
            INSERT OR IGNORE INTO categories (name, colour, description) VALUES 
                ('Food', '#FF6B6B', 'Food and dining expenses'),
                ('Transport', '#4ECDC4', 'Transportation costs'),
                ('Entertainment', '#45B7D1', 'Entertainment and leisure'),
                ('Bills', '#FFA07A', 'Utility bills and subscriptions'),
                ('Salary', '#98D8C8', 'Income from salary'),
                ('Shopping', '#F7DC6F', 'General shopping'),
                ('Health', '#BB8FCE', 'Medical and health expenses'),
                ('Other', '#AED6F1', 'Miscellaneous');
        ''')