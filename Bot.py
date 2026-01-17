import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiohttp import web

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8495883169:AAEbPfdFYB3_Viobfbu_mSZqRFns0wgoxjk"
ADMIN_ID = 5245806367
MAIN_CHANNEL = "@ua_market_ukraine"

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# --- ЗАГЛУШКА ДЛЯ RENDER (ЧТОБЫ НЕ ПЕРЕЗАГРУЖАЛСЯ) ---
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 10000)))
    await site.start()

# --- ЛОГИКА БОТА ---
class AdStates(StatesGroup):
    choosing_city = State()
    waiting_content = State()

CITIES = ["Київ", "Львів", "Одеса", "Дніпро", "Харків", "Вся Україна"]

def get_cities_kb():
    buttons = [[types.KeyboardButton(text=city)] for city in CITIES]
    return types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_admin_kb(user_id, has_photo=False):
    suffix = "photo" if has_photo else "text"
    kb = [[types.InlineKeyboardButton(text="✅ Опублікувати", callback_data=f"post_{suffix}_{user_id}")],
          [types.InlineKeyboardButton(text="❌ Відхилити", callback_data=f"decl_{user_id}")]]
    return types.InlineKeyboardMarkup(inline_keyboard=kb)

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await message.answer("🇺🇦 Вітаємо у UA Market! Оберіть місто:", reply_markup=get_cities_kb())
    await state.set_state(AdStates.choosing_city)

@dp.message(AdStates.choosing_city)
async def city_selected(message: types.Message, state: FSMContext):
    if message.text not in CITIES: return
    await state.update_data(city=message.text)
    await message.answer(f"📍 {message.text}. Надішліть опис товару (з фото або без):")
    await state.set_state(AdStates.waiting_content)

@dp.message(AdStates.waiting_content)
async def process_ad(message: types.Message, state: FSMContext):
    data = await state.get_data()
    city = data['city']
    caption = message.caption if message.caption else message.text
    user_ref = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"
    full_text = f"🔹 **НОВЕ ОГОЛОШЕННЯ**\n📍 Місто: #{city.replace(' ', '_')}\n\n{caption}\n\n👤 Контакт: {user_ref}"

    if message.photo:
        await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"📥 ЗАЯВКА:\n\n{full_text}", reply_markup=get_admin_kb(message.from_user.id, True), parse_mode="Markdown")
    else:
        await bot.send_message(ADMIN_ID, f"📥 ЗАЯВКА:\n\n{full_text}", reply_markup=get_admin_kb(message.from_user.id, False), parse_mode="Markdown")
    await message.answer("✅ Надіслано на модерацію!")
    await state.clear()

@dp.callback_query(F.data.startswith("post_"))
async def approve(callback: types.Callback_query):
    parts = callback.data.split("_")
    mode, user_id = parts[1], parts[2]
    clean_text = (callback.message.caption or callback.message.text).replace("📥 ЗАЯВКА:\n\n", "")
    try:
        if mode == "photo":
            await bot.send_photo(MAIN_CHANNEL, callback.message.photo[-1].file_id, caption=clean_text, parse_mode="Markdown")
        else:
            await bot.send_message(MAIN_CHANNEL, clean_text, parse_mode="Markdown")
        await callback.message.edit_text("✅ Опубліковано!") if not callback.message.photo else await callback.message.edit_caption(caption="✅ Опубліковано!")
        await bot.send_message(user_id, "🚀 Ваше оголошення опубліковано!")
    except Exception as e:
        await callback.answer(f"Помилка: {e}", show_alert=True)

async def main():
    # Запускаем веб-сервер и бота одновременно
    await asyncio.gather(start_web_server(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())
