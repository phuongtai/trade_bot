import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import requests
import sqlite3
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import os
db_path = os.path.join(os.path.dirname(__file__), 'gold_data.db')

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")

# Initialize database
# If the database does not exist, it will be created

conn = sqlite3.connect(db_path)
c = conn.cursor()

# Create tables
c.execute('''CREATE TABLE IF NOT EXISTS gold_prices
             (date TEXT PRIMARY KEY, price REAL, currency TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS central_bank_reserves
             (country TEXT, date TEXT, tonnes REAL)''')

conn.commit()

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message with menu buttons"""
    keyboard = [
        [InlineKeyboardButton("🏦 Central Bank Data", callback_data='cb_data')],
        [InlineKeyboardButton("💰 Gold Price", callback_data='price')],
        [InlineKeyboardButton("📰 Gold News", callback_data='news')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🟡 Gold Demand Monitor Bot\n\nChoose an option:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'price':
        await get_gold_price(update, context)
    elif query.data == 'news':
        await get_gold_news(update, context)
    elif query.data == 'cb_data':
        await get_central_bank_data(update, context)

async def get_gold_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch current gold price"""
    try:
        url = f"https://www.alphavantage.co/query?function=GOLD&apikey={ALPHA_VANTAGE_API_KEY}"
        response = requests.get(url).json()
        price = float(response["name"])
        
        # Store in database
        c.execute("INSERT OR REPLACE INTO gold_prices VALUES (datetime('now'), ?, 'USD')", 
                 (price,))
        conn.commit()
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"🟡 Current Gold Price: ${price:.2f}/oz"
        )
    except Exception as e:
        logging.error(f"Error fetching gold price: {e}")
        await send_error(update, context)

async def get_central_bank_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch central bank gold reserves (mock data - replace with real API)"""
    try:
        # Example: World Gold Council API (mock)
        data = {
            "China": 225,
            "Turkey": 160,
            "India": 34
        }
        
        message = "🏦 Central Bank Purchases (2023):\n"
        for country, tonnes in data.items():
            message += f"\n• {country}: {tonnes} tonnes"
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message
        )
    except Exception as e:
        await send_error(update, context)

async def get_gold_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch latest gold-related news"""
    try:
        url = f"https://newsapi.org/v2/everything?q=gold&apiKey={NEWSAPI_KEY}"
        response = requests.get(url).json()
        
        news_items = response['articles'][:3]
        message = "📰 Latest Gold News:\n\n"
        
        for item in news_items:
            message += f"• {item['title']}\n{item['url']}\n\n"
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message
        )
    except Exception as e:
        await send_error(update, context)

async def send_error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors gracefully"""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="⚠️ Error fetching data. Please try again later."
    )

async def scheduled_updates(context: ContextTypes.DEFAULT_TYPE):
    """Send daily updates to subscribers"""
    try:
        # Get all subscribed users (implement subscription logic)
        url = f"https://www.alphavantage.co/query?function=GOLD&apikey={ALPHA_VANTAGE_API_KEY}"
        price = requests.get(url).json()["name"]
        
        message = f"🌅 Daily Gold Update:\n\nPrice: ${price}/oz"
        await context.bot.send_message(
            chat_id=context.job.chat_id,
            text=message
        )
    except Exception as e:
        logging.error(f"Scheduled update failed: {e}")

def main():
    """Start the bot"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Set up scheduler for daily updates
    scheduler = AsyncIOScheduler()
    scheduler.add_job(scheduled_updates, 'cron', hour=8, args=[application])
    scheduler.start()
    
    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()