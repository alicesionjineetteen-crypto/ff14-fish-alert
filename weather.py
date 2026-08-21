"""
FFXIV エオルゼア天候の計算モジュール。

アルゴリズムの出典:
  https://github.com/xivapi/ffxiv-datamining/blob/master/docs/Weather.md
天候テーブル(WeatherRate)の出典:
  https://github.com/Asvel/ffxiv-weather/blob/master/src/Weather.ts
どちらも公開されているゲームデータ解析情報で、外部サイトへのアクセスは不要。
"""

import datetime

# 各ゾーンの天候テーブル。[天候名, 累積しきい値, 天候名, 累積しきい値, ..., 最後の天候名]
# target(0-99) がしきい値未満なら対応する天候。最後の要素はしきい値なし(残り全部)。
WEATHER_RATES = {
    "Il Mheg": ["Rain", 10, "Fog", 20, "Clouds", 35, "Thunderstorms", 45, "Clear Skies", 60, "Fair Skies"],
    "The Tempest": ["Clouds", 20, "Fair Skies", 80, "Clear Skies"],
    "Ultima Thule": ["Astromagnetic Storms", 15, "Fair Skies", 85, "Umbral Wind"],
    "Urqopacha": ["Clear Skies", 20, "Fair Skies", 50, "Clouds", 70, "Fog", 80, "Wind", 90, "Snow"],
    "Kozama'uka": ["Clear Skies", 25, "Fair Skies", 60, "Clouds", 75, "Fog", 85, "Rain", 95, "Showers"],
    "Yak T'el": ["Clear Skies", 15, "Fair Skies", 55, "Clouds", 70, "Fog", 85, "Rain"],
    "Shaaloani": ["Clear Skies", 5, "Fair Skies", 50, "Clouds", 70, "Dust Storms", 85, "Gales"],
    "Heritage Found": ["Fair Skies", 5, "Clouds", 25, "Fog", 40, "Rain", 45, "Thunderstorms", 50, "Umbral Static"],
    "Living Memory": ["Rain", 10, "Fog", 20, "Clouds", 40, "Fair Skies"],
}

EORZEA_RATIO = 3600 / 175  # 1 real sec = 20.5714... eorzea sec
PERIOD = 8 * 175  # 1天候ブロック=ET8時間=リアル1400秒


def calc_forecast_target(unix_seconds: int) -> int:
    bell = unix_seconds // 175
    increment = (bell + 8 - (bell % 8)) % 24
    total_days = (unix_seconds // 4200) & 0xFFFFFFFF
    calc_base = (total_days * 100 + increment) & 0xFFFFFFFF
    step1 = (((calc_base << 11) & 0xFFFFFFFF) ^ calc_base) & 0xFFFFFFFF
    step2 = ((step1 >> 8) ^ step1) & 0xFFFFFFFF
    return step2 % 100


def weather_for_target(zone: str, target: int) -> str:
    table = WEATHER_RATES[zone]
    for i in range(0, len(table) - 1, 2):
        name, threshold = table[i], table[i + 1]
        if target < threshold:
            return name
    return table[-1]


def period_weather(period_start_unix: int, zone: str) -> str:
    target = calc_forecast_target(int(period_start_unix))
    return weather_for_target(zone, target)


def real_to_eorzea(dt_utc: datetime.datetime) -> datetime.datetime:
    epoch = dt_utc.timestamp()
    et_epoch = int(epoch * EORZEA_RATIO)
    return datetime.datetime.fromtimestamp(et_epoch, tz=datetime.timezone.utc)


def et_to_real(et_dt: datetime.datetime) -> datetime.datetime:
    et_epoch = et_dt.timestamp()
    real_epoch = et_epoch / EORZEA_RATIO
    return datetime.datetime.fromtimestamp(real_epoch, tz=datetime.timezone.utc)
