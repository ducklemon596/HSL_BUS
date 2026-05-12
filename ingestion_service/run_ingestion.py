"""Kafka ingestion module for MQTT data."""

import base64
from datetime import timezone
import time
import json
import ssl
import paho.mqtt.client as mqtt

# Required libraries for GCP Managed Kafka authentication
from confluent_kafka import Producer
from google.auth import default
from google.auth.transport.requests import Request

from shared_lib.settings import get_settings_instance
from shared_lib.logger import get_logger_instance

logger = get_logger_instance(__name__)
settings_instance = get_settings_instance()


def get_gcp_iam_token(config_str):
    """
    Hàm chế tạo JWT giả để bọc Google IAM Token cho Kafka.
    Miễn nhiễm với lỗi import datetime conflict.
    """
    try:
        # Import cục bộ để chắc chắn gọi đúng hàm của google-auth
        from google.auth import default
        from google.auth.transport.requests import Request

        # 1. Lấy credentials có quyền Cloud Platform
        credentials, _ = default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        credentials.refresh(Request())

        # 2. Tạo Header định danh cho Google
        header = json.dumps({"typ": "JWT", "alg": "GOOG_OAUTH2_TOKEN"})

        # 3. Tạo Payload chứa hạn sử dụng và email (Đã fix lỗi timezone)
        token_data = {
            # Gắn múi giờ UTC vào expiry để lấy timestamp chuẩn
            "exp": int(credentials.expiry.replace(tzinfo=timezone.utc).timestamp()),
            # Dùng time.time() cực kỳ an toàn, không sợ đụng datetime
            "iat": int(time.time()),
            "iss": "Google",
            "sub": credentials.service_account_email,
        }
        payload = json.dumps(token_data)

        # 4. Hàm mã hóa Base64 an toàn cho URL
        def encode_b64(source):
            return (
                base64.urlsafe_b64encode(source.encode("utf-8"))
                .decode("utf-8")
                .rstrip("=")
            )

        # 5. Lắp ráp thành chuỗi JWT chuẩn: Header.Payload.Signature
        jwt_token = f"{encode_b64(header)}.{encode_b64(payload)}.{encode_b64(credentials.token)}"

        return jwt_token, credentials.expiry.timestamp()

    except Exception as e:
        logger.error(f"❌ Failed to get GCP IAM token: {e}")
        raise


class MQTTToKafkaIngestion:
    """Handles MQTT message consumption and Kafka publishing."""

    def __init__(self):
        """Initializes the MQTT client and GCP Kafka Producer."""

        # 1. INITIALIZE KAFKA PRODUCER FOR GCP
        kafka_conf = {
            "bootstrap.servers": settings_instance.KAFKA_BROKER,
            "security.protocol": "SASL_SSL",
            "sasl.mechanisms": "OAUTHBEARER",
            "oauth_cb": get_gcp_iam_token,  # Inject the token retrieval function here
            "client.id": "hsl-python-ingestion",
            # Optimization for high-throughput streaming (Optional)
            "linger.ms": 10,
            "batch.size": 16384,
        }
        self.producer = Producer(kafka_conf)
        logger.info("✅ GCP Kafka Producer initialized with OAUTHBEARER")

        # 2. INITIALIZE MQTT CLIENT
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.tls_set(cert_reqs=ssl.CERT_NONE)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        """Callback for MQTT connection events."""
        if reason_code == 0:
            try:
                logger.info(f"✅ Connected to MQTT via SSL (Code: {reason_code})")
                logger.info(f"📡 Subscribing to topic: {settings_instance.MQTT_TOPIC}")
                client.subscribe(settings_instance.MQTT_TOPIC)
            except Exception as e:
                logger.error(f"❌ Error occurred while subscribing to MQTT topic: {e}")
        else:
            logger.error(f"❌ MQTT connection failed, code: {reason_code}")

    def _on_message(self, client, userdata, msg):
        """Callback for when an MQTT message is received."""
        try:
            # Parse the MQTT payload
            payload = msg.payload.decode("utf-8")
            json_data = json.loads(payload)
            vp = json_data.get("VP", {})

            if vp:
                # Create a unique vehicle ID
                oper_id = str(vp.get("oper", "0"))
                veh_num = str(vp.get("veh", "0"))
                unique_veh_id = f"{oper_id}_{veh_num}"

                # Add the unique ID to the payload
                json_data["VP"]["unique_veh_id"] = unique_veh_id

                # Serialize data to bytes before sending to Kafka
                kafka_payload = json.dumps(json_data).encode("utf-8")
                kafka_key = unique_veh_id.encode("utf-8")

                # Publish data to Kafka
                self.producer.produce(
                    topic=settings_instance.KAFKA_TOPIC,
                    key=kafka_key,
                    value=kafka_payload,
                    on_delivery=self._delivery_report,
                )

                # Trigger poll() to serve delivery report callbacks (mandatory in confluent-kafka)
                self.producer.poll(0)

        except Exception as e:
            logger.error(f"❌ Error processing MQTT message: {e}")

    def _delivery_report(self, err, msg):
        """Callback to report the result of the Kafka produce request (Success/Failure)."""
        if err is not None:
            logger.error(f"❌ Kafka delivery failed: {err}")
        else:
            # Log at debug level to avoid flooding the terminal during high-speed ingestion
            logger.info(
                f"🚀 Sent to Kafka | Partition: {msg.partition()} | Offset: {msg.offset()}"
            )

    def start(self):
        """Starts the MQTT connection and the main message loop."""
        try:
            logger.info("⏳ Connecting to HSL MQTT broker via SSL...")
            self.client.connect(
                settings_instance.MQTT_BROKER, settings_instance.MQTT_PORT, 60
            )
            logger.info("🚀 Starting MQTT message loop...")
            self.client.loop_forever()
        except KeyboardInterrupt:
            logger.warning("\n🛑 Ingestion stopped by user.")
            self.stop()
        except Exception as e:
            logger.critical(f"💀 Fatal Error: {e}")
            raise

    def stop(self):
        """Stops the MQTT connection and flushes remaining Kafka messages."""
        try:
            self.client.disconnect()
            logger.info("⏳ Flushing remaining messages to Kafka...")
            # Wait up to 10 seconds to flush lingering messages in the buffer to Kafka
            self.producer.flush(10)
            logger.info("✅ Ingestion stopped cleanly")
        except Exception as e:
            logger.error(f"❌ Error stopping ingestion: {e}")


def main():
    """Main entry point for the ingestion script."""
    ingestion = MQTTToKafkaIngestion()
    ingestion.start()


if __name__ == "__main__":
    main()
