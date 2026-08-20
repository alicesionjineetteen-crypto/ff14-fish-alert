import os
import requests

webhook = os.environ["DISCORD_WEBHOOK"]

message = {
    "content": "✅ FF14 Fish Monitor テスト通知"
}

requests.post(webhook, json=message)

print("sent")
``
