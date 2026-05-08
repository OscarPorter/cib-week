from flask import Flask
from database import init_db
from routes import register_routes

app = Flask(__name__)
app.secret_key = 'super_secret_finance_key'

init_db()
register_routes(app)

if __name__ == '__main__':
    app.run(debug=False)
