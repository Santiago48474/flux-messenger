import requests
import telebot

# ===== CONFIG =====
TOKEN = "8530189698:AAHkKnn9DPnwkRT61397zCeUU0-po_d6uE4"
API_KEY = "4f91a220fa436c0c6b2848302c85a378"

BASE_URL = "http://apilayer.net/api/validate"

bot = telebot.TeleBot(TOKEN)


# ===== PHONE NORMALIZATION =====
def normalize_phone(phone):
    phone = phone.strip().replace(" ", "")
    if not phone.startswith("+") or len(phone) < 8:
        return None
    return phone


# ===== API REQUEST =====
def get_phone_info(phone):

    params = {
        "access_key": API_KEY,
        "number": phone
    }

    try:
        response = requests.get(BASE_URL, params=params)
        data = response.json()

        if not data.get("valid"):
            return "Number not valid"

        text = (
            f"Valid: {data.get('valid')}\n"
            f"Country: {data.get('country_name')}\n"
            f"Location: {data.get('location')}\n"
            f"Carrier: {data.get('carrier')}\n"
            f"Line type: {data.get('line_type')}\n"
            f"International format: {data.get('international_format')}\n"
            f"Local format: {data.get('local_format')}"
        )

        return text

    except Exception as e:
        return f"Error: {e}"


# ===== START COMMAND =====
@bot.message_handler(commands=['start'])
def start(msg):
    bot.reply_to(msg, "Send phone number like +123456789")


# ===== MESSAGE HANDLER =====
@bot.message_handler(func=lambda m: True)
def handler(msg):

    phone = normalize_phone(msg.text)

    if not phone:
        bot.reply_to(msg, "Invalid format")
        return

    result = get_phone_info(phone)
    bot.reply_to(msg, result)


print("BOT STARTED")
bot.infinity_polling()
