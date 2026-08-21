"""
ヌシ・オオヌシ 出現スケジュール監視 & Discord通知

使い方:
  python fish_monitor.py daily   -> 未取得の「ヌシ」について、今から24時間以内の出現を通知
  python fish_monitor.py weekly  -> 未取得の「オオヌシ」について、今から7日以内の出現を通知

fish_conditions.json の "caught": true にした魚は通知対象から除外されます。
"""

import sys
import os
import json
import datetime
import requests

from weather import (
    period_weather, real_to_eorzea, et_to_real, PERIOD, WEATHER_RATES,
)

JST = datetime.timezone(datetime.timedelta(hours=9))
HERE = os.path.dirname(os.path.abspath(__file__))


def load_fish():
    with open(os.path.join(HERE, "fish_conditions.json"), encoding="utf-8") as f:
        return json.load(f)


def scan_fish(fish, scan_start, scan_end):
    """指定した魚が scan_start〜scan_end の間に出現する時間帯のリストを返す"""
    zone = fish["zone_en"]
    start_hm = fish["start_hm"]
    end_hm = fish["end_hm"]
    weather = fish["weather"]
    prev_weather = fish["prev_weather"]

    results = []
    p = int(scan_start.timestamp() // PERIOD) * PERIOD
    end_ts = scan_end.timestamp()

    while p < end_ts:
        period_start_dt = datetime.datetime.fromtimestamp(p, tz=datetime.timezone.utc)
        et_start = real_to_eorzea(period_start_dt)
        block_hour = et_start.hour  # 0, 8, 16 のいずれか

        # 時刻指定がある場合は、その魚の時間帯が属するブロックのみ対象
        if start_hm is not None:
            fish_block = (start_hm[0] // 8) * 8
            if block_hour != fish_block:
                p += PERIOD
                continue

        cur_w = period_weather(p, zone)
        prev_w = period_weather(p - PERIOD, zone)

        weather_ok = (weather is None) or (cur_w == weather)
        prev_ok = (prev_weather is None) or (prev_w == prev_weather)

        if weather_ok and prev_ok:
            et_day_base = et_start.replace(hour=0, minute=0, second=0, microsecond=0)
            if start_hm is not None:
                et_fish_start = et_day_base.replace(hour=start_hm[0], minute=start_hm[1])
                et_fish_end = et_day_base.replace(hour=end_hm[0], minute=end_hm[1], second=59)
            else:
                # 時刻指定なし=このブロック全体(8ET時間)が対象
                et_fish_start = et_day_base.replace(hour=block_hour)
                et_fish_end = et_fish_start + datetime.timedelta(hours=8, seconds=-1)

            real_begin = et_to_real(et_fish_start)
            real_end = et_to_real(et_fish_end)

            # スキャン範囲内に収まる部分だけ採用
            if real_end >= scan_start and real_begin <= scan_end:
                results.append((max(real_begin, scan_start), min(real_end, scan_end)))

        p += PERIOD

    return results


def build_report(fish_type, days_ahead):
    fish_list = load_fish()
    now = datetime.datetime.now(datetime.timezone.utc)
    scan_end = now + datetime.timedelta(days=days_ahead)

    lines = []
    for fish in fish_list:
        if fish["type"] != fish_type:
            continue
        if fish.get("caught"):
            continue
        if fish["zone_en"] not in WEATHER_RATES and fish["weather"] is not None:
            continue  # ゾーン未対応(データ不足)は安全のためスキップ

        occurrences = scan_fish(fish, now, scan_end)
        if not occurrences:
            continue

        times_str = []
        for begin, end in occurrences:
            b = begin.astimezone(JST)
            times_str.append(f"{b.strftime('%m/%d(%a) %H:%M')}〜")

        lines.append(
            f"**{fish['name']}**（{fish['zone_jp']} {fish['point']}）\n"
            + "\n".join(f"　・{t}" for t in times_str)
        )

    return lines


def send_discord(content: str):
    webhook = os.environ["DISCORD_WEBHOOK"]
    # Discordの1メッセージ2000文字制限に合わせて分割送信
    chunk = ""
    for line in content.split("\n\n"):
        if len(chunk) + len(line) + 2 > 1900:
            requests.post(webhook, json={"content": chunk})
            chunk = ""
        chunk += line + "\n\n"
    if chunk.strip():
        requests.post(webhook, json={"content": chunk})


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "daily"

    if mode == "daily":
        lines = build_report("ヌシ", 1)
        title = "🐟 本日の未取得ヌシ出現予定(24時間以内)"
    elif mode == "weekly":
        lines = build_report("オオヌシ", 7)
        title = "🐋 今週の未取得オオヌシ出現予定(7日以内)"
    else:
        print("Usage: python fish_monitor.py [daily|weekly]")
        sys.exit(1)

    if not lines:
        content = f"{title}\n\n該当する魚は見つかりませんでした。"
    else:
        content = f"{title}\n\n" + "\n\n".join(lines)

    print(content)
    send_discord(content)


if __name__ == "__main__":
    main()
