/**
 * Discordにスラッシュコマンド(/デイリー /ウィークリー)を登録する、一度だけ実行するスクリプト。
 *
 * 使い方:
 *   DISCORD_TOKEN=xxxx DISCORD_APPLICATION_ID=xxxx node register-commands.js
 *
 * DISCORD_TOKEN: Discord Developer Portal の Bot タブで発行したトークン
 * DISCORD_APPLICATION_ID: 同じくDeveloper Portalの「General Information」にある Application ID
 *
 * コマンドの内容を変更したときは、このスクリプトをもう一度実行すれば上書き登録されます。
 * (Discord全体に反映されるまで最大1時間ほどかかる場合があります)
 */

const token = process.env.DISCORD_TOKEN;
const appId = process.env.DISCORD_APPLICATION_ID;

if (!token || !appId) {
  console.error("環境変数 DISCORD_TOKEN と DISCORD_APPLICATION_ID を設定してください");
  process.exit(1);
}

const commands = [
  {
    name: "デイリー",
    description: "本日分のヌシ・オオヌシ出現予定を今すぐ通知します",
    type: 1, // CHAT_INPUT
  },
  {
    name: "ウィークリー",
    description: "今週分のオオヌシ出現予定を今すぐ通知します",
    type: 1,
  },
];

const res = await fetch(`https://discord.com/api/v10/applications/${appId}/commands`, {
  method: "PUT",
  headers: {
    "Authorization": `Bot ${token}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify(commands),
});

const text = await res.text();
console.log(res.status, text);

if (!res.ok) {
  process.exit(1);
}
console.log("コマンドの登録が完了しました。");
