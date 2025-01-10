import os
import logging
from flask import Flask

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create the app
app = Flask(__name__)

@app.route('/')
def index():
    return "Test server is running!"

if __name__ == "__main__":
    try:
        logger.info("Starting test server...")
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port, debug=True)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        raise
