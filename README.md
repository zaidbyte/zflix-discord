# zflix-discord

A Discord bot that answers questions about **zflix.me** using a free AI API (Groq).
It replies when you `@mention` it, when you reply to one of its messages, or when
you DM it. Conversation context is built by walking up the Discord reply chain.

## How it works

- `main.py` — main bot (uses `discord.py` + `groq`).
- `site_context.md` — what the bot knows about your site. **Edit this** before
  shipping; it's injected into the AI's system prompt at startup.
- `requirements.txt` — Python deps.
- `.env.example` — env vars template.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in DISCORD_TOKEN and GROQ_API_KEY in .env
python main.py
```

## Discord setup

1. Go to https://discord.com/developers/applications and create an application.
2. Under **Bot**, click **Reset Token** and copy it into `DISCORD_TOKEN`.
3. Enable the **MESSAGE CONTENT INTENT** toggle on that same page (required so the
   bot can read message text it's mentioned in).
4. Under **OAuth2 → URL Generator**, select scopes `bot` and `applications.commands`,
   and bot permissions: `Send Messages`, `Read Message History`, `Embed Links`,
   `Use External Emojis`. Open the generated URL to invite the bot to your server.

## Groq setup

1. Sign up at https://console.groq.com (free).
2. Create an API key at https://console.groq.com/keys.
3. Put it in `GROQ_API_KEY`.

Default model is `llama-3.3-70b-versatile`. Switch via `GROQ_MODEL` env var if
you hit rate limits — `llama-3.1-8b-instant` is faster/cheaper.

## Deploy on Wispbyte

1. Create a new **Python Generic** server in your Wispbyte panel.
2. In the file manager (or SFTP), pull this repo into the server. From the
   console: `git clone https://github.com/zaidbyte/zflix-discord.git .`
   (the default startup command will `git pull` on each restart).
3. Create a `.env` file in the server root with:
   ```
   DISCORD_TOKEN=your_discord_bot_token
   GROQ_API_KEY=your_groq_api_key
   ```
   The bot loads these via `python-dotenv` at startup.
4. The default Python Generic startup runs `main.py` and auto-installs
   `requirements.txt` — no changes needed. Just start the server.
5. Check the console for `Logged in as ...`.

## Usage

In any channel the bot can see:

- **Mention:** `@zflix-bot how do I sign up?`
- **Reply:** Reply to any message the bot sent — it'll keep context from the chain.
- **DM:** Send the bot a DM directly.

## Customizing what the bot knows

Edit `site_context.md`. The file is loaded once when the bot starts, so restart
the bot after editing. Keep it focused — a tight, well-organized context produces
much better answers than a giant dump.
