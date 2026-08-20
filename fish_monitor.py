import os
import requests

data = requests.get(
    "https://mollysstudio.net/wp-admin/admin-ajax.php",
    params={
        "action": "big_fish_monitor_get_data",
        "version": "3.21"
    }
).json()

count = len(data["fishes"])

requests.post(
    os.environ["DISCORD_WEBHOOK"],
    json={
        "content": f"魚データ取得成功: {count}件"
    }
)
