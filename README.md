# FF14 ヌシ・オオヌシ 監視Bot

## セットアップ
1. このフォルダの中身をリポジトリのルートに配置
   (`.github/workflows/fish_alert.yml` はそのままのパスで配置してください)
2. リポジトリの Settings > Secrets and variables > Actions で
   `DISCORD_WEBHOOK` を登録(Discordの通知先Webhook URL)
3. Discordのスラッシュコマンド(`/デイリー` `/ウィークリー`)で手動実行したい場合は、
   `cloudflare-worker/README.md` の手順に沿ってセットアップしてください
   (セットアップしない場合、自動の定期通知だけが動作します)
4. これでOK。以降は自動で
   - **平日** 夜19:00(JST): 未取得「ヌシ」「オオヌシ」の**向こう6時間以内**の出現予定
   - **土日祝** 朝7:00(JST): 未取得「ヌシ」「オオヌシ」の**24時間以内**の出現予定(従来通り)
   - 毎週月曜 朝7:00(JST): 未取得「オオヌシ」の7日以内の出現予定(週間の予定立て用、変更なし)

   がDiscordに通知されます。祝日判定には `jpholiday` ライブラリ(内蔵の祝日データ、外部
   通信なし)を使用しています。

## Discordスラッシュコマンドでの手動実行
Discordで `/デイリー` または `/ウィークリー` と打つと、即座にGitHub Actionsが起動し、
その場でレポートを実行してDiscordに投稿します。

Cloudflare Workers(サーバーレス。常時起動のサーバーは不要で、無料枠で足ります)が
Discordからのリクエストを即時に受け取り、GitHub Actionsの `repository_dispatch` を
呼び出す仕組みです。コマンドを打ってから数秒で「開始しました」と返信があり、その後
数十秒〜1分程度でレポートがDiscordに届きます。

セットアップ手順の詳細は `cloudflare-worker/README.md` を参照してください
(Discordアプリの作成、Cloudflare Workerのデプロイ、GitHubトークンの発行などが
必要です)。

補足:
- 通常の定期通知(平日夜19時/土日祝朝7時/週次)はこの手動実行の設定がなくても
  そのまま動作します。スラッシュコマンドはあくまで「今すぐ見たい」ときの追加機能です

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
以下のモードを選んで手動実行できます。
- `daily`: 曜日を問わず24時間以内を通知
- `daily-morning`: 朝枠と同じロジック(土日祝のみ実際に通知、平日はスキップ)
- `daily-evening`: 夜枠と同じロジック(平日のみ実際に通知、土日祝はスキップ)
- `weekly`: 7日以内のオオヌシを通知

ローカルで試す場合:
```
pip install -r requirements.txt
export DISCORD_WEBHOOK="https://discord.com/api/webhooks/xxxx"
python fish_monitor.py daily
python fish_monitor.py daily-morning
python fish_monitor.py daily-evening
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
