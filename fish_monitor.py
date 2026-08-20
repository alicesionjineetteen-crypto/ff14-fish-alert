import requests

r = requests.get(
    "https://mollysstudio.net/wp-admin/admin-ajax.php",
    params={
        "action": "big_fish_monitor_get_data",
        "version": "3.21"
    }
)

print("STATUS:", r.status_code)
print(r.text[:1000])
