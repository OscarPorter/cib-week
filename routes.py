from flask import render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from database import get_db

def register_routes(app):
    
    @app.route('/')
    def index():
        return render_template('index.html')
