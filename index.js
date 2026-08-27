/**
 * Discordのスラッシュコマンド(/デイリー /ウィークリー)を受け取り、
 * GitHub Actionsの repository_dispatch を叩いて起動するCloudflare Worker。
 *
 * 常時稼働のサーバーは不要。Discordからのリクエストが来たときだけ実行される。
 */
import { verifyKey, InteractionType, InteractionResponseType } from "discord-interactions";

// Discordのコマンド名 -> GitHub repository_dispatch の event_type
const COMMAND_TO_EVENT_TYPE = {
  "デイリー": "discord-daily",
  "ウィークリー": "discord-weekly",
};

export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return new Response("FF14 Fish Alert Discord bot is running.", { status: 200 });
    }

    const signature = request.headers.get("x-signature-ed25519");
    const timestamp = request.headers.get("x-signature-timestamp");
    const body = await request.text();

    if (!signature || !timestamp) {
      return new Response("署名ヘッダーがありません", { status: 401 });
    }

    const isValid = await verifyKey(body, signature, timestamp, env.DISCORD_PUBLIC_KEY);
    if (!isValid) {
      return new Response("署名検証に失敗しました", { status: 401 });
    }

    const interaction = JSON.parse(body);

    // Discordの疎通確認(初回登録時などに飛んでくる)
    if (interaction.type === InteractionType.PING) {
      return jsonResponse({ type: InteractionResponseType.PONG });
    }

    if (interaction.type === InteractionType.APPLICATION_COMMAND) {
      const commandName = interaction.data.name;
      const eventType = COMMAND_TO_EVENT_TYPE[commandName];

      if (!eventType) {
        return jsonResponse({
          type: InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
          data: { content: `未対応のコマンドです: ${commandName}` },
        });
      }

      // GitHub Actions側のレスポンスは待たず、応答だけ即座に返す
      // (Discordは3秒以内に応答しないとエラー表示になるため)
      let replyText = `「${commandName}」のレポート作成を開始しました🎣 まもなくこのチャンネルに届きます。`;
      try {
        await dispatchToGitHub(env, eventType);
      } catch (err) {
        console.error(err);
        replyText = `GitHubへの起動リクエストに失敗しました: ${err.message}`;
      }

      return jsonResponse({
        type: InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
        data: { content: replyText },
      });
    }

    return new Response("未対応のinteraction typeです", { status: 400 });
  },
};

async function dispatchToGitHub(env, eventType) {
  const url = `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/dispatches`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${env.GITHUB_TOKEN}`,
      "Accept": "application/vnd.github+json",
      "User-Agent": "ff14-fish-alert-discord-bot",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ event_type: eventType }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`GitHub dispatch failed (${res.status}): ${text}`);
  }
}

function jsonResponse(obj) {
  return new Response(JSON.stringify(obj), {
    headers: { "content-type": "application/json" },
  });
}
