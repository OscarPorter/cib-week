from flask import render_template, request, redirect, url_for, session, flash, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from database import get_db
from functools import wraps
import pyotp
import qrcode
import base64
import io
import json

def no_cache(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = make_response(f(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    return decorated_function


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def get_user_by_role(db, role, user_id):
    if role == 'adviser':
        return db.execute('SELECT * FROM advisers WHERE adviser_id = ?', (user_id,)).fetchone()
    return db.execute('SELECT * FROM customers WHERE customer_id = ?', (user_id,)).fetchone()


def get_customer_account(db, account_id, customer_id):
    return db.execute(
        'SELECT * FROM accounts WHERE account_id = ? AND customer_id = ?', 
        (account_id, customer_id)
    ).fetchone()


def register_routes(app):
    
    @app.route('/')
    @no_cache
    def index():
        if 'user_id' not in session: return redirect(url_for('login'))
        db = get_db()
        if session.get('role') == 'customer':
            accounts = db.execute(
                'SELECT * FROM accounts WHERE customer_id = ? ORDER BY account_id DESC',
                (session['user_id'],)
            ).fetchall()
            return render_template('index.html', accounts=accounts)
        return render_template('index.html')

    @app.route('/accounts/create', methods=['POST'])
    @login_required
    @no_cache
    def create_account():
        if session.get('role') != 'customer':
            return redirect(url_for('index'))

        name = request.form.get('account_name', '').strip()
        acct_type = request.form.get('account_type', 'Checking').strip()
        balance_value = request.form.get('opening_balance', '0').strip() or '0'

        try:
            balance = float(balance_value)
        except ValueError:
            balance = 0.0

        if not name:
            flash('Please provide a valid account name.', 'warning')
            return redirect(url_for('index'))

        db = get_db()
        db.execute(
            'INSERT INTO accounts (customer_id, name, type, balance, currency) VALUES (?, ?, ?, ?, ?)',
            (session['user_id'], name, acct_type, balance, 'GBP')
        )
        db.commit()
        flash('Account created successfully.', 'success')
        return redirect(url_for('index'))

    @app.route('/accounts/<int:account_id>/delete', methods=['POST'])
    @login_required
    @no_cache
    def delete_account(account_id):
        if session.get('role') != 'customer':
            return redirect(url_for('index'))

        db = get_db()
        account = get_customer_account(db, account_id, session['user_id'])
        if not account:
            flash('Account not found.', 'warning')
            return redirect(url_for('index'))

        db.execute('DELETE FROM transactions WHERE account_id = ?', (account_id,))
        db.execute('DELETE FROM accounts WHERE account_id = ?', (account_id,))
        db.commit()
        flash('Account deleted successfully.', 'success')
        return redirect(url_for('index'))

    @app.route('/accounts/<int:account_id>')
    @login_required
    @no_cache
    def account_detail(account_id):
        if session.get('role') != 'customer':
            return redirect(url_for('index'))

        db = get_db()
        account = get_customer_account(db, account_id, session['user_id'])
        if not account:
            flash('Account not found.', 'warning')
            return redirect(url_for('index'))

        categories = db.execute('SELECT * FROM categories ORDER BY name').fetchall()

        transactions = db.execute('''
            SELECT t.*, c.name AS category_name, c.colour AS category_colour
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.category_id
            WHERE t.account_id = ?
            ORDER BY t.transaction_date DESC
        ''', (account_id,)).fetchall()

        transactions_asc = db.execute('''
            SELECT t.amount, t.transaction_date, c.name AS category_name, c.colour AS category_colour
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.category_id
            WHERE t.account_id = ?
            ORDER BY t.transaction_date ASC, t.transaction_id ASC
        ''', (account_id,)).fetchall()

        # Group by date for line chart
        date_groups = {}
        for t in transactions_asc:
            date = str(t['transaction_date'])[:10]
            amount = t['amount'] or 0
            if date not in date_groups:
                date_groups[date] = {'expenses': 0, 'revenue': 0, 'net': 0}
            if amount < 0:
                date_groups[date]['expenses'] += abs(amount)
            else:
                date_groups[date]['revenue'] += amount
            date_groups[date]['net'] += amount

        total_amounts = sum((t['amount'] or 0) for t in transactions_asc)
        opening_balance = (account['balance'] or 0) - total_amounts

        sorted_dates = sorted(date_groups.keys())
        line_balance, line_expenses, line_revenue = [], [], []
        running = opening_balance
        for date in sorted_dates:
            running += date_groups[date]['net']
            line_balance.append(round(running, 2))
            line_expenses.append(round(date_groups[date]['expenses'], 2))
            line_revenue.append(round(date_groups[date]['revenue'], 2))

        # Group expenses by category for expenditure pie chart
        cat_totals, cat_colours = {}, {}
        for t in transactions_asc:
            amount = t['amount'] or 0
            if amount < 0:
                cat = t['category_name'] or 'Uncategorised'
                cat_totals[cat] = cat_totals.get(cat, 0) + abs(amount)
                cat_colours[cat] = t['category_colour'] or '#AED6F1'

        # Group income by category for income pie chart
        income_totals, income_colours = {}, {}
        for t in transactions_asc:
            amount = t['amount'] or 0
            if amount > 0:
                cat = t['category_name'] or 'Uncategorised'
                income_totals[cat] = income_totals.get(cat, 0) + amount
                income_colours[cat] = t['category_colour'] or '#98D8C8'

        pie_labels = list(cat_totals.keys())
        income_labels = list(income_totals.keys())
        chart_data = json.dumps({
            'line': {
                'labels': sorted_dates,
                'balance': line_balance,
                'expenses': line_expenses,
                'revenue': line_revenue,
            },
            'pie': {
                'labels': pie_labels,
                'amounts': [round(cat_totals[k], 2) for k in pie_labels],
                'colours': [cat_colours[k] for k in pie_labels],
            },
            'pie_income': {
                'labels': income_labels,
                'amounts': [round(income_totals[k], 2) for k in income_labels],
                'colours': [income_colours[k] for k in income_labels],
            }
        })

        return render_template(
            'account_detail.html',
            account=account,
            transactions=transactions,
            categories=categories,
            chart_data=chart_data,
            today=datetime.utcnow().strftime('%Y-%m-%d')
        )

    @app.route('/accounts/<int:account_id>/transactions/add', methods=['POST'])
    @login_required
    @no_cache
    def add_transaction(account_id):
        if session.get('role') != 'customer':
            return redirect(url_for('index'))

        name = request.form.get('transaction_name', '').strip()
        category = request.form.get('category', '').strip()
        description = request.form.get('description', '').strip()
        amount_value = request.form.get('amount', '0').strip() or '0'
        transaction_date = request.form.get('transaction_date', '').strip() or datetime.utcnow().strftime('%Y-%m-%d')

        try:
            amount = float(amount_value)
        except ValueError:
            amount = None

        if not name or amount is None:
            flash('Please complete the transaction name and amount.', 'warning')
            return redirect(url_for('account_detail', account_id=account_id))

        db = get_db()
        account = get_customer_account(db, account_id, session['user_id'])
        if not account:
            flash('Account not found.', 'warning')
            return redirect(url_for('index'))

        category_row = db.execute(
            'SELECT category_id FROM categories WHERE name = ?', (category,)
        ).fetchone() if category else None
        category_id = category_row['category_id'] if category_row else None

        db.execute(
            'INSERT INTO transactions (account_id, category_id, name, description, amount, transaction_date) VALUES (?, ?, ?, ?, ?, ?)',
            (account_id, category_id, name, description, amount, transaction_date)
        )
        db.execute(
            'UPDATE accounts SET balance = balance + ? WHERE account_id = ?',
            (amount, account_id)
        )
        db.commit()
        flash('Transaction added successfully.', 'success')
        return redirect(url_for('account_detail', account_id=account_id))

    @app.route('/accounts/<int:account_id>/transactions/<int:transaction_id>/delete', methods=['POST'])
    @login_required
    @no_cache
    def delete_transaction(account_id, transaction_id):
        if session.get('role') != 'customer':
            return redirect(url_for('index'))

        db = get_db()
        account = get_customer_account(db, account_id, session['user_id'])
        if not account:
            flash('Account not found.', 'warning')
            return redirect(url_for('index'))

        transaction = db.execute(
            'SELECT * FROM transactions WHERE transaction_id = ? AND account_id = ?',
            (transaction_id, account_id)
        ).fetchone()
        if not transaction:
            flash('Transaction not found.', 'warning')
            return redirect(url_for('account_detail', account_id=account_id))

        db.execute('DELETE FROM transactions WHERE transaction_id = ?', (transaction_id,))
        db.execute('UPDATE accounts SET balance = balance - ? WHERE account_id = ?', (transaction['amount'], account_id))
        db.commit()
        flash('Transaction removed successfully.', 'success')
        return redirect(url_for('account_detail', account_id=account_id))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            db = get_db()
            user_type = request.form.get('user_type', 'customer')
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            user = None
            role = None

            if user_type == 'adviser':
                user = db.execute('SELECT * FROM advisers WHERE email = ?', (email,)).fetchone()
                role = 'adviser'
            else:
                user = db.execute('SELECT * FROM customers WHERE email = ?', (email,)).fetchone()
                role = 'customer'

            if user and check_password_hash(user['password'], password):
                pending_data = {
                    'user_id': user['adviser_id'] if role == 'adviser' else user['customer_id'],
                    'username': user['name'],
                    'role': role,
                    'is_manager': bool(user['is_manager']) if role == 'adviser' else False
                }

                if user['is_2fa_enabled']:
                    session['pending_2fa'] = pending_data
                    return redirect(url_for('two_factor'))

                session.update(pending_data)
                if role == 'adviser' and pending_data['is_manager']:
                    flash('Welcome manager. Your adviser account has is_manager access.', 'success')
                return redirect(url_for('index'))

            flash('Invalid email or password. Please try again.', 'danger')
        return render_template('login.html')

    @app.route('/two-factor', methods=['GET', 'POST'])
    @no_cache
    def two_factor():
        pending = session.get('pending_2fa')
        if not pending:
            flash('Please sign in before entering a 2FA code.', 'warning')
            return redirect(url_for('login'))

        if request.method == 'POST':
            code = request.form.get('code', '').strip()
            db = get_db()
            user = get_user_by_role(db, pending['role'], pending['user_id'])

            if user and user['totp_secret'] and pyotp.TOTP(user['totp_secret']).verify(code, valid_window=1):
                session.update(pending)
                session.pop('pending_2fa', None)
                flash('Sign in successful.', 'success')
                return redirect(url_for('index'))

            flash('Invalid authentication code. Please try again.', 'danger')

        return render_template('two_factor.html')

    @app.route('/setup-2fa', methods=['GET', 'POST'])
    @login_required
    @no_cache
    def setup_2fa():
        db = get_db()
        user = get_user_by_role(db, session['role'], session['user_id'])

        if not user:
            session.clear()
            return redirect(url_for('login'))

        if request.method == 'POST':
            code = request.form.get('code', '').strip()
            secret = session.get('totp_secret_setup')

            if not secret:
                flash('Your 2FA setup session expired. Please refresh the page.', 'warning')
                return redirect(url_for('setup_2fa'))

            if pyotp.TOTP(secret).verify(code, valid_window=1):
                if session['role'] == 'adviser':
                    db.execute('UPDATE advisers SET totp_secret = ?, is_2fa_enabled = 1 WHERE adviser_id = ?', (secret, session['user_id']))
                else:
                    db.execute('UPDATE customers SET totp_secret = ?, is_2fa_enabled = 1 WHERE customer_id = ?', (secret, session['user_id']))
                db.commit()
                session.pop('totp_secret_setup', None)
                flash('Two-factor authentication is now enabled for your account.', 'success')
                return redirect(url_for('index'))

            flash('That code is not valid. Please try again.', 'danger')

        if user['is_2fa_enabled']:
            flash('Two-factor authentication is already enabled for your account.', 'info')
            return redirect(url_for('index'))

        secret = pyotp.random_base32()
        session['totp_secret_setup'] = secret
        provisioning_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user['email'],
            issuer_name='DWK Finance'
        )

        qr = qrcode.QRCode(box_size=8, border=2)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')

        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_code_data = base64.b64encode(buffer.getvalue()).decode()

        return render_template(
            'setup_2fa.html',
            qr_code_data=qr_code_data,
            secret=secret
        )

    @app.route('/logout')
    def logout():
        session.clear()
        flash('You have been logged out.', 'success')
        return redirect(url_for('login'))

    @app.route('/forgot-password', methods=['GET', 'POST'])
    def forgot_password():
        """Handle password reset requests"""
        if request.method == 'POST':
            email = request.form.get('email', '').strip()
            db = get_db()
            
            #Check if email exists in either customers or advisers table
            customer = db.execute('SELECT * FROM customers WHERE email = ?', (email,)).fetchone()
            adviser = db.execute('SELECT * FROM advisers WHERE email = ?', (email,)).fetchone()
            
            if customer or adviser:
                # TODO: In production, send a password reset email here
                # For now, we'll just show a success message
                flash(
                    'If an account exists with that email, you will receive password reset instructions shortly. '
                    'Please check your email and follow the instructions provided.',
                    'success'
                )
            else:
                #show success message for security reasons
                flash(
                    'If an account exists with that email, you will receive password reset instructions shortly. '
                    'Please check your email and follow the instructions provided.',
                    'info'
                )
            
            return redirect(url_for('login'))
        
        return render_template('forgot_password.html')

    @app.route('/about-vectura')
    def about_vectura():
        """Serve the Vectura team information page"""
        return render_template('about_vectura.html')

    @app.route('/terms')
    def terms():
        """Serve the Terms of Service page"""
        return render_template('terms.html')

    @app.route('/privacy')
    def privacy():
        """Serve the Privacy Policy page"""
        return render_template('privacy.html')

    @app.route('/settings', methods=['GET', 'POST'])
    @login_required
    @no_cache
    def settings():
        db = get_db()
        user = get_user_by_role(db, session['role'], session['user_id'])

        if not user:
            session.clear()
            return redirect(url_for('login'))

        if request.method == 'POST':
            action = request.form.get('action')
            if action == 'disable_2fa':
                code = request.form.get('code', '').strip()
                if user['totp_secret'] and pyotp.TOTP(user['totp_secret']).verify(code, valid_window=1):
                    if session['role'] == 'adviser':
                        db.execute('UPDATE advisers SET totp_secret = NULL, is_2fa_enabled = 0 WHERE adviser_id = ?', (session['user_id'],))
                    else:
                        db.execute('UPDATE customers SET totp_secret = NULL, is_2fa_enabled = 0 WHERE customer_id = ?', (session['user_id'],))
                    db.commit()
                    flash('Two-factor authentication has been disabled.', 'success')
                    return redirect(url_for('settings'))
                else:
                    flash('Invalid authentication code. Please try again.', 'danger')

        return render_template('settings.html', user=user)

    @app.route('/contact')
    def contact():
        """Serve the Contact Us page"""
        return render_template('contact.html')
