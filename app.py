# ============================================================
#  bot.py — Telegram-бот ELFLIQ_VapeLab + Flask + WebApp
#  Render-ready + CORS для GitHub Pages
# ============================================================

import asyncio
import logging
import json
import os
import threading
from datetime import datetime

import requests as rq
from flask import Flask, request, jsonify, send_from_directory

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, WebAppInfo,
)
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# ===================== CONFIG =====================
BOT_TOKEN    = os.environ.get("BOT_TOKEN", "8717566441:AAGawmDkoIUv2INBePTrdDEH8lKNBZAeaGw")
ADMIN_ID     = int(os.environ.get("ADMIN_ID", "5422357973"))
ADMIN_KEY    = os.environ.get("ADMIN_KEY", "elfliq-super-secret-2026")
WEBAPP_URL   = os.environ.get("WEBAPP_URL", "https://vasneebet1.github.io/vpshp/")
LISTEN_HOST  = "0.0.0.0"
LISTEN_PORT  = int(os.environ.get("PORT", "8080"))
DATA_DIR     = os.environ.get("DATA_DIR", ".")
DATA_FILE    = os.path.join(DATA_DIR, "stock.json")
# ==================================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp  = Dispatcher()
app = Flask(__name__)

DEFAULT_STOCK = {
    "2":  {"name": "Elflio / Strawberry Banana",               "qty": 0},
    "3":  {"name": "Elflio / Cherry Lemon Peach",              "qty": 0},
    "4":  {"name": "Elflio / Blueberry Raspberry Pomegranate", "qty": 0},
    "6":  {"name": "Elflio / Raspberry Lychee",                "qty": 0},
    "7":  {"name": "Elflio / Pineapple Ice",                   "qty": 0},
    "8":  {"name": "Elflio / Lemon Lime",                      "qty": 0},
    "10": {"name": "Elflio / Blueberry",                       "qty": 0},
    "12": {"name": "Elflio / Sour apple",                      "qty": 0},
    "13": {"name": "Elflio / Grape",                           "qty": 0},
    "16": {"name": "Elflio / Apple peach",                     "qty": 0},
    "17": {"name": "Elflio / Cola",                            "qty": 0},
    "18": {"name": "Elflio / Peach ice",                       "qty": 0},
    "19": {"name": "Elflio / Pinacolada",                      "qty": 0},
    "20": {"name": "Elflio / Blackberry lemon",                "qty": 0},
    "21": {"name": "Elflio / Pink Grapefruit",                 "qty": 0},
    "22": {"name": "Elflio / Blackcurrant anised (5%)",        "qty": 0},
}


def load_stock():
    if not os.path.exists(DATA_FILE):
        save_stock(DEFAULT_STOCK)
        return dict(DEFAULT_STOCK)
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return dict(DEFAULT_STOCK)


def save_stock(stock):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(stock, f, ensure_ascii=False, indent=2)


def build_catalog_text():
    stock = load_stock()
    lines = []
    for key in sorted(stock.keys(), key=lambda k: int(k)):
        item = stock[key]
        q = int(item.get("qty", 0))
        if q <= 0:
            continue
        lines.append(f"{key}. {item['name']} — {q} шт.")
    return "\n\n".join(lines) if lines else "😔 Каталог пуст."


# ============================================================
#  FLASK
# ============================================================
def _cors(resp):
    resp.headers["Access-Control-Allow-Origin"]  = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp


@app.route("/", methods=["GET", "HEAD"])
@app.route("/health", methods=["GET", "HEAD"])
def health():
    return "OK", 200


@app.route("/webapp", methods=["GET"])
def webapp():
    return send_from_directory(".", "index.html")


@app.route("/img/<path:filename>", methods=["GET"])
def serve_img(filename):
    return send_from_directory("img", filename)


@app.route("/admin", methods=["GET"])
def admin_page():
    key = request.args.get("key", "")
    if key != ADMIN_KEY:
        return "Not Found", 404
    return send_from_directory(".", "admin.html")


@app.route("/admin/api/stock", methods=["GET", "POST", "OPTIONS"])
def admin_api_stock():
    if request.method == "OPTIONS":
        return _cors(jsonify({"ok": True}))

    key = request.args.get("key", "")
    if key != ADMIN_KEY:
        return _cors(jsonify({"ok": False, "error": "forbidden"})), 403

    if request.method == "GET":
        return _cors(jsonify({"ok": True, "stock": load_stock()}))

    data = request.get_json(silent=True) or {}
    item_id = str(data.get("id", "")).strip()
    qty = data.get("qty")
    if not item_id or qty is None:
        return _cors(jsonify({"ok": False, "error": "missing id or qty"})), 400
    try:
        qty = max(0, int(qty))
    except (ValueError, TypeError):
        return _cors(jsonify({"ok": False, "error": "qty must be int"})), 400

    stock = load_stock()
    if item_id not in stock:
        return _cors(jsonify({"ok": False, "error": "item not found"})), 404
    stock[item_id]["qty"] = qty
    save_stock(stock)
    return _cors(jsonify({"ok": True, "id": item_id, "qty": qty}))


@app.route("/api/stock", methods=["GET", "OPTIONS"])
def public_stock():
    if request.method == "OPTIONS":
        return _cors(jsonify({"ok": True}))
    stock = load_stock()
    out = {k: int(v.get("qty", 0)) for k, v in stock.items()}
    return _cors(jsonify(out))


