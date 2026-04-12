"""Kafka ingestion module for MQTT data"""

import json
import paho.mqtt.client as mqtt
import ssl

from hsl_common import get_settings_instance, get_logger_instance
from hsl_common.kafka_service import get_kafka_service

settings_instance = get_settings_instance()
logger = get_logger_instance(__name__)


class MQTTToKafkaIngestion:
    """Handle MQTT message consumption and Kafka publishing"""

    def __init__(self):
        """Initialize MQTT client and Kafka service"""
        self.kafka_service = get_kafka_service()
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.tls_set(cert_reqs=ssl.CERT_NONE)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        """Callback for MQTT connection"""
        if reason_code == 0:
            try:
                logger.info(f"✅ Connected to MQTT via SSL (Code: {reason_code})")
                logger.info(f"📡 Subscribing to: {settings_instance.MQTT_TOPIC}")
                client.subscribe(settings_instance.MQTT_TOPIC)
            except Exception as e:
                logger.error(f"❌ Error occurred while connecting to MQTT: {e}")
        else:
            logger.error(f"❌ MQTT connection failed, code: {reason_code}")

    def _on_message(self, client, userdata, msg):
        """Callback for MQTT message received"""
        try:
            # Parse MQTT payload
            payload = msg.payload.decode("utf-8")
            json_data = json.loads(payload)
            vp = json_data.get("VP", {})

            if vp:
                # Create unique vehicle ID
                oper_id = str(vp.get("oper", "0"))
                veh_num = str(vp.get("veh", "0"))
                unique_veh_id = f"{oper_id}_{veh_num}"

                # Add unique ID to data
                json_data["VP"]["unique_veh_id"] = unique_veh_id

                # Send to Kafka
                self.kafka_service.send_message(
                    value=json_data,
                    key=unique_veh_id,
                    on_success=self._on_kafka_success,
                    on_error=self._on_kafka_error,
                )
        except Exception as e:
            logger.error(f"❌ Error processing MQTT message: {e}")

    def _on_kafka_success(self, record_metadata):
        """Callback for successful Kafka send"""
        logger.info(
            f"🚀 Sent to Kafka | Partition: {record_metadata.partition} | "
            f"Offset: {record_metadata.offset}"
        )

    def _on_kafka_error(self, exc):
        """Callback for Kafka send error"""
        logger.error(f"❌ Kafka error: {exc}")

    def start(self):
        """Start MQTT connection and message loop"""
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
        """Stop MQTT connection and clean up"""
        try:
            self.client.disconnect()
            self.kafka_service.flush()
            self.kafka_service.close()
            logger.info("✅ Ingestion stopped cleanly")
        except Exception as e:
            logger.error(f"❌ Error stopping ingestion: {e}")


def main():
    """Main entry point for ingestion"""
    ingestion = MQTTToKafkaIngestion()
    ingestion.start()


if __name__ == "__main__":
    main()
