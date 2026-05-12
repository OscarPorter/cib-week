from database import get_db, init_db
from werkzeug.security import generate_password_hash


TEST_USERS = [
    {
        'table': 'customers',
        'query': 'SELECT 1 FROM customers WHERE email = ?',
        'insert_sql': 'INSERT INTO customers (name, email, password, currency) VALUES (?, ?, ?, ?)',
        'params': ('Test Customer', 'customer@example.com', generate_password_hash('cust123'), 'GBP'),
    },
    {
        'table': 'advisers',
        'query': 'SELECT 1 FROM advisers WHERE email = ?',
        'insert_sql': 'INSERT INTO advisers (name, email, password, currency, is_manager) VALUES (?, ?, ?, ?, ?)',
        'params': ('Test Adviser', 'adviser@example.com', generate_password_hash('adv123'), 'GBP', 0),
    },
    {
        'table': 'advisers',
        'query': 'SELECT 1 FROM advisers WHERE email = ?',
        'insert_sql': 'INSERT INTO advisers (name, email, password, currency, is_manager) VALUES (?, ?, ?, ?, ?)',
        'params': ('Test Manager', 'manager@example.com', generate_password_hash('mgr123'), 'GBP', 1),
    },
]


def add_test_users():
    init_db()
    with get_db() as db:
        for user in TEST_USERS:
            if db.execute(user['query'], (user['params'][1],)).fetchone() is None:
                db.execute(user['insert_sql'], user['params'])
        db.commit()


if __name__ == '__main__':
    add_test_users()
    print('Test users have been added to finance.db')
