from flask import Flask, render_template
from flask_socketio import SocketIO
import json
import os
import redis
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

redis_host = os.getenv("REDIS_HOST", "localhost")
redis_client = redis.Redis(host=redis_host, port=6379, db=0, decode_responses=True)


# --- LUỒNG PHÁT SÓNG ---
def periodic_broadcaster():
    print("📡 Web Server bắt đầu phát sóng...")
    while True:
        socketio.sleep(1)
        try:
            snapshot = {}

            cursor = 0
            while True:
                cursor, keys = redis_client.scan(
                    cursor=cursor, match="bus:*", count=1000
                )

                if keys:
                    values = redis_client.mget(keys)
                    for key, data_str in zip(keys, values):
                        if data_str:
                            try:
                                data = json.loads(data_str)
                                veh_id = key.split(":")[1]
                                snapshot[veh_id] = data
                            except:
                                continue

                if cursor == 0:
                    break

            if snapshot:
                socketio.emit("batch_update", snapshot)

        except Exception as e:
            print(f"⚠️ Lỗi Redis: {e}")
            socketio.sleep(5)


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    socketio.start_background_task(periodic_broadcaster)
    print("🚀 Web Server đang khởi động...")
    socketio.run(app, host="0.0.0.0", debug=True, port=5000, allow_unsafe_werkzeug=True)
