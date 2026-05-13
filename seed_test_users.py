"""
Seed script — wipes and repopulates finance.db with realistic test data
spanning roughly the last two weeks.

Run:  python seed_test_users.py

Logins
------
Manager : sarah@dwk.com        / mgr123
Advisers: james@dwk.com        / adv123
          emily@dwk.com        / adv456
          marcus@dwk.com       / adv789
Customers (password: pass123 for all)
          alice@example.com
          robert@example.com
          priya@example.com
          tom@example.com
          lisa@example.com
          david@example.com
          emma@example.com
"""

import sqlite3
import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from database import init_db, DB

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def days_ago(n, hour=9, minute=0):
    """Return an ISO-format datetime string n days before today."""
    dt = datetime.now() - timedelta(days=n)
    return dt.replace(hour=hour, minute=minute, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')

def future(n, hour=10, minute=0):
    dt = datetime.now() + timedelta(days=n)
    return dt.replace(hour=hour, minute=minute, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')

PW = generate_password_hash('pass123')

# ---------------------------------------------------------------------------
# Reset & initialise
# ---------------------------------------------------------------------------

if os.path.exists(DB):
    os.remove(DB)
    print(f'Removed existing {DB}')

init_db()

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
db = conn

# ---------------------------------------------------------------------------
# Category IDs (inserted by init_db in this order)
# ---------------------------------------------------------------------------
CAT = {row['name']: row['category_id'] for row in db.execute('SELECT * FROM categories')}
FOOD, TRANSPORT, ENTERTAINMENT, BILLS, SALARY, SHOPPING, HEALTH, OTHER = (
    CAT['Food'], CAT['Transport'], CAT['Entertainment'], CAT['Bills'],
    CAT['Salary'], CAT['Shopping'], CAT['Health'], CAT['Other']
)

# ---------------------------------------------------------------------------
# Advisers
# ---------------------------------------------------------------------------
db.execute(
    'INSERT INTO advisers (name, email, password, currency, is_manager, description) VALUES (?,?,?,?,?,?)',
    ('Sarah Mitchell', 'sarah@dwk.com', generate_password_hash('mgr123'), 'GBP', 1,
     'Head of client services with 18 years in wealth management and portfolio strategy.')
)
db.execute(
    'INSERT INTO advisers (name, email, password, currency, is_manager, description) VALUES (?,?,?,?,?,?)',
    ('James Okafor', 'james@dwk.com', generate_password_hash('adv123'), 'GBP', 0,
     'Specialises in personal savings, budgeting, and first-time investor support.')
)
db.execute(
    'INSERT INTO advisers (name, email, password, currency, is_manager, description) VALUES (?,?,?,?,?,?)',
    ('Emily Chen', 'emily@dwk.com', generate_password_hash('adv456'), 'GBP', 0,
     'Experienced in ISA planning, mortgage preparation, and retirement portfolios.')
)
db.execute(
    'INSERT INTO advisers (name, email, password, currency, is_manager, description) VALUES (?,?,?,?,?,?)',
    ('Marcus Webb', 'marcus@dwk.com', generate_password_hash('adv789'), 'GBP', 0,
     'Focuses on small business owners, self-employed clients, and tax-efficient investing.')
)
db.commit()

adviser_ids = {r['name']: r['adviser_id'] for r in db.execute('SELECT adviser_id, name FROM advisers')}
SARAH, JAMES, EMILY, MARCUS = adviser_ids['Sarah Mitchell'], adviser_ids['James Okafor'], adviser_ids['Emily Chen'], adviser_ids['Marcus Webb']

# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------
customers_data = [
    ('Alice Thompson',  'alice@example.com',  PW, 'GBP', 'Saving for a house deposit and reviewing my pension contributions.'),
    ('Robert Davies',   'robert@example.com', PW, 'GBP', 'Recently started my first job and want to build good financial habits.'),
    ('Priya Sharma',    'priya@example.com',  PW, 'GBP', 'Running a small online business alongside my day job — need help with tax planning.'),
    ('Tom Harris',      'tom@example.com',    PW, 'GBP', 'Interested in ISA options and growing my emergency fund.'),
    ('Lisa Anderson',   'lisa@example.com',   PW, 'GBP', 'Going through a career change; need a full financial review.'),
    ('David Kim',       'david@example.com',  PW, 'GBP', 'Looking for an adviser to help with my investment portfolio.'),
    ('Emma Wilson',     'emma@example.com',   PW, 'GBP', 'New to the platform — exploring budgeting tools.'),
]
for row in customers_data:
    db.execute(
        'INSERT INTO customers (name, email, password, currency, description) VALUES (?,?,?,?,?)', row
    )
db.commit()

cust_ids = {r['name']: r['customer_id'] for r in db.execute('SELECT customer_id, name FROM customers')}
ALICE, ROBERT, PRIYA, TOM, LISA, DAVID, EMMA = (
    cust_ids['Alice Thompson'], cust_ids['Robert Davies'], cust_ids['Priya Sharma'],
    cust_ids['Tom Harris'], cust_ids['Lisa Anderson'], cust_ids['David Kim'], cust_ids['Emma Wilson']
)

# ---------------------------------------------------------------------------
# Assignments
# ---------------------------------------------------------------------------
assignments = [
    (JAMES,  ALICE,  'accepted'),
    (JAMES,  ROBERT, 'accepted'),
    (EMILY,  PRIYA,  'accepted'),
    (EMILY,  TOM,    'accepted'),
    (MARCUS, LISA,   'accepted'),
    (MARCUS, DAVID,  'pending'),   # David requested, not yet assigned
]
for adv, cust, status in assignments:
    db.execute('INSERT INTO user_assignments (adviser_id, customer_id, status) VALUES (?,?,?)', (adv, cust, status))
db.commit()

# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------
def add_account(customer_id, name, atype, balance, is_private=0):
    cur = db.execute(
        'INSERT INTO accounts (customer_id, name, type, balance, currency, is_private) VALUES (?,?,?,?,?,?)',
        (customer_id, name, atype, balance, 'GBP', is_private)
    )
    return cur.lastrowid

# Alice
acc_alice_chk  = add_account(ALICE,  'Current Account',   'Checking',    2413.50)
acc_alice_sav  = add_account(ALICE,  'ISA Savings',       'Savings',    12800.00)
acc_alice_inv  = add_account(ALICE,  'Investment Pot',    'Investment', 45200.00, is_private=1)

# Robert
acc_rob_chk    = add_account(ROBERT, 'Current Account',   'Checking',     890.20)
acc_rob_sav    = add_account(ROBERT, 'Rainy Day Fund',    'Savings',     3200.00)

# Priya
acc_pri_chk    = add_account(PRIYA,  'Business Current',  'Checking',    1648.75)
acc_pri_sav    = add_account(PRIYA,  'Tax Reserve',       'Savings',     8500.00)
acc_pri_crd    = add_account(PRIYA,  'Credit Card',       'Credit',      -342.60)

# Tom
acc_tom_chk    = add_account(TOM,    'Current Account',   'Checking',    3104.00)
acc_tom_sav    = add_account(TOM,    'Emergency Fund',    'Savings',     5000.00)

# Lisa
acc_lis_chk    = add_account(LISA,   'Current Account',   'Checking',    1195.30)
acc_lis_sav    = add_account(LISA,   'Savings Account',   'Savings',     6820.00)

# David
acc_dav_chk    = add_account(DAVID,  'Current Account',   'Checking',    2100.00)
acc_dav_sav    = add_account(DAVID,  'Savings',           'Savings',     4500.00)

# Emma
acc_emm_chk    = add_account(EMMA,   'Current Account',   'Checking',     782.40)

db.commit()

# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------
def txn(account_id, cat_id, name, amount, days, merchant=None, method=None, desc=None, hour=12):
    db.execute(
        '''INSERT INTO transactions
           (account_id, category_id, name, description, amount, transaction_date, merchant, payment_method)
           VALUES (?,?,?,?,?,?,?,?)''',
        (account_id, cat_id, name, desc or '', amount, days_ago(days, hour), merchant, method)
    )

# ── Alice ──────────────────────────────────────────────────────────────────
txn(acc_alice_chk, SALARY,        'Monthly Salary',        3200.00,  13, 'DWK Employer Ltd',  'Bank Transfer')
txn(acc_alice_chk, BILLS,         'Rent',                 -1100.00,  12, 'Landlord',           'Bank Transfer')
txn(acc_alice_chk, BILLS,         'Electricity Bill',       -68.40,  11, 'British Gas',        'Direct Debit')
txn(acc_alice_chk, FOOD,          'Weekly shop',           -112.30,  10, 'Waitrose',           'Debit Card')
txn(acc_alice_chk, TRANSPORT,     'Monthly bus pass',       -62.00,  10, 'TfL',                'Debit Card')
txn(acc_alice_chk, FOOD,          'Lunch',                  -14.80,   9, 'Pret a Manger',      'Debit Card')
txn(acc_alice_chk, ENTERTAINMENT, 'Cinema tickets',         -24.00,   8, 'Odeon',              'Credit Card')
txn(acc_alice_chk, FOOD,          'Coffee',                  -4.50,   7, 'Costa Coffee',       'Debit Card')
txn(acc_alice_chk, SHOPPING,      'New shoes',              -79.99,   6, 'Office Shoes',       'Debit Card')
txn(acc_alice_chk, FOOD,          'Weekly shop',            -98.60,   5, 'Sainsbury\'s',       'Debit Card')
txn(acc_alice_chk, HEALTH,        'Gym membership',         -45.00,   5, 'PureGym',            'Direct Debit')
txn(acc_alice_chk, FOOD,          'Dinner out',             -42.50,   4, 'Dishoom',            'Credit Card')
txn(acc_alice_chk, BILLS,         'Netflix',                -17.99,   3, 'Netflix',            'Direct Debit')
txn(acc_alice_chk, TRANSPORT,     'Taxi',                   -12.40,   2, 'Uber',               'Credit Card')
txn(acc_alice_chk, FOOD,          'Coffee',                  -4.50,   1, 'Starbucks',          'Debit Card')
txn(acc_alice_sav, OTHER,         'ISA Transfer',           500.00,   5, 'DWK Finance',        'Bank Transfer')

# ── Robert ─────────────────────────────────────────────────────────────────
txn(acc_rob_chk, SALARY,        'Salary',                 1800.00,  13, 'Tesco PLC',          'Bank Transfer')
txn(acc_rob_chk, BILLS,         'Rent',                   -650.00,  12, 'Landlord',           'Bank Transfer')
txn(acc_rob_chk, FOOD,          'Groceries',               -54.20,  11, 'Aldi',               'Debit Card')
txn(acc_rob_chk, TRANSPORT,     'Train to work',           -38.50,  10, 'Greater Anglia',     'Debit Card')
txn(acc_rob_chk, FOOD,          'Meal deal',                -4.00,   9, 'Boots',              'Cash')
txn(acc_rob_chk, ENTERTAINMENT, 'Spotify',                  -6.99,   8, 'Spotify',            'Direct Debit')
txn(acc_rob_chk, FOOD,          'Takeaway',                -19.50,   7, 'Deliveroo',          'Credit Card')
txn(acc_rob_chk, SHOPPING,      'Amazon order',            -34.99,   6, 'Amazon',             'Debit Card')
txn(acc_rob_chk, FOOD,          'Groceries',               -61.80,   5, 'Aldi',               'Debit Card')
txn(acc_rob_chk, BILLS,         'Mobile phone',            -22.00,   4, 'EE',                 'Direct Debit')
txn(acc_rob_chk, FOOD,          'Lunch',                   -11.20,   3, 'Greggs',             'Cash')
txn(acc_rob_chk, OTHER,         'Cashback',                  8.00,   2, 'Barclays',           'Bank Transfer')
txn(acc_rob_sav, OTHER,         'Savings deposit',         100.00,   1, 'DWK Finance',        'Bank Transfer')

# ── Priya ──────────────────────────────────────────────────────────────────
txn(acc_pri_chk, SALARY,        'Freelance invoice — April', 2400.00, 13, 'Client Co Ltd',    'Bank Transfer')
txn(acc_pri_chk, SALARY,        'Day job salary',            1600.00, 13, 'Apex Tech',        'Bank Transfer')
txn(acc_pri_chk, BILLS,         'Rent',                      -850.00, 12, 'Landlord',         'Bank Transfer')
txn(acc_pri_chk, BILLS,         'Internet',                   -35.00, 11, 'Virgin Media',     'Direct Debit')
txn(acc_pri_chk, TRANSPORT,     'Petrol',                     -72.00, 10, 'Shell',             'Debit Card')
txn(acc_pri_chk, FOOD,          'Supermarket',                -88.40,  9, 'Tesco',             'Debit Card')
txn(acc_pri_chk, HEALTH,        'Dental checkup',             -55.00,  8, 'City Dental',       'Debit Card')
txn(acc_pri_chk, ENTERTAINMENT, 'Theatre tickets',            -68.00,  7, 'National Theatre',  'Credit Card')
txn(acc_pri_chk, FOOD,          'Coffee',                      -5.20,  6, 'Pret a Manger',     'Debit Card')
txn(acc_pri_chk, SHOPPING,      'Office supplies',            -47.60,  5, 'Staples',           'Debit Card')
txn(acc_pri_chk, BILLS,         'Accountancy software',       -29.00,  4, 'QuickBooks',        'Direct Debit')
txn(acc_pri_chk, FOOD,          'Team lunch',                 -36.80,  3, 'Wagamama',          'Debit Card')
txn(acc_pri_chk, TRANSPORT,     'Parking',                     -9.00,  2, 'NCP',               'Cash')
txn(acc_pri_sav, OTHER,         'Tax reserve deposit',        800.00,  1, 'DWK Finance',       'Bank Transfer')
txn(acc_pri_crd, SHOPPING,      'Laptop stand',               -89.00,  7, 'John Lewis',        'Credit Card')

# ── Tom ────────────────────────────────────────────────────────────────────
txn(acc_tom_chk, SALARY,        'Salary',                    2600.00, 13, 'Hammond Ltd',       'Bank Transfer')
txn(acc_tom_chk, BILLS,         'Mortgage',                 -1050.00, 12, 'Halifax',           'Direct Debit')
txn(acc_tom_chk, BILLS,         'Council tax',               -145.00, 11, 'Local Council',     'Direct Debit')
txn(acc_tom_chk, FOOD,          'Weekly shop',               -124.60, 10, 'Morrisons',         'Debit Card')
txn(acc_tom_chk, TRANSPORT,     'Fuel',                       -68.00,  9, 'BP',                'Debit Card')
txn(acc_tom_chk, ENTERTAINMENT, 'Football match tickets',     -55.00,  8, 'Wembley Stadium',   'Debit Card')
txn(acc_tom_chk, FOOD,          'Takeaway pizza',             -28.50,  7, 'Domino\'s',         'Credit Card')
txn(acc_tom_chk, HEALTH,        'Pharmacy',                   -12.80,  6, 'Boots',             'Cash')
txn(acc_tom_chk, SHOPPING,      'DIY supplies',               -63.40,  5, 'B&Q',               'Debit Card')
txn(acc_tom_chk, FOOD,          'Weekly shop',               -109.20,  3, 'Morrisons',         'Debit Card')
txn(acc_tom_chk, BILLS,         'Broadband',                  -28.00,  2, 'BT',                'Direct Debit')
txn(acc_tom_chk, FOOD,          'Coffee and cake',             -8.60,  1, 'Costa Coffee',      'Debit Card')
txn(acc_tom_sav, OTHER,         'Savings transfer',           200.00,  5, 'DWK Finance',       'Bank Transfer')

# ── Lisa ───────────────────────────────────────────────────────────────────
txn(acc_lis_chk, SALARY,        'Final salary (old job)',    1950.00, 13, 'Meridian Corp',     'Bank Transfer')
txn(acc_lis_chk, BILLS,         'Rent',                      -750.00, 12, 'Landlord',          'Bank Transfer')
txn(acc_lis_chk, BILLS,         'Gas bill',                   -54.20, 11, 'Octopus Energy',    'Direct Debit')
txn(acc_lis_chk, FOOD,          'Groceries',                  -79.30, 10, 'Sainsbury\'s',      'Debit Card')
txn(acc_lis_chk, TRANSPORT,     'Bus pass',                   -42.00,  9, 'Arriva',            'Debit Card')
txn(acc_lis_chk, HEALTH,        'Yoga classes',               -35.00,  8, 'YogaHub',           'Direct Debit')
txn(acc_lis_chk, ENTERTAINMENT, 'Book purchase',              -18.99,  7, 'Waterstones',       'Debit Card')
txn(acc_lis_chk, FOOD,          'Lunch',                      -13.40,  6, 'Leon',              'Debit Card')
txn(acc_lis_chk, SHOPPING,      'Clothes',                    -92.00,  5, 'Zara',              'Credit Card')
txn(acc_lis_chk, FOOD,          'Grocery top-up',             -31.50,  3, 'Co-op',             'Debit Card')
txn(acc_lis_chk, BILLS,         'Phone bill',                 -20.00,  2, 'Vodafone',          'Direct Debit')
txn(acc_lis_sav, OTHER,         'Savings deposit',            150.00,  4, 'DWK Finance',       'Bank Transfer')

# ── David ──────────────────────────────────────────────────────────────────
txn(acc_dav_chk, SALARY,        'Salary',                    2200.00, 13, 'Nexus Digital',     'Bank Transfer')
txn(acc_dav_chk, BILLS,         'Rent',                      -800.00, 12, 'Landlord',          'Bank Transfer')
txn(acc_dav_chk, FOOD,          'Groceries',                  -65.20,  9, 'Lidl',              'Debit Card')
txn(acc_dav_chk, TRANSPORT,     'Oyster top-up',              -40.00,  8, 'TfL',               'Debit Card')
txn(acc_dav_chk, ENTERTAINMENT, 'Nintendo Switch game',       -49.99,  6, 'Nintendo eShop',    'Credit Card')
txn(acc_dav_chk, FOOD,          'Dinner out',                 -38.00,  5, 'Nandos',            'Debit Card')
txn(acc_dav_sav, OTHER,         'Savings transfer',           300.00,  3, 'DWK Finance',       'Bank Transfer')

# ── Emma ───────────────────────────────────────────────────────────────────
txn(acc_emm_chk, SALARY,        'Part-time salary',           950.00, 13, 'Corner Bistro Ltd', 'Bank Transfer')
txn(acc_emm_chk, BILLS,         'Rent share',                -380.00, 12, 'Flatshare',         'Bank Transfer')
txn(acc_emm_chk, FOOD,          'Groceries',                  -42.10, 10, 'Aldi',              'Debit Card')
txn(acc_emm_chk, TRANSPORT,     'Bus fare',                    -3.50,  8, 'Stagecoach',        'Cash')
txn(acc_emm_chk, ENTERTAINMENT, 'Netflix split',               -4.99,  7, 'Netflix',           'Direct Debit')
txn(acc_emm_chk, FOOD,          'Takeaway',                   -16.80,  5, 'Just Eat',          'Debit Card')
txn(acc_emm_chk, SHOPPING,      'H&M',                        -34.00,  3, 'H&M',               'Debit Card')

db.commit()

# ---------------------------------------------------------------------------
# Support tickets
# ---------------------------------------------------------------------------
def add_ticket(customer_id, ttype, subject, message, days, status='open', resolved_days=None):
    cur = db.execute(
        '''INSERT INTO support_tickets (customer_id, type, subject, message, status, created_at, resolved_at)
           VALUES (?,?,?,?,?,?,?)''',
        (customer_id, ttype, subject, message, status,
         days_ago(days), days_ago(resolved_days) if resolved_days else None)
    )
    return cur.lastrowid

t1 = add_ticket(ALICE,  'help',      'How do I export my transaction history?',
                'I would like to download my transactions as a spreadsheet for my accountant.',
                10, 'resolved', resolved_days=8)
t2 = add_ticket(ROBERT, 'help',      'Can I have multiple savings accounts?',
                'I want to set up a separate pot for holiday savings.',
                7, 'open')
t3 = add_ticket(PRIYA,  'complaint', 'Transaction date shown incorrectly',
                'Several of my transactions from last week are showing the wrong date in the system.',
                5, 'open')
t4 = add_ticket(TOM,    'help',      'Forgot how to mark an account as private',
                'I want to hide my investment account from my adviser temporarily.',
                3, 'resolved', resolved_days=1)
t5 = add_ticket(LISA,   'complaint', 'Adviser not responding to messages',
                'I submitted a consultation request 4 days ago and have heard nothing back.',
                4, 'open')
t6 = add_ticket(DAVID,  'help',      'Adviser assignment still pending',
                'I requested an adviser over a week ago but my status is still pending.',
                8, 'open')
db.commit()

# ---------------------------------------------------------------------------
# Adviser tasks  (auto-created from tickets + manual)
# ---------------------------------------------------------------------------
def add_task(adviser_id, customer_id, title, desc, priority, status, created_days,
             due_days=None, completed_days=None, ticket_id=None):
    db.execute(
        '''INSERT INTO adviser_tasks
           (adviser_id, customer_id, ticket_id, title, description, priority, status,
            due_date, created_at, completed_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)''',
        (adviser_id, customer_id, ticket_id, title, desc, priority, status,
         days_ago(due_days) if due_days else None,
         days_ago(created_days),
         days_ago(completed_days) if completed_days else None)
    )

# James's tasks
add_task(JAMES, ALICE,  'Review Alice\'s ISA contributions',
         'Client wants to maximise ISA allowance before end of tax year. Review current contributions.',
         1, 'pending', 6, due_days=1)
add_task(JAMES, ALICE,  'Respond to export query',
         'Alice asked how to export transactions for her accountant.',
         2, 'completed', 10, completed_days=8, ticket_id=t1)
add_task(JAMES, ROBERT, 'Set up savings pot guidance',
         'Robert wants a second savings account for holidays. Walk him through the process.',
         2, 'pending', 7, due_days=3, ticket_id=t2)
add_task(JAMES, ROBERT, 'First-time investor onboarding call',
         'Schedule an intro call to discuss Robert\'s investment risk appetite.',
         2, 'completed', 11, completed_days=9)

# Emily's tasks
add_task(EMILY, PRIYA,  'Investigate wrong transaction dates — complaint',
         'Priya has flagged incorrect dates on last week\'s transactions. Check system logs.',
         1, 'pending', 5, due_days=1, ticket_id=t3)
add_task(EMILY, PRIYA,  'Quarterly business finance review',
         'Review Priya\'s business income, tax reserve, and credit card usage.',
         2, 'pending', 9, due_days=4)
add_task(EMILY, TOM,    'Confirm private account feature — resolved',
         'Tom asked about marking accounts as private. Explained the lock icon.',
         3, 'completed', 3, completed_days=1, ticket_id=t4)
add_task(EMILY, TOM,    'ISA options consultation preparation',
         'Tom is interested in ISA products. Prepare a summary of current rates.',
         2, 'pending', 8, due_days=5)

# Marcus's tasks
add_task(MARCUS, LISA,  'Respond to adviser non-response complaint',
         'Lisa filed a complaint about lack of communication. Contact immediately.',
         1, 'pending', 4, due_days=0, ticket_id=t5)
add_task(MARCUS, LISA,  'Career change financial review',
         'Lisa is changing careers. Full income, savings, and spending review needed.',
         2, 'pending', 6, due_days=7)
add_task(MARCUS, LISA,  'Welcome call completed',
         'Introductory call with Lisa completed. Notes taken on financial goals.',
         3, 'completed', 10, completed_days=8)

db.commit()

# ---------------------------------------------------------------------------
# Consultations
# ---------------------------------------------------------------------------
def add_consultation(customer_id, adviser_id, title, notes, status, created_days, scheduled_offset=None):
    if scheduled_offset is not None:
        if scheduled_offset >= 0:
            sched = future(scheduled_offset, 14, 0)
        else:
            sched = days_ago(-scheduled_offset, 14, 0)
    else:
        sched = None
    db.execute(
        '''INSERT INTO consultations
           (customer_id, adviser_id, title, notes, scheduled_at, status, created_at)
           VALUES (?,?,?,?,?,?,?)''',
        (customer_id, adviser_id, title, notes, sched, status, days_ago(created_days))
    )

add_consultation(ALICE,  JAMES, 'ISA Year-End Review',
                 'Discuss maximising this year\'s ISA allowance and setting up an investment ISA.',
                 'scheduled', 7, scheduled_offset=3)
add_consultation(ALICE,  JAMES, 'Investment Portfolio Introduction',
                 'Initial overview of Alice\'s investment pot and risk tolerance.',
                 'completed', 12, scheduled_offset=-10)
add_consultation(ROBERT, JAMES, 'Getting Started with Savings',
                 'Robert is new to saving. Cover emergency fund basics and account setup.',
                 'scheduled', 6, scheduled_offset=5)
add_consultation(PRIYA,  EMILY, 'Tax Planning — Freelance Income',
                 'Review freelance income, expenses, and self-assessment deadlines.',
                 'scheduled', 4, scheduled_offset=2)
add_consultation(PRIYA,  EMILY, 'Business Account Review',
                 'Quarterly look at the business current account and credit card.',
                 'completed', 11, scheduled_offset=-9)
add_consultation(TOM,    EMILY, 'ISA Options Q&A',
                 'Tom wants to compare cash ISA vs. stocks & shares ISA.',
                 'scheduled', 5, scheduled_offset=7)
add_consultation(TOM,    EMILY, 'Mortgage Overpayment Strategy',
                 'Discussed overpayment options on Tom\'s Halifax mortgage.',
                 'completed', 14, scheduled_offset=-12)
add_consultation(LISA,   MARCUS, 'Career Change Financial Health Check',
                 'Full review of Lisa\'s income, outgoings, and savings ahead of career change.',
                 'scheduled', 3, scheduled_offset=4)
add_consultation(LISA,   MARCUS, 'Welcome Meeting',
                 'Introductory session — goals, risk appetite, and financial snapshot.',
                 'completed', 9, scheduled_offset=-7)

db.commit()

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
conn.close()

print('Database seeded successfully.\n')
print('  Staff logins:')
print('    sarah@dwk.com  / mgr123   (Manager)')
print('    james@dwk.com  / adv123   (Adviser — Alice, Robert)')
print('    emily@dwk.com  / adv456   (Adviser — Priya, Tom)')
print('    marcus@dwk.com / adv789   (Adviser — Lisa, David pending)')
print()
print('  Customer logins (all: pass123):')
for name, email in [
    ('Alice Thompson',  'alice@example.com'),
    ('Robert Davies',   'robert@example.com'),
    ('Priya Sharma',    'priya@example.com'),
    ('Tom Harris',      'tom@example.com'),
    ('Lisa Anderson',   'lisa@example.com'),
    ('David Kim',       'david@example.com'),
    ('Emma Wilson',     'emma@example.com'),
]:
    print(f'    {email:<26} ({name})')
