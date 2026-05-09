from flask import render_template, request, redirect, url_for, session, flash, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from database import get_db
from functools import wraps
import pyotp
import qrcode
import base64
import io

try:
    from PIL import Image  # noqa: F401
    QR_IMAGE_FACTORY = None
except ImportError:
    from qrcode.image.svg import SvgPathImage
    QR_IMAGE_FACTORY = SvgPathImage

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

        buffer = io.BytesIO()
        if QR_IMAGE_FACTORY is None:
            img = qr.make_image(fill_color='black', back_color='white')
            img.save(buffer, format='PNG')
            qr_code_data = base64.b64encode(buffer.getvalue()).decode()
            qr_code_type = 'png'
        else:
            img = qr.make_image(image_factory=QR_IMAGE_FACTORY)
            img.save(buffer)
            qr_code_data = base64.b64encode(buffer.getvalue()).decode()
            qr_code_type = 'svg'

        return render_template(
            'setup_2fa.html',
            qr_code_data=qr_code_data,
            qr_code_type=qr_code_type,
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

    @app.route('/contact')
    def contact():
        """Serve the Contact Us page"""
        return render_template('contact.html')
