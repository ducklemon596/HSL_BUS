import paho.mqtt.client as mqtt
import os
import ssl
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from google.cloud import pubsub_v1

load_dotenv()

# --- 1. CẤU HÌNH LOGGING (QUAN TRỌNG) ---
# Tạo logger
logger = logging.getLogger("HSL_Ingestion")
logger.setLevel(logging.INFO)

# Định dạng log: [Thời gian] [Mức độ] [Nội dung]
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

# Handler 1: Ghi vào file (Tự động cắt file khi đạt 5MB, giữ lại 3 file cũ)
# encoding='utf-8' để ghi được icon ✅ ❌
file_handler = RotatingFileHandler(
    "pipeline.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
file_handler.setFormatter(formatter)

# Handler 2: In ra màn hình Console (để bạn vẫn theo dõi được trực tiếp)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# Thêm cả 2 handler vào logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# --- 2. CẤU HÌNH MQTT & PUBSUB ---
MQTT_BROKER = os.getenv("MQTT_BROKER", "mqtt.hsl.fi")
MQTT_PORT = int(os.getenv("MQTT_PORT", 8883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "/hfp/v2/journey/ongoing/vp/bus/#")

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCP_PUBSUB_TOPIC = os.getenv("GCP_PUBSUB_TOPIC")

# Initialize Pub/Sub Publisher
publisher = pubsub_v1.PublisherClient()
try:
    topic_path = publisher.topic_path(GCP_PROJECT_ID, GCP_PUBSUB_TOPIC)
except Exception as e:
    logger.error(f"❌ Lỗi cấu hình Pub/Sub: {e}")
    exit(1)


def get_callback(future, payload):
    """
    Wrapper function to capture the payload context for logging.
    """

    def callback(future):
        try:
            # Check if an exception occurred during publishing
            if future.exception():
                # Chỉ log lỗi vào file/console thay vì print
                logger.error(f"❌ Pub/Sub Error: {future.exception()}")
            else:
                # Log mức INFO khi thành công
                logger.info(f"🚀 Published to Pub/Sub. ID: {future.result()}")
        except Exception as e:
            logger.error(f"❌ Callback crash: {e}")

    return callback


# --- CALLBACK FUNCTIONS (API VERSION 2) ---
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        logger.info(f"✅ Connected via SSL! (Code: {reason_code})")
        logger.info(f"📡 Subscribing to: {MQTT_TOPIC}")
        client.subscribe(MQTT_TOPIC)
    else:
        logger.error(f"❌ Connection failed, code: {reason_code}")


def on_message(client, userdata, msg):
    try:
        payload = msg.payload

        # Publish to Pub/Sub (Asynchronous)
        future = publisher.publish(topic_path, payload)

        # Attach callback
        future.add_done_callback(get_callback(future, payload))

    except Exception as e:
        logger.error(f"❌ Processing error: {e}")


# --- CLIENT INITIALIZATION ---
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

# Enable SSL/TLS
client.tls_set(cert_reqs=ssl.CERT_NONE)

client.on_connect = on_connect
client.on_message = on_message

# --- MAIN EXECUTION ---
logger.info("⏳ Connecting to HSL via secure channel (SSL)...")
try:
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()
except KeyboardInterrupt:
    logger.warning("\n🛑 Program stopped by user.")
    client.disconnect()
except Exception as e:
    logger.critical(f"💀 Fatal Error: {e}")
