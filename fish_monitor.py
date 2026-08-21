"""
ヌシ・オオヌシ 出現スケジュール監視 & Discord通知

使い方:
  python fish_monitor.py daily   -> 未取得の「ヌシ」「オオヌシ」について、今から24時間以内の出現を通知
  python fish_monitor.py weekly  -> 未取得の「オオヌシ」について、今から7日以内の出現を通知(週間の予定立て用)

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


def fish_by_name(fish_list, name):
    for f in fish_list:
        if f["name"] == name:
            return f
    return None


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
                et_fish_start = et_day_base.replace(hour=block_hour)
                et_fish_end = et_fish_start + datetime.timedelta(hours=8, seconds=-1)

            real_begin = et_to_real(et_fish_start)
            real_end = et_to_real(et_fish_end)

            if real_end >= scan_start and real_begin <= scan_end:
                results.append((max(real_begin, scan_start), min(real_end, scan_end)))

        p += PERIOD

    return results


def format_occurrences(occurrences, limit=None):
    lines = []
    shown = occurrences[:limit] if limit else occurrences
    for begin, end in shown:
        b = begin.astimezone(JST)
        lines.append(f"　・{b.strftime('%m/%d(%a) %H:%M')}〜")
    if limit and len(occurrences) > limit:
        lines.append(f"　　...他 {len(occurrences) - limit} 回")
    return lines


def format_fish_block(fish, occurrences, indent="", limit=None):
    """魚1匹分の情報(条件・釣り方・スケジュール)をテキストブロックにする"""
    lines = []
    lines.append(f"{indent}【{fish['name']}】{fish['zone_jp']} {fish['point']}")
    lines.append(f"{indent}時刻: {fish['time_raw'] or '指定なし'} / 天候: {fish['weather_raw']}")
    if fish["method_lines"]:
        lines.append(f"{indent}釣り方:")
        for m in fish["method_lines"]:
            lines.append(f"{indent}　{m}")
    if not occurrences:
        lines.append(f"{indent}(該当なし)")
    else:
        lines.extend(f"{indent}{l}" for l in format_occurrences(occurrences, limit=limit))
    return "\n".join(lines)


def build_report(fish_types, days_ahead, title):
    fish_list = load_fish()
    now = datetime.datetime.now(datetime.timezone.utc)
    scan_end = now + datetime.timedelta(days=days_ahead)

    blocks = []
    for fish in fish_list:
        if fish["type"] not in fish_types:
            continue
        if fish.get("caught"):
            continue
        if fish["weather"] is not None and fish["zone_en"] not in WEATHER_RATES:
            continue  # ゾーン未対応(データ不足)は安全のためスキップ

        occurrences = scan_fish(fish, now, scan_end)
        if not occurrences:
            continue

        block = format_fish_block(fish, occurrences)

        # 前提の魚がいれば、その魚自身のスケジュールも合わせて載せる
        for prereq_name in fish.get("prerequisites", []):
            prereq = fish_by_name(fish_list, prereq_name)
            if prereq is None:
                continue
            prereq_occ = scan_fish(prereq, now, scan_end)
            prereq_block = format_fish_block(prereq, prereq_occ, indent="　", limit=5)
            block += f"\n\n　※前提: {prereq_name}\n{prereq_block}"

        blocks.append(block)

    if not blocks:
        return f"{title}\n\n該当する魚は見つかりませんでした。"
    return f"{title}\n\n" + "\n\n----------\n\n".join(blocks)


def send_discord(content: str):
    webhook = os.environ["DISCORD_WEBHOOK"]
    chunk = ""
    for line in content.split("\n"):
        if len(chunk) + len(line) + 1 > 1900:
            requests.post(webhook, json={"content": chunk})
            chunk = ""
        chunk += line + "\n"
    if chunk.strip():
        requests.post(webhook, json={"content": chunk})


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "daily"

    if mode == "daily":
        content = build_report(
            ["ヌシ", "オオヌシ"], 1,
            "🐟 本日の未取得ヌシ・オオヌシ出現予定(24時間以内)",
        )
    elif mode == "weekly":
        content = build_report(
            ["オオヌシ"], 7,
            "🐋 今週の未取得オオヌシ出現予定(7日以内・予定立て用)",
        )
    else:
        print("Usage: python fish_monitor.py [daily|weekly]")
        sys.exit(1)

    print(content)
    send_discord(content)


if __name__ == "__main__":
    main()
