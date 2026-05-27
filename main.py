from __future__ import annotations

import logging
import os
from pathlib import Path

import discord
from discord import Message
from dotenv import load_dotenv
from groq import AsyncGroq

load_dotenv()

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
MAX_REPLY_DEPTH = int(os.environ.get("MAX_REPLY_DEPTH", "12"))
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "1024"))
TEMPERATURE = float(os.environ.get("TEMPERATURE", "0.5"))
DISCORD_MSG_LIMIT = 1900

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("zflix-bot")

if not DISCORD_TOKEN:
    raise SystemExit("DISCORD_TOKEN env var is required")
if not GROQ_API_KEY:
    raise SystemExit("GROQ_API_KEY env var is required")

SITE_CONTEXT_PATH = Path(__file__).parent / "site_context.md"
SITE_CONTEXT = (
    SITE_CONTEXT_PATH.read_text(encoding="utf-8")
    if SITE_CONTEXT_PATH.exists()
    else "(No site context file found.)"
)

SYSTEM_PROMPT = f"""You are the official assistant for zflix.me. Answer user questions about the site clearly, accurately, and in a friendly tone.

Rules:
- Stick to what's in the site information below. If something isn't covered, say you're not sure and suggest the user check the site or contact support.
- Keep answers short by default. Expand only when the user asks for details or a step-by-step guide.
- Don't invent features, links, prices, or policies.
- Format with markdown when it helps (lists, bold, code). Avoid huge walls of text.

Site information for zflix.me:
---
{SITE_CONTEXT}
---
"""

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
groq_client = AsyncGroq(api_key=GROQ_API_KEY)


def strip_bot_mention(content: str, bot_id: int) -> str:
    return (
        content.replace(f"<@{bot_id}>", "")
        .replace(f"<@!{bot_id}>", "")
        .strip()
    )


async def build_conversation(message: Message) -> list[dict[str, str]]:
    chain: list[Message] = []
    current: Message | None = message
    depth = 0

    while current is not None and depth < MAX_REPLY_DEPTH:
        chain.append(current)
        ref = current.reference
        if ref and ref.message_id:
            try:
                current = await current.channel.fetch_message(ref.message_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                break
        else:
            break
        depth += 1

    chain.reverse()

    bot_id = client.user.id if client.user else 0
    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]

    for msg in chain:
        text = strip_bot_mention(msg.content or "", bot_id)
        if not text:
            continue
        role = "assistant" if msg.author.id == bot_id else "user"
        messages.append({"role": role, "content": text})

    return messages


def should_respond(message: Message) -> bool:
    if message.author.bot or client.user is None:
        return False

    if client.user.mentioned_in(message) and not message.mention_everyone:
        return True

    ref = message.reference
    if ref and isinstance(ref.resolved, Message):
        if ref.resolved.author.id == client.user.id:
            return True

    if isinstance(message.channel, discord.DMChannel):
        return True

    return False


async def call_groq(messages: list[dict[str, str]]) -> str:
    completion = await groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
    )
    return (completion.choices[0].message.content or "").strip()


def chunk_message(text: str, limit: int = DISCORD_MSG_LIMIT) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break
        split_at = remaining.rfind("\n", 0, limit)
        if split_at < limit // 2:
            split_at = remaining.rfind(" ", 0, limit)
        if split_at <= 0:
            split_at = limit
        chunks.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()
    return chunks


@client.event
async def on_ready() -> None:
    user = client.user
    log.info("Logged in as %s (id=%s)", user, user.id if user else "?")
    log.info("Using model: %s", GROQ_MODEL)
    log.info("Site context bytes: %d", len(SITE_CONTEXT))


@client.event
async def on_message(message: Message) -> None:
    if not should_respond(message):
        return

    log.info(
        "Responding to %s in #%s",
        message.author,
        getattr(message.channel, "name", "DM"),
    )

    try:
        async with message.channel.typing():
            conversation = await build_conversation(message)
            answer = await call_groq(conversation)
    except Exception as exc:
        log.exception("Failed to generate reply")
        await message.reply(
            f"Sorry, I ran into an error: `{type(exc).__name__}`. Try again in a moment.",
            mention_author=False,
        )
        return

    if not answer:
        await message.reply(
            "I don't have an answer for that one.",
            mention_author=False,
        )
        return

    for i, chunk in enumerate(chunk_message(answer)):
        if i == 0:
            await message.reply(chunk, mention_author=False)
        else:
            await message.channel.send(chunk)


if __name__ == "__main__":
    client.run(DISCORD_TOKEN, log_handler=None)
