import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Load .env file variables
load_dotenv()

# === CONFIG ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = os.getenv("ADMIN_IDS")  # Comma-separated string e.g. "123,456,789"
if ADMIN_IDS:
    ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS.split(",")]
else:
    ADMIN_IDS = []

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# === FSM STATES ===
class Register(StatesGroup):
    ChooseLang = State()
    Contact = State()
    Password = State()
    PaymentScreenshot = State()

# === HANDLERS ===

@dp.message_handler(commands=["start"], state="*")
async def start_handler(message: types.Message, state: FSMContext):
    await state.finish()
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🇬🇧 English"), KeyboardButton("🇪🇹 አማርኛ"))
    await message.answer("🌐 Please select your language / እባክዎን ቋንቋ ይምረጡ።", reply_markup=kb)
    await Register.ChooseLang.set()

@dp.message_handler(state=Register.ChooseLang)
async def language_chosen(message: types.Message, state: FSMContext):
    if "አማርኛ" in message.text:
        lang = "am"
        prompt = "📲 ስልክ ቁጥርዎን በተን በመንካት ያጋሩ።"
    else:
        lang = "en"
        prompt = "📞 Please share your phone number."

    await state.update_data(lang=lang)
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📞 Send Contact", request_contact=True))
    await message.answer(prompt, reply_markup=kb)
    await Register.Contact.set()

@dp.message_handler(content_types=types.ContentType.CONTACT, state=Register.Contact)
async def contact_received(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    data = await state.get_data()
    lang = data.get("lang")

    prompt = "🔐 እባክዎ password ያስገቡ።" if lang == "am" else "🔐 Please enter your desired password."
    await message.answer(prompt, reply_markup=types.ReplyKeyboardRemove())
    await Register.Password.set()

@dp.message_handler(state=Register.Contact)
async def invalid_contact(message: types.Message):
    await message.answer("⚠️ Please use the contact button.")

@dp.message_handler(state=Register.Password)
async def password_received(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang")
    password = message.text.strip()

    if not password or len(password) < 4:
        await message.answer(
            "❗ የይለፍ ቃል ቢያንስ 4 ፊደላት አለበት።" if lang == "am" else "❗ Password must be at least 4 characters. Try again."
        )
        return

    await state.update_data(password=password)

    if lang == "am":
        msg = (
            "🏦 290 ብር ወደ ከዚህ በታች ያሉት ሂሳቦች ይላኩ፡፡\n"
            "👉 ስም: Brook Fantahun Gebremeskel\n"
            "👉 CBE: 1000218150628\n"
            "👉 TELEBIRR: 0953134956\n"
            "*__ከዚያም የክፍያውን screenshot ያስገቡ።__*"
        )
    else:
        msg = (
            "💳 Please transfer 290 ETB to:\n"
            "👉 Name: Brook Fantahun Gebremeskel\n"
            "👉 CBE: 1000218150628\n"
            "👉 TELEBIRR: 0953134956\n"
            "*__Then upload your payment screenshot.__*"
        )

    await message.answer(msg, parse_mode=types.ParseMode.MARKDOWN)
    await Register.PaymentScreenshot.set()

@dp.message_handler(content_types=types.ContentType.PHOTO, state=Register.PaymentScreenshot)
async def photo_received(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang")
    phone = data.get("phone")
    password = data.get("password")
    photo_id = message.photo[-1].file_id

    caption = (
        f"🆕 Registration:\n📱 Phone: {phone}\n🔑 Password: {password}\n"
        f"🌐 Lang: {lang}\n👤 From: @{message.from_user.username or message.from_user.full_name}"
    )

    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("✅ Send Login Info", callback_data=f"login:{message.from_user.id}")
    )

    for admin_id in ADMIN_IDS:
        await bot.send_photo(admin_id, photo=photo_id, caption=caption, reply_markup=kb)

    thank_you = (
        "✅ አመሰግናለን! ፎቶዎ ደርሶናል። በ 2 ሰአታት ውስጥ እንመልሶለናል። እዚው ይጠብቁ"
        if lang == "am"
        else "✅ Thanks! We received your screenshot. We'll activate your access shortly."
    )
    await message.answer(thank_you)
    await state.finish()

@dp.message_handler(state=Register.PaymentScreenshot)
async def invalid_photo(message: types.Message):
    await message.answer("⚠️ Please send a clear screenshot.")

@dp.callback_query_handler(lambda c: c.data.startswith("login:"))
async def send_login_info(callback_query: types.CallbackQuery):
    user_id = int(callback_query.data.split(":")[1])
    try:
        await bot.send_message(
            user_id,
            "👋 እንኳን ደህና መጣችሁ! ከአሁን ጀምሮ Zegju.com ላይ መጠቀም ይችላሉ።\n👉 https://www.youtube.com/watch?v=YOUR_VIDEO_ID",
        )
        await bot.send_message(
            user_id,
            "👋 Hello! You can now use Zegju.com.\n👉 https://www.youtube.com/watch?v=YOUR_VIDEO_ID",
        )
        await callback_query.answer("✅ Login message sent.")
    except Exception as e:
        logging.error(f"Failed to message user: {e}")
        await callback_query.answer("❌ Failed to send login info.")

@dp.message_handler(commands="cancel", state="*")
async def cancel(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("❌ Cancelled. Send /start to restart.", reply_markup=types.ReplyKeyboardRemove())

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
