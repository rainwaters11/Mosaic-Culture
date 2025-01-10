from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_caching import Cache
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
import logging

# Initialize Flask extensions
db = SQLAlchemy()
login_manager = LoginManager()
cache = Cache()

# Configure login manager
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

# Configure SQLAlchemy session handling
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    # Enable foreign key support and proper transaction handling
    cursor = dbapi_connection.cursor()
    cursor.execute("SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL READ COMMITTED")
    cursor.close()

# Add session cleanup
@event.listens_for(db.session, 'after_rollback')
def handle_after_rollback(session):
    logging.warning("SQLAlchemy session rollback occurred")
    session.expire_all()

@event.listens_for(db.session, 'after_commit')
def handle_after_commit(session):
    session.expire_all()

# Add error handling to session operations
def safe_commit():
    """Commit the current transaction safely, with rollback on error."""
    try:
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"Database error occurred: {str(e)}")
        raise

# Attach the safe commit method to the db object
db.safe_commit = safe_commit