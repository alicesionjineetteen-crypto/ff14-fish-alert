import requests

ITEM_ID = 33242  # Ealad Skaan / イラッド・スカーン
url = f"https://www.garlandtools.org/db/doc/fishing/ja/2/{ITEM_ID}.json"
resp = requests.get(url)
print(resp.status_code)
print(resp.json())
