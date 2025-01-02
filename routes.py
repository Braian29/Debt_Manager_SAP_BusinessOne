# routes.py
from flask import Flask
from controllers import routes_blueprint
from config import Config
from utils import format_number 

app = Flask(__name__)
app.config.from_object(Config)
app.register_blueprint(routes_blueprint)

app.jinja_env.filters['format_number'] = format_number 

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5010)