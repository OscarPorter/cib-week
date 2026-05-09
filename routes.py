from flask import render_template, request, redirect, url_for, session, flash, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from database import get_db
from functools import wraps

def no_cache(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = make_response(f(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    return decorated_function

def register_routes(app):
    
    @app.route('/')
    @no_cache
    def index():
        if 'user_id' not in session: return redirect(url_for('login'))
        
        return render_template('index.html')

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
                session_data = {
                    'user_id': user['adviser_id'] if role == 'adviser' else user['customer_id'],
                    'username': user['name'],
                    'role': role,
                    'is_manager': bool(user['is_manager']) if role == 'adviser' else False
                }
                session.update(session_data)

                if role == 'adviser' and session_data['is_manager']:
                    flash('Welcome manager. Your adviser account has is_manager access.', 'success')

                return redirect(url_for('index'))

            flash('Invalid email or password. Please try again.', 'danger')
        return render_template('login.html')

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

    @app.route('/contact')
    def contact():
        """Serve the Contact Us page"""
        return render_template('contact.html')
