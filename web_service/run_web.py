"""Flask web application for real-time bus data"""

from flask import Flask, render_template
from flask_socketio import SocketIO

from shared_lib.settings import get_settings_instance
from shared_lib.logger import get_logger_instance
from shared_lib.redis_service import get_redis_service

settings_instance = get_settings_instance()
logger = get_logger_instance(__name__)


def create_app() -> Flask:
    """Create and configure Flask application"""
    app = Flask(__name__, template_folder="templates", static_folder="templates")

    # Configuration
    app.config["JSON_AS_ASCII"] = False

    # Initialize SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

    # Initialize services
    redis_service = get_redis_service()

    # Routes
    @app.route("/")
    def index():
        """Serve main page"""
        return render_template("index.html")

    # Background broadcaster task
    def periodic_broadcaster():
        """Broadcast bus data to all connected clients"""
        logger.info("📡 Web Server broadcasting started")

        while True:
            socketio.sleep(1)  # Update every 1 second
            try:
                # Get all current bus data from Redis
                snapshot = redis_service.get_all_buses()
                logger.info(f"🔍 Dữ liệu bốc từ Redis: {snapshot}")

                if snapshot:
                    # Broadcast to all connected clients
                    socketio.emit("batch_update", snapshot)
                    logger.info(f"📤 Broadcasted {len(snapshot)} buses")

            except Exception as e:
                logger.error(f"⚠️ Broadcasting error: {e}")
                socketio.sleep(5)

    socketio.start_background_task(periodic_broadcaster)
    logger.info("✅ Background broadcaster task scheduled")

    # Error handlers
    @app.errorhandler(400)
    def bad_request(error):
        return {"error": "Bad request"}, 400

    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Not found"}, 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return {"error": "Internal server error"}, 500

    # Store socketio instance on app
    app.socketio = socketio

    return app


# Create app instance
app = create_app()


def main():
    """Main entry point for web server"""
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
    except Exception as e:
        logger.critical(f"💀 Fatal server error: {e}")
        raise


if __name__ == "__main__":
    app = create_app()

    settings_instance = get_settings_instance()
    logger = get_logger_instance(__name__)
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