@app.route("/order", methods=["POST", "OPTIONS"])
def order():
    if request.method == "OPTIONS":
        return _cors(jsonify({"ok": True}))

    data     = request.get_json(silent=True) or {}
    name     = str(data.get("name", "")).strip()
    contact  = str(data.get("contact", "")).strip()
    comment  = str(data.get("comment", "")).strip()
    items    = data.get("items", []) or []
    tg_user  = str(data.get("tg_user", "")).strip()
    tg_id    = data.get("tg_id")
    total    = float(data.get("total", 0) or 0)

    if not items:
        return _cors(jsonify({"ok": False, "error": "empty items"})), 400

    # --- ПРОВЕРКА НАЛИЧИЯ И СПИСАНИЕ ---
    stock = load_stock()
    for it in items:
        iid = str(it.get("id", ""))
        qty_needed = int(it.get("qty", 0))
        if iid not in stock:
            return _cors(jsonify({"ok": False, "error": f"item {iid} not found"})), 400
        have = int(stock[iid].get("qty", 0))
        if have < qty_needed:
            return _cors(jsonify({"ok": False, "error": f"not enough stock for {iid}: have {have}, need {qty_needed}"})), 400

    for it in items:
        iid = str(it.get("id", ""))
        qty_needed = int(it.get("qty", 0))
        stock[iid]["qty"] = max(0, int(stock[iid].get("qty", 0)) - qty_needed)
    save_stock(stock)

    item_lines = []
    for it in items:
        item_lines.append(
            f"• {it.get('name','')} × {it.get('qty',0)} = {float(it.get('sum', 0)):.2f} zł"
        )
    items_block = "\n".join(item_lines)
    dt = datetime.now().strftime("%d.%m.%Y, %H:%M:%S")

    admin_text = (
        "🛒 <b>Новый заказ · ELFLIQ_VapeLab</b>\n"
        "━━━━━━━━━━━━━━━\n"
        f"👤 <b>Имя:</b> {name or '—'}\n"
        f"📞 <b>Контакт:</b> {contact or '—'}\n"
        f"💳 <b>Оплата:</b> {comment or 'Картой'}\n"
        "━━━━━━━━━━━━━━━\n"
        f"{items_block}\n"
        "━━━━━━━━━━━━━━━\n"
        f"💰 <b>Итого:</b> {total:.2f} zł\n"
        f"🆔 <b>Telegram:</b> {tg_user or '—'} (id: {tg_id})\n"
        f"⏱ {dt}"
    )

    buyer_text = (
        "✅ <b>Ваш заказ принят · ELFLIQ_VapeLab</b>\n"
        "━━━━━━━━━━━━━━━\n"
        f"{items_block}\n"
        "━━━━━━━━━━━━━━━\n"
        f"💰 <b>Итого:</b> {total:.2f} zł\n"
        f"💳 <b>Оплата:</b> {comment or 'Картой'}\n\n"
        "📞 Менеджер свяжется с вами: @ELFLIQ_Mng\n"
        f"⏱ {dt}"
    )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    ok_admin = False
    ok_buyer = False

    try:
        r = rq.post(url, json={
            "chat_id": ADMIN_ID,
            "text": admin_text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }, timeout=10)
        ok_admin = r.status_code == 200
        if not ok_admin:
            logging.error("Admin send failed: %s %s", r.status_code, r.text)
    except Exception as e:
        logging.exception("Admin send exception: %s", e)

    if tg_id and int(tg_id) != int(ADMIN_ID):
        try:
            r2 = rq.post(url, json={
                "chat_id": int(tg_id),
                "text": buyer_text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }, timeout=10)
            ok_buyer = r2.status_code == 200
        except Exception as e:
            logging.exception("Buyer send exception: %s", e)

    return _cors(jsonify({"ok": ok_admin, "ok_buyer": ok_buyer})), (200 if ok_admin else 500)


# ============================================================
#  HANDLERS
# ============================================================
WELCOME_TEXT = (
    "Добро пожаловать в <b>ELFLIQ_VapeLab</b>! ✨\n\n"
    "🕐 <b>Время работы:</b> 10:00–21:00\n"
    "📞 Менеджер: @ELFLIQ_Mng\n\n"
    "Открывай каталог 👇"
)


def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Открыть каталог",
                              web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton(text="📋 Наличие (список)",
                              callback_data="show_stock")],
        [InlineKeyboardButton(text="📢 Наш канал",
                              url="https://t.me/ELFLIQ_LAB")],
    ])


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb())


@dp.callback_query(F.data == "show_stock")
async def show_stock_cb(call: CallbackQuery):
    await call.message.answer("🍓 <b>Наличие:</b>\n\n" + build_catalog_text())
    await call.answer()


def run_flask():
    app.run(host=LISTEN_HOST, port=LISTEN_PORT, debug=False, use_reloader=False)


async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    logging.info("Flask: http://%s:%s", LISTEN_HOST, LISTEN_PORT)
    logging.info("DATA_FILE: %s", os.path.abspath(DATA_FILE))
    logging.info("WEBAPP_URL: %s", WEBAPP_URL)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
