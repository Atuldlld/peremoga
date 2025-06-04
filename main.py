import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import requests

# Загрузка переменных окружения
load_dotenv()

# Конфигурация логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ключи из .env
API_KEY = os.getenv('UKRAINE_ALARM_API_KEY')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
API_URL = "https://api.ukrainealarm.com/api/v3"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user = update.effective_user
    await update.message.reply_html(
        f"Привет {user.mention_html()}!\n\n"
        "Я бот для отслеживания воздушных тревог в Украине.\n"
        "Используй команды:\n"
        "/alerts - текущие тревоги\n"
        "/regions - список регионов\n"
        "/region [id] - тревоги по региону (например /region 5)"
    )

async def get_access_token() -> str:
    """Получение JWT токена"""
    try:
        response = requests.post(
            f"{API_URL}/token",
            json={"apiKey": API_KEY},
            timeout=10
        )
        response.raise_for_status()
        return response.json()["accessToken"]
    except Exception as e:
        logger.error(f"Token error: {e}")
        raise

async def alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Получение всех активных тревог"""
    try:
        token = await get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(
            f"{API_URL}/alerts",
            headers=headers,
            timeout=15
        )
        response.raise_for_status()
        
        alerts_data = response.json()
        if not alerts_data:
            await update.message.reply_text("🚫 Активных тревог нет")
            return
            
        message = "🚨 Активные тревоги:\n\n"
        for region in alerts_data:
            region_name = region.get("regionName", "N/A")
            alarms = region.get("alarms", [])
            if alarms:
                for alarm in alarms:
                    alarm_type = alarm.get("type", "UNKNOWN")
                    start_date = alarm.get("startDate", "N/A")
                    message += f"📍 {region_name}\n"
                    message += f"Тип: {alarm_type}\n"
                    message += f"Начало: {start_date}\n\n"
        
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Alerts error: {e}")
        await update.message.reply_text("⚠️ Ошибка получения данных. Попробуйте позже.")

async def regions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Получение списка регионов"""
    try:
        token = await get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(
            f"{API_URL}/regions",
            headers=headers,
            timeout=15
        )
        response.raise_for_status()
        
        regions_data = response.json()
        message = "📋 Список регионов:\n\n"
        for region in regions_data:
            message += f"ID: {region['regionId']}\n"
            message += f"Название: {region['regionName']}\n\n"
        
        await update.message.reply_text(message + "Используй /region [id] для проверки")
    except Exception as e:
        logger.error(f"Regions error: {e}")
        await update.message.reply_text("⚠️ Ошибка получения списка регионов")

async def region_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Получение тревог по конкретному региону"""
    try:
        region_id = context.args[0] if context.args else None
        if not region_id:
            await update.message.reply_text("ℹ️ Укажите ID региона: /region [id]")
            return

        token = await get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(
            f"{API_URL}/alerts/regions/{region_id}",
            headers=headers,
            timeout=15
        )
        response.raise_for_status()
        
        region_data = response.json()
        message = f"🔍 Регион: {region_data.get('regionName', 'N/A')}\n\n"
        
        alarms = region_data.get("alarms", [])
        if not alarms:
            message += "🚫 Активных тревог нет"
        else:
            for alarm in alarms:
                alarm_type = alarm.get("type", "UNKNOWN")
                start_date = alarm.get("startDate", "N/A")
                message += f"Тип: {alarm_type}\n"
                message += f"Начало: {start_date}\n"
                if alarm.get("endDate"):
                    message += f"Конец: {alarm.get('endDate')}\n"
                message += "\n"
        
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Region alerts error: {e}")
        await update.message.reply_text("⚠️ Ошибка получения данных региона")

def main() -> None:
    """Запуск бота"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("alerts", alerts))
    application.add_handler(CommandHandler("regions", regions))
    application.add_handler(CommandHandler("region", region_alerts))
    
    # Запуск бота
    application.run_polling()

if __name__ == "__main__":
    main()
