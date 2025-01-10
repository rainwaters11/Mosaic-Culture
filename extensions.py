from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_caching import Cache

# Initialize Flask extensions
db = SQLAlchemy()
login_manager = LoginManager()
cache = Cache()

# Configure login manager
login_manager.login_view = 'login'
