import json
import time
import paho.mqtt.client as mqtt
import os
import ssl
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from kafka import KafkaProducer

load_dotenv()

# --- 1. Tạo logger ---
logger = logging.getLogger("HSL_Ingestion")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler = RotatingFileHandler(
    "pipeline.log", maxBytes=5 * 1024 * 1024, backupCount=10, encoding="utf-8"
)
file_handler.setFormatter(formatter)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# --- 2. CẤU HÌNH MQTT & KAFKA ---
MQTT_BROKER = os.getenv("MQTT_BROKER", "mqtt.hsl.fi")
MQTT_PORT = int(os.getenv("MQTT_PORT", 8883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "/hfp/v2/journey/ongoing/vp/bus/#")

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "hsl_bus")

# --- 3. KẾT NỐI KAFKA ---
while True:
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BROKER,
            # Nhận vào Dictionary và tự động dịch ra nhị phân
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: str(k).encode("utf-8"),
        )
        logger.info(f"✅ Connected to Kafka at {KAFKA_BROKER}")
        break
    except Exception as e:
        logger.error(f"❌ Kafka connection failed: {e}. Retrying in 5 seconds...")
        time.sleep(5)


# --- CALLBACK FUNCTIONS CỦA KAFKA ---
def on_send_success(record_metadata):
    logger.info(
        f"🚀 Sent to Kafka | Partition: {record_metadata.partition} | Offset: {record_metadata.offset}"
    )


def on_send_error(excp):
    logger.error(f"❌ Kafka Error: {excp}")


# --- CALLBACK FUNCTIONS CỦA MQTT ---
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        logger.info(f"✅ Connected via SSL! (Code: {reason_code})")
        logger.info(f"📡 Subscribing to: {MQTT_TOPIC}")
        client.subscribe(MQTT_TOPIC)
    else:
        logger.error(f"❌ Connection to MQTT failed, code: {reason_code}")


def on_message(client, userdata, msg):
    try:
        # Bước 1: Lấy string gốc
        payload = msg.payload.decode("utf-8")

        # Bước 2: Dịch ra Dictionary
        json_data = json.loads(payload)
        vp = json_data.get("VP", {})

        if vp:
            oper_id = str(vp.get("oper", "0"))
            veh_num = str(vp.get("veh", "0"))
            unique_veh_id = f"{oper_id}_{veh_num}"

            vp["unique_veh_id"] = unique_veh_id

            # Bước 4: Đẩy ĐÚNG biến json_data (Dictionary) đi để bộ serializer làm việc
            producer.send(KAFKA_TOPIC, value=json_data, key=unique_veh_id).add_callback(
                on_send_success
            ).add_errback(on_send_error)

    except Exception as e:
        logger.error(f"❌ Processing error: {e}")


# --- CLIENT INITIALIZATION ---
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
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
