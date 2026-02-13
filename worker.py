import os
import json
import redis
from google.cloud import pubsub_v1
from dotenv import load_dotenv

# 1. Cấu hình
load_dotenv()
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_client = redis.Redis(host=redis_host, port=6379, db=0, decode_responses=True)


# 2. Logic xử lý tin nhắn
def callback(message):
    try:
        data = json.loads(message.data.decode("utf-8"))
        vp = data.get("VP")

        if vp:
            # Tạo ID duy nhất
            oper_id = str(vp.get("oper", "0"))
            veh_num = str(vp.get("veh", "0"))
            unique_veh_id = f"{oper_id}_{veh_num}"
            new_tst = vp.get("tst", 0)

            old_data_str = redis_client.get(f"bus:{unique_veh_id}")
            if old_data_str:
                old_data = json.loads(old_data_str)
                old_tst = old_data.get("tst", 0)

                # Nếu dữ liệu cũ mới hơn, giữ nguyên timestamp cũ
                if old_tst >= new_tst:
                    message.ack()
                    return

            # --- GHI VÀO REDIS ---
            new_bus_data = {
                "lat": vp["lat"],
                "long": vp["long"],
                "hdg": vp.get("hdg", 0),
                "route": vp.get("desi", "?"),
                "tst": new_tst,
                "oper": oper_id,
            }

            # Ghi dữ liệu xe
            redis_client.set(f"bus:{unique_veh_id}", json.dumps(new_bus_data), ex=60)

        message.ack()
    except Exception:
        message.nack()


# 3. Chạy vòng lặp chính
def main():
    print("👷 Worker đang khởi động...")
    project_id = os.getenv("GCP_PROJECT_ID")
    subscription_id = os.getenv("GCP_SUBSCRIPTION_ID")

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_id)

    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    print(f"✅ Đang lắng nghe từ: {subscription_id}")

    try:
        streaming_pull_future.result()
    except KeyboardInterrupt:
        streaming_pull_future.cancel()


if __name__ == "__main__":
    main()
