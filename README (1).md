# Discordスラッシュコマンド → GitHub Actions 起動Bot(Cloudflare Workers)

Discordで `/デイリー` `/ウィークリー` と打つと、即座にこのWorkerが受け取り、
GitHub Actions(`repository_dispatch`)を起動します。実際のヌシ・オオヌシ計算と
Discordへの通知は、これまで通り本体リポジトリの `fish_monitor.py` が行います。

常時起動のサーバーは不要です(Cloudflare Workersはリクエストが来たときだけ動く
サーバーレスな仕組みで、無料枠で十分に足ります)。

## 全体の流れ
```
Discordで /デイリー と入力
   ↓ (Discordが即座にこのWorkerへPOST)
Cloudflare Worker: 署名を検証 → GitHubへ repository_dispatch を送信 → 即座に「開始しました」と返信
   ↓
GitHub Actions: fish_monitor.py daily を実行 → Discordの別チャンネル(Webhook)へ結果を投稿
```

## 事前準備
- Node.js (18以上推奨)
- Cloudflareの無料アカウント
- Discord Developer Portal (https://discord.com/developers/applications) でのアプリ作成権限
- GitHubの対象リポジトリへの書き込み権限

## セットアップ手順

### 1. Discordアプリケーションの作成
1. https://discord.com/developers/applications で「New Application」から作成
2. 「General Information」タブの **Application ID** と **Public Key** を控える
   (Public Key は後で `DISCORD_PUBLIC_KEY` として使います)
3. 「Bot」タブでBotを追加し、トークンを発行(これが `DISCORD_TOKEN`。コマンド登録の
   一度きりの作業にのみ使います)
4. 「OAuth2 > URL Generator」で scope に `bot` と `applications.commands` を選び、
   権限は `Send Messages` を付与。生成されたURLからBotをサーバーに招待

### 2. このフォルダ(cloudflare-worker)をセットアップ
```bash
cd cloudflare-worker
npm install
npx wrangler login   # Cloudflareアカウントでログイン
```

`wrangler.toml` の `GITHUB_OWNER` / `GITHUB_REPO` を、実際のGitHubユーザー名・
リポジトリ名に書き換えてください。

秘密情報(このファイルには書かない)を登録します:
```bash
npx wrangler secret put DISCORD_PUBLIC_KEY
# → 手順1で控えた Public Key を貼り付け

npx wrangler secret put GITHUB_TOKEN
# → 下記「3. GitHubトークンの発行」で作成したトークンを貼り付け
```

### 3. GitHubトークンの発行
GitHubの Settings > Developer settings > Fine-grained personal access tokens で、
対象リポジトリのみにアクセスできるトークンを発行してください。
- Repository access: 対象リポジトリのみを選択
- Permissions: **Contents: Read and write**(`repository_dispatch` の実行に必要)

発行したトークンを、上記の `wrangler secret put GITHUB_TOKEN` で登録します。

### 4. Workerのデプロイ
```bash
npx wrangler deploy
```
デプロイ完了後に表示される `https://xxxx.workers.dev` のURLを控えます。

### 5. DiscordにWorkerのURLを登録
Discord Developer Portal の該当アプリ →「General Information」→
**Interactions Endpoint URL** に、手順4のURLを貼り付けて保存してください。
(署名検証が通らないと保存自体が失敗するので、うまく保存できればWorker側の設定は
正しく完了しています)

### 6. スラッシュコマンドの登録
```bash
DISCORD_TOKEN=xxxx DISCORD_APPLICATION_ID=xxxx node register-commands.js
```
初回反映まで最大1時間ほどかかることがあります。反映されたら、Discordのチャンネルで
`/デイリー` `/ウィークリー` と入力すると候補として表示されるようになります。

## 動作確認
Discordで `/デイリー` を実行し、
1. すぐに「レポート作成を開始しました」という返信が来る
2. 数十秒〜1分程度で、Webhook経由のチャンネルにヌシ・オオヌシのレポートが届く

の両方が確認できればOKです。GitHub Actionsの実行状況は、リポジトリの Actions タブ
→ "FF14 Fish Alert" → `discord-command` ジョブから確認できます。

## トラブルシューティング
- Discord側で「Interactions Endpoint URLの保存に失敗する」→ `DISCORD_PUBLIC_KEY` の
  設定ミス、またはWorkerがデプロイされていない可能性があります
- コマンドを打っても反応がない → コマンド登録後の反映待ち、またはBotがサーバーに
  招待されていない可能性があります
- 「開始しました」とは返るがレポートが届かない → `GITHUB_TOKEN` の権限不足、または
  `wrangler.toml` の `GITHUB_OWNER`/`GITHUB_REPO` の誤りが考えられます。GitHubの
  Actionsタブでワークフローが起動しているか確認してください
