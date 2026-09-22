# ============================================================
#  bot.py — Telegram-бот ELFLIQ_VapeLab + Flask + WebApp
#  Render-ready + CORS для GitHub Pages + мультиадмин
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

# Список админов (получатели заказов в личку + доступ к /admin)
ADMIN_IDS    = [5422357973, 1818878028, 8060630121]

# Первый в списке — "главный" (например, для логики "не отправлять покупателю, если это админ")
ADMIN_ID     = ADMIN_IDS[0]

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
    # ─── Жидкости: старые позиции ─────────────────────
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

    # ─── Жидкости: новые позиции ──────────────────────
    "100": {"name": "Elflio / Apple Pear",                      "qty": 0},
    "101": {"name": "Elflio / Blueberry Rose Mint",             "qty": 0},
    "102": {"name": "Elflio / Blueberry Sour Raspberry",        "qty": 0},
    "103": {"name": "Elflio / Blue Razz",                       "qty": 0},
    "104": {"name": "Elflio / Blue Razz Lemonade",              "qty": 0},
    "105": {"name": "Elflio / Cherry",                          "qty": 0},
    "106": {"name": "Elflio / Cherry Cola",                     "qty": 0},
    "107": {"name": "Elflio / Cool Mint",                       "qty": 0},
    "108": {"name": "Elflio / Cuba Tobacco",                    "qty": 0},
    "109": {"name": "Elflio / Double Apple",                    "qty": 0},
    "110": {"name": "Elflio / Elfbull Ice",                     "qty": 0},
    "111": {"name": "Elflio / Elf Jack",                        "qty": 0},
    "112": {"name": "Elflio / Grape Cherry",                    "qty": 0},
    "113": {"name": "Elflio / Green Grape Rose",                "qty": 0},
    "114": {"name": "Elflio / Jasmine Raspberry",               "qty": 0},
    "115": {"name": "Elflio / Kiwi Passion Fruit Guava",        "qty": 0},
    "116": {"name": "Elflio / Ocean Mint",                      "qty": 0},
    "117": {"name": "Elflio / P&B Cloudd",                      "qty": 0},
    "118": {"name": "Elflio / Pineapple Colada",                "qty": 0},
    "119": {"name": "Elflio / Pink Lemonade",                   "qty": 0},
    "120": {"name": "Elflio / Pink Lemonade Soda",              "qty": 0},
    "121": {"name": "Elflio / Raspberry Lychee",                "qty": 0},
    "122": {"name": "Elflio / Rhubarb Snoow",                   "qty": 0},
    "123": {"name": "Elflio / Snoow Tobacco",                   "qty": 0},
    "124": {"name": "Elflio / Sour Watermelon Gummy",           "qty": 0},
    "125": {"name": "Elflio / Spearmint",                       "qty": 0},
    "126": {"name": "Elflio / Strawberry Cherry Lemon",         "qty": 0},
    "127": {"name": "Elflio / Strawberry Ice",                  "qty": 0},
    "128": {"name": "Elflio / Strawberry Kiwi",                 "qty": 0},
    "129": {"name": "Elflio / Strawberry Raspberry Cherry Ice", "qty": 0},
    "130": {"name": "Elflio / Strawberry Snoow",                "qty": 0},
    "131": {"name": "Elflio / Watermelon",                      "qty": 0},
    "132": {"name": "Elflio / Watermelon Cherry",               "qty": 0},

    # ─── Картриджи ────────────────────────────────────
    "200": {"name": "Xros 0,4 om",                              "qty": 0},
    "201": {"name": "OXVA xlim 0,6 om",                         "qty": 0},
}


def load_stock():
    if not os.path.exists(DATA_FILE):
        save_stock(DEFAULT_STOCK)
        return dict(DEFAULT_STOCK)
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Дополняем новыми позициями, если их нет в файле
        changed = False
        for k, v in DEFAULT_STOCK.items():
            if k not in data:
                data[k] = v
                changed = True
        if changed:
            save_stock(data)
        return data
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

    ok_admin_any = False
    ok_buyer = False

    # --- отправка ВСЕМ админам ---
    for admin_id in ADMIN_IDS:
        try:
            r = rq.post(url, json={
                "chat_id": admin_id,
                "text": admin_text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }, timeout=10)
            if r.status_code == 200:
                ok_admin_any = True
            else:
                logging.error("Admin %s send failed: %s %s", admin_id, r.status_code, r.text)
        except Exception as e:
            logging.exception("Admin %s send exception: %s", admin_id, e)

    # --- отправка покупателю (если он не админ) ---
    if tg_id and int(tg_id) not in ADMIN_IDS:
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

    return _cors(jsonify({"ok": ok_admin_any, "ok_buyer": ok_buyer})), (200 if ok_admin_any else 500)


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
    try:
        await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb())
    except Exception as e:
        logging.exception("cmd_start error: %s", e)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Наличие (список)",
                                  callback_data="show_stock")],
            [InlineKeyboardButton(text="📢 Наш канал",
                                  url="https://t.me/ELFLIQ_LAB")],
        ])
        await message.answer(WELCOME_TEXT, reply_markup=kb)


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
    logging.info("ADMIN_IDS: %s", ADMIN_IDS)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
