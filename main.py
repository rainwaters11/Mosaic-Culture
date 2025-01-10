import os
import logging
from app import app, db, init_services

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def initialize_application():
    """Initialize all application components"""
    try:
        # Initialize database tables
        with app.app_context():
            logger.info("Initializing database...")
            db.create_all()
            logger.info("Database initialized successfully")

        # Initialize services
        logger.info("Initializing services...")
        services = init_services()
        if not all(services.values()):
            failed_services = [name for name, service in services.items() if not service]
            logger.warning(f"Some services failed to initialize: {failed_services}")
        logger.info("Services initialization completed")

        return True
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        return False

def main():
    try:
        # Initialize application
        if not initialize_application():
            logger.error("Application initialization failed")
            return

        logger.info("Starting Flask server...")
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port, debug=True)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        raise

if __name__ == "__main__":
    main()