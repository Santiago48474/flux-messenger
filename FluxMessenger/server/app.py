from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
import random
import time
import uuid

app = Flask(__name__)
# Настройка CORS для доступа с любого источника
CORS(app, origins=["http://localhost:8000", "http://127.0.0.1:8000", "http://192.168.0.18:8000", "*"])

# ============ БАЗА ДАННЫХ ============
users = {}
messages = []
gifts = []

# ============ СИСТЕМА ВАЛЮТ ============
class Economy:
    def __init__(self):
        self.thanks = {}
        self.afk_coins = {}
        self.flux_coins = {}
        self.last_daily = {}
        self.ratings = {}
    
    def add_daily_thanks(self, user_id):
        now = time.time()
        if user_id not in self.last_daily or now - self.last_daily[user_id] > 86400:
            self.thanks[user_id] = self.thanks.get(user_id, 0) + 100
            self.last_daily[user_id] = now
            user_msgs = len([m for m in messages if m['from'] == user_id])
            if user_msgs > 10:
                self.thanks[user_id] += 50
            return True, 100
        return False, 0
    
    def buy_afk_coin(self, user_id, amount):
        cost = amount * 10
        if self.thanks.get(user_id, 0) >= cost:
            self.thanks[user_id] -= cost
            self.afk_coins[user_id] = self.afk_coins.get(user_id, 0) + amount
            return True
        return False
    
    def add_rating(self, user_id, points):
        cost = points * 2
        if self.thanks.get(user_id, 0) >= cost:
            self.thanks[user_id] -= cost
            self.ratings[user_id] = self.ratings.get(user_id, 0) + points
            return True
        return False

economy = Economy()

# ============ ТЕМЫ ============
THEMES = {
    "black": "#000000",
    "white": "#FFFFFF",
    "pink": "#FF69B4",
    "blue": "#2196F3",
    "lightblue": "#87CEEB",
    "gray": "#808080",
    "blackwhite": "grayscale(100%)"
}

PREMIUM_THEMES = {
    "gradient_purple": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
    "gradient_coral": "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)",
    "gradient_forest": "linear-gradient(135deg, #11998e 0%, #38ef7d 100%)"
}

# ============ API ============

@app.route('/')
def index():
    return jsonify({
        "name": "Flux Messenger",
        "version": "0.2",
        "status": "running",
        "themes": list(THEMES.keys()),
        "premium_themes": list(PREMIUM_THEMES.keys()),
        "server_time": time.time()
    })

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    # Генерируем уникальный ID
    user_id = str(uuid.uuid4())[:8]
    
    # Проверка email
    for uid, user in users.items():
        if user.get('email') == data.get('email'):
            return jsonify({"status": "error", "message": "Email уже используется"}), 400
    
    users[user_id] = {
        "username": data.get('username'),
        "email": data.get('email'),
        "password": data.get('password'),
        "theme": "black",
        "wallpaper": "default",
        "premium": False,
        "created": time.time(),
        "bio": "",
        "status": "online"
    }
    
    economy.thanks[user_id] = 500
    economy.afk_coins[user_id] = 0
    economy.flux_coins[user_id] = 0
    economy.ratings[user_id] = 0
    
    return jsonify({
        "status": "ok",
        "user_id": user_id,
        "message": f"Добро пожаловать в Flux, {data.get('username')}!"
    })

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    for uid, user in users.items():
        if user['email'] == data.get('email') and user['password'] == data.get('password'):
            user['status'] = "online"
            return jsonify({
                "status": "ok",
                "user_id": uid,
                "user": {
                    "username": user['username'],
                    "email": user['email'],
                    "theme": user['theme'],
                    "premium": user['premium'],
                    "rating": economy.ratings.get(uid, 0),
                    "thanks": economy.thanks.get(uid, 0),
                    "afk": economy.afk_coins.get(uid, 0),
                    "flux": economy.flux_coins.get(uid, 0)
                }
            })
    return jsonify({"status": "error", "message": "Неверный email или пароль"}), 401

@app.route('/api/user/<user_id>')
def get_user(user_id):
    if user_id in users:
        user = users[user_id].copy()
        user.pop('password', None)
        user['rating'] = economy.ratings.get(user_id, 0)
        user['thanks'] = economy.thanks.get(user_id, 0)
        user['afk'] = economy.afk_coins.get(user_id, 0)
        user['flux'] = economy.flux_coins.get(user_id, 0)
        return jsonify(user)
    return jsonify({"status": "error", "message": "Пользователь не найден"}), 404

@app.route('/api/currency/daily/<user_id>')
def get_daily(user_id):
    success, amount = economy.add_daily_thanks(user_id)
    if success:
        return jsonify({
            "status": "ok",
            "thanks": economy.thanks.get(user_id, 0),
            "message": f"+{amount} Спасибо получено!"
        })
    last = economy.last_daily.get(user_id, 0)
    time_left = 86400 - (time.time() - last)
    hours = int(time_left // 3600)
    minutes = int((time_left % 3600) // 60)
    return jsonify({
        "status": "wait",
        "message": f"Уже получал сегодня. Жди {hours}ч {minutes}м"
    })

@app.route('/api/currency/buy_afk', methods=['POST'])
def buy_afk():
    data = request.json
    user_id = data.get('user_id')
    amount = data.get('amount', 1)
    
    if economy.buy_afk_coin(user_id, amount):
        return jsonify({
            "status": "ok",
            "thanks": economy.thanks.get(user_id, 0),
            "afk": economy.afk_coins.get(user_id, 0),
            "message": f"Куплено {amount} AFK коин(ов)"
        })
    return jsonify({
        "status": "error",
        "message": "Недостаточно Спасибо! Нужно 10 Спасибо за 1 AFK"
    }), 400

@app.route('/api/rating/add', methods=['POST'])
def add_rating():
    data = request.json
    user_id = data.get('user_id')
    points = data.get('points', 1)
    
    if economy.add_rating(user_id, points):
        return jsonify({
            "status": "ok",
            "rating": economy.ratings.get(user_id, 0),
            "thanks": economy.thanks.get(user_id, 0),
            "message": f"Рейтинг повышен на {points}"
        })
    return jsonify({
        "status": "error",
        "message": f"Недостаточно Спасибо! Нужно {points * 2} Спасибо"
    }), 400

@app.route('/api/chat/send', methods=['POST'])
def send_message():
    data = request.json
    msg = {
        "id": str(uuid.uuid4())[:8],
        "from": data.get('from'),
        "to": data.get('to'),
        "text": data.get('text'),
        "time": time.time(),
        "read": False
    }
    messages.append(msg)
    
    if data.get('from') in economy.thanks:
        bonus = random.randint(1, 3)
        economy.thanks[data.get('from')] += bonus
    
    return jsonify({"status": "ok", "message_id": msg['id']})

@app.route('/api/chat/messages/<user_id>')
def get_messages(user_id):
    user_msgs = [m for m in messages if m['to'] == user_id or m['from'] == user_id]
    user_msgs.sort(key=lambda x: x['time'])
    return jsonify(user_msgs[-50:])

@app.route('/api/theme/set/<user_id>/<theme>')
def set_theme(user_id, theme):
    if theme in THEMES or (users.get(user_id, {}).get('premium') and theme in PREMIUM_THEMES):
        if user_id in users:
            users[user_id]['theme'] = theme
            return jsonify({"status": "ok", "theme": theme})
    return jsonify({"status": "error", "message": "Тема не найдена"}), 404

@app.route('/api/test')
def test():
    return jsonify({
        "status": "ok",
        "message": "Сервер работает!",
        "time": time.time()
    })

# ============ ЗАПУСК ============
if __name__ == '__main__':
    print("""
    ╔══════════════════════════════════╗
    ║     FLUX MESSENGER SERVER v0.2   ║
    ║         ☭ НА ТЕЛЕФОНЕ ☭          ║
    ╚══════════════════════════════════╝
    """)
    print("🔥 Сервер запущен!")
    print("📱 Доступен по адресам:")
    print("   http://localhost:5000")
    print("   http://127.0.0.1:5000")
    print("   http://192.168.0.18:5000")
    print("\n💰 Валюты: Спасибо | AFK | Fluxkoin")
    print("\n👑 Премиум: 100 Fluxkoin")
    print("\n🚀 Нажми Ctrl+C для остановки")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
