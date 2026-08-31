"""
ヌシ・オオヌシ 出現スケジュール監視 & Discord通知

使い方:
  python fish_monitor.py daily-morning -> 土日祝の朝7時用。平日なら何もせず終了。24時間以内を通知。
  python fish_monitor.py daily-evening -> 平日の夜18時用。土日祝なら何もせず終了。向こう7時間以内を通知。
  python fish_monitor.py daily         -> 曜日を問わず、今から24時間以内を通知(手動実行・Discordコマンド用)
  python fish_monitor.py weekly        -> 未取得の「オオヌシ」について、今から7日以内の出現を通知(週間の予定立て用)

Discordから「/デイリー」「/ウィークリー」と打つと、Cloudflare Workers経由でGitHub Actionsの
repository_dispatchが発火し、このスクリプトが daily / weekly モードで即座に実行されます。
(詳細は cloudflare-worker/README.md を参照)

fish_conditions.json の "caught": true にした魚は通知対象から除外されます。
"""

import sys
import os
import json
import datetime
import requests
import jpholiday

from weather import (
    period_weather, real_to_eorzea, et_to_real, PERIOD, WEATHER_RATES,
)

JST = datetime.timezone(datetime.timedelta(hours=9))
HERE = os.path.dirname(os.path.abspath(__file__))


def is_business_day(date: datetime.date) -> bool:
    """平日(月〜金)かつ日本の祝日でなければ True"""
    if date.weekday() >= 5:  # 5=土, 6=日
        return False
    if jpholiday.is_holiday(date):
        return False
    return True


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
        lines.append(f" ・{b.strftime('%m/%d(%a) %H:%M')}〜")
    if limit and len(occurrences) > limit:
        lines.append(f"  ...他 {len(occurrences) - limit} 回")
    return lines


def format_fish_block(fish, occurrences, indent="", limit=None):
    """魚1匹分の情報(条件・釣り方・スケジュール)をテキストブロックにする"""
    lines = []
    lines.append(f"{indent}【{fish['name']}】{fish['zone_jp']} {fish['point']}")
    lines.append(f"{indent}時刻: {fish['time_raw'] or '指定なし'} / 天候: {fish['weather_raw']}")
    if fish["method_lines"]:
        lines.append(f"{indent}釣り方:")
        for m in fish["method_lines"]:
            lines.append(f"{indent} {m}")
    if not occurrences:
        lines.append(f"{indent}(該当なし)")
    else:
        lines.extend(f"{indent}{l}" for l in format_occurrences(occurrences, limit=limit))
    return "\n".join(lines)


def build_report(fish_types, title, days_ahead=None, hours_ahead=None):
    """
    days_ahead / hours_ahead のどちらか一方を指定する。
    (例: days_ahead=1 なら24時間以内、hours_ahead=7 なら7時間以内)
    """
    fish_list = load_fish()
    now = datetime.datetime.now(datetime.timezone.utc)
    if hours_ahead is not None:
        scan_end = now + datetime.timedelta(hours=hours_ahead)
    else:
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
            prereq_block = format_fish_block(prereq, prereq_occ, indent=" ", limit=5)
            block += f"\n\n ※前提: {prereq_name}\n{prereq_block}"

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


def run_daily(hours_ahead=None, days_ahead=None, suffix=""):
    if hours_ahead is not None:
        title = f"🐟 本日の未取得ヌシ・オオヌシ出現予定(向こう{hours_ahead}時間以内){suffix}"
    else:
        title = f"🐟 本日の未取得ヌシ・オオヌシ出現予定(24時間以内){suffix}"
    content = build_report(
        ["ヌシ", "オオヌシ"], title,
        days_ahead=days_ahead, hours_ahead=hours_ahead,
    )
    print(content)
    send_discord(content)


def run_weekly(suffix=""):
    content = build_report(
        ["オオヌシ"], f"🐋 今週の未取得オオヌシ出現予定(7日以内・予定立て用){suffix}",
        days_ahead=7,
    )
    print(content)
    send_discord(content)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "daily"
    today_jst = datetime.datetime.now(JST).date()

    if mode == "daily-morning":
        # 土日祝の朝7時枠。平日はここでは何もしない(夜枠が担当)
        if is_business_day(today_jst):
            print("平日のため朝の通知はスキップします(夜19時に通知します)")
            return
        run_daily(days_ahead=1)

    elif mode == "daily-evening":
        # 平日の夜18時枠。土日祝はここでは何もしない(朝枠が担当)
        if not is_business_day(today_jst):
            print("土日祝のため夜の通知はスキップします(朝に通知済みです)")
            return
        run_daily(hours_ahead=7)

    elif mode == "daily":
        # 曜日を問わず24時間以内を通知(手動実行 / Discordコマンド[repository_dispatch]用)
        suffix = "・Discordコマンド実行" if os.environ.get("GITHUB_EVENT_NAME") == "repository_dispatch" else ""
        run_daily(days_ahead=1, suffix=suffix)

    elif mode == "weekly":
        suffix = "・Discordコマンド実行" if os.environ.get("GITHUB_EVENT_NAME") == "repository_dispatch" else ""
        run_weekly(suffix=suffix)

    else:
        print("Usage: python fish_monitor.py [daily-morning|daily-evening|daily|weekly]")
        sys.exit(1)


if __name__ == "__main__":
    main()
  
