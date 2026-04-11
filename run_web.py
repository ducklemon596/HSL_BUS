"""Entry point for Flask web server"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from hsl_bus.web import create_app

if __name__ == "__main__":
    app = create_app()
    from hsl_bus.config import settings_instance
    from hsl_bus.utils import get_logger

    logger = get_logger(__name__)
    logger.info(
        f"🌐 Starting Flask server on {settings_instance.FLASK_HOST}:{settings_instance.FLASK_PORT}"
    )

    try:
        app.socketio.run(
            app,
            host=settings_instance.FLASK_HOST,
            port=settings_instance.FLASK_PORT,
            debug=settings_instance.FLASK_DEBUG,
            allow_unsafe_werkzeug=True,
        )
    except KeyboardInterrupt:
        logger.warning("\n🛑 Web server stopped by user")
