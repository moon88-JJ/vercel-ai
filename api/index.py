import os
import asyncio
from openai import OpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from fastapi import FastAPI, Request

# ========= 环境变量 =========
API_KEY = os.getenv("MIMO_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# ========= 初始化 OpenAI 客户端 =========
client = OpenAI(api_key=API_KEY, base_url="https://api.xiaomimimo.com/v1")

# ========= 初始化 Telegram 应用 =========
application = Application.builder().token(TELEGRAM_TOKEN).build()
_initialized = False  # 标记是否已初始化（防止重复初始化）


async def ensure_initialized():
    """确保 Telegram Application 只初始化一次"""
    global _initialized
    if not _initialized:
        await application.initialize()   # ✅ 初始化 bot / dispatcher
        _initialized = True


# ========= Telegram Handlers =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 你好！我是你的 GPT 助手。随便问我点什么吧～")


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    try:
        completion = await asyncio.to_thread(lambda: client.chat.completions.create(
            model="mimo-v2-flash",
            messages=[
                {"role": "system", "content": "你是一个友好、有逻辑的AI助手。"},
                {"role": "user", "content": user_text}
            ],
            temperature=0.6,
        ))
        reply_text = completion.choices[0].message.content.strip()
    except Exception as e:
        reply_text = f"⚠️ 出现错误：{str(e)}"
    await update.message.reply_text(reply_text)


application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))


# ========= FastAPI 入口 =========
app = FastAPI()


@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Telegram Webhook 回调"""
    try:
        await ensure_initialized()  # ✅ 确保已初始化
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return {"status": "ok"}  # ✅ 返回 dict，避免 bytes header 错误
    except Exception as e:
        print(f"⚠️ Webhook error: {e}")
        return {"error": str(e)}


# ========= （可选）Webhook 注册 =========
# 在部署后，本地或单独运行一次以下代码注册 webhook
if __name__ == "__main__":
    async def register_webhook():
        await ensure_initialized()
        webhook_url = "https://vercel-ai-smoky.vercel.app/webhook"
        await application.bot.set_webhook(webhook_url)
        print(f"✅ Webhook 已注册到 {webhook_url}")

    asyncio.run(register_webhook())
