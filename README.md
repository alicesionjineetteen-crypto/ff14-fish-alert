# FF14 ヌシ・オオヌシ 監視Bot

## セットアップ
1. このフォルダの中身をリポジトリのルートに配置
   (`.github/workflows/fish_alert.yml` はそのままのパスで配置してください)
2. リポジトリの Settings > Secrets and variables > Actions で
   `DISCORD_WEBHOOK` を登録(Discordの通知先Webhook URL)
3. これでOK。以降は自動で
   - 毎日 朝7:00(JST): 未取得「ヌシ」「オオヌシ」の24時間以内の出現予定(当日行けるかどうか用)
   - 毎週月曜 朝7:00(JST): 未取得「オオヌシ」の7日以内の出現予定(週間の予定立て用)
   がDiscordに通知されます。

各魚の通知には、釣り場・時刻・天候に加えて「釣り方」(必要な餌・あたりの種類[ストロング
フッキング/プレシジョンフッキング]など)もそのまま記載されます。また、前提となる魚
(例: ミズウオ→モラ・テクタ、スターホエール→パライナ、三刃の鯱→ブライトカッパー
シャーク、ロネークポリプテルス→ドクトー)がいる場合は、その前提の魚自身の出現予定も
合わせて表示されます(前提の魚は表示が長くなりすぎないよう直近5回までに絞っています)。

## 魚を釣ったら
`fish_conditions.json` の該当の魚の `"caught": false` を `"caught": true` に書き換えて
コミットしてください。以降その魚は通知対象から除外されます。

## 動作確認・手動実行
GitHub の Actions タブ → "FF14 Fish Alert" → "Run workflow" から
daily/weekly を選んで手動実行できます。

ローカルで試す場合:
```
pip install -r requirements.txt
export DISCORD_WEBHOOK="https://discord.com/api/webhooks/xxxx"
python fish_monitor.py daily
python fish_monitor.py weekly
```

## 天候計算の仕組み・出典
- 天候決定アルゴリズム: https://github.com/xivapi/ffxiv-datamining/blob/master/docs/Weather.md
- 各ゾーンの天候テーブル: https://github.com/Asvel/ffxiv-weather (data オブジェクト)
どちらも公開されているゲームデータ解析情報で、外部サイトへの都度アクセスは不要です。
実装した天候計算は、既知の「イラッド・スカーン」の出現日時と突き合わせて検証済みです。

## 魚を追加したい場合
`fish_conditions.json` に以下の形式で1件追加してください。

```json
{
  "name": "魚の名前",
  "type": "ヌシ",            // "ヌシ" or "オオヌシ"
  "zone_jp": "表示用ゾーン名(日本語)",
  "zone_en": "Il Mheg",       // weather.py の WEATHER_RATES キーと一致させる
  "point": "釣り場名",
  "start_hm": [23, 30],       // ET開始 [時,分]。時刻指定なしなら null
  "end_hm": [23, 59],
  "weather": "Clear Skies",   // 天候指定なしなら null。英語表記で weather.py のテーブルに合わせる
  "prev_weather": "Thunderstorms", // 前天候の指定がなければ null
  "note": "釣り方メモ",
  "caught": false
}
```
新しいゾーンを追加する場合は `weather.py` の `WEATHER_RATES` にもそのゾーンの
天候テーブルを追加する必要があります(Asvel/ffxiv-weather の該当ゾーンをコピー)。
