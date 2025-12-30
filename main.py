import os
import asyncio
import logging
import datetime
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder


API_TOKEN = ''
ADMIN_ID = 
LOGS_DIR = '' # Example: /home/USER/tcpdumpLOGS/

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class SearchState(StatesGroup):
    waiting_for_ip = State()
    file_name = State()

class CaptureState(StatesGroup):
    waiting_for_duration = State()

def get_readable_size(path):
    try:
        size = os.path.getsize(path)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"
    except OSError:
        return "N/A"

def get_pcap_files():
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR, exist_ok=True)
    files = [f for f in os.listdir(LOGS_DIR) if f.endswith('.pcap')]
    return sorted(files, reverse=True)

async def get_ip_info(ip):
    """Пробив IP через API"""
    url = f"http://ip-api.com/json/{ip}?fields=status,message,country,city,isp,org,as"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                data = await resp.json()
                if data['status'] == 'success':
                    return (
                        f"🌍 *Страна:* {data.get('country', 'N/A')}, {data.get('city', 'N/A')}\n"
                        f"🏢 *Провайдер:* {data.get('isp', 'N/A')}\n"
                        f"📡 *Орг:* {data.get('org', 'N/A')}"
                    )
                else:
                    return "🔒 Локальный IP или инфо скрыто."
        except Exception as e:
            return f"⚠️ Ошибка API: {e}"

async def run_command_async(cmd):
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return stdout.decode('utf-8', errors='ignore').strip()

async def send_result(message: types.Message, result: str, title: str):
    if not result:
        await message.answer(f"ℹ️ Результат *{title}* пуст.", parse_mode="Markdown")
        return

    if len(result) > 4000:
        temp_path = f"/tmp/{title.replace(' ', '_')}.txt"
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(result)

        await message.answer_document(
            FSInputFile(temp_path),
            caption=f"📄 Результат {title} (слишком длинный для чата)"
        )
        os.remove(temp_path)
    else:
        await message.answer(f"📊 *{title}:*\n```\n{result}\n```", parse_mode="Markdown")

def file_keyboard(action_type):
    builder = InlineKeyboardBuilder()
    files = get_pcap_files()
    if not files:
        return None
    for f in files:
        path = os.path.join(LOGS_DIR, f)
        size_str = get_readable_size(path)
        builder.row(types.InlineKeyboardButton(
            text=f"{f} ({size_str})",
            callback_data=f"{action_type}:{f}")
        )
    return builder.as_markup()

def analysis_keyboard(filename):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🌐 Все сайты (DNS)", callback_data=f"dns:{filename}"))
    builder.row(types.InlineKeyboardButton(text="🚀 Последние 100 пакетов", callback_data=f"last:{filename}"))
    builder.row(types.InlineKeyboardButton(text="🔍 SNI (HTTPS домены)", callback_data=f"sni:{filename}"))
    builder.row(types.InlineKeyboardButton(text="📊 Топ 10 активных IP", callback_data=f"top_ip:{filename}"))
    builder.row(types.InlineKeyboardButton(text="📱 User-Agents (Устройства)", callback_data=f"ua:{filename}"))
    builder.row(types.InlineKeyboardButton(text="🎯 Поиск по IP + Пробив", callback_data=f"search_ip:{filename}"))
    builder.row(types.InlineKeyboardButton(text="🗑 Удалить файл", callback_data=f"del:{filename}"))
    builder.adjust(1)
    return builder.as_markup()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id != ADMIN_ID: return

    welcome_text = (
        "👋 *Привет, Админ!*\n"
        "Я твой инструмент для анализа сетевого трафика (TCPDUMP).\n\n"
        "🛠 *Основные команды:*\n"
        "🔴 /capture — **Запись трафика**. Если идет атака, жми сюда. Запишет новый .pcap файл.\n"
        "📂 /stats — **Анализ логов**. Главное меню работы с файлами.\n"
        "📥 /download — **Скачать**. Забрать raw-файл себе.\n\n"
        "🧐 *Что я умею искать (в меню /stats):*\n"
        "• **Топ IP** — Кто больше всех шлет запросы (поиск DDoS).\n"
        "• **DNS и SNI** — Какие сайты/домены открывались.\n"
        "• **User-Agents** — С каких устройств заходят (iPhone, Android, боты).\n"
        "• **Поиск IP + Пробив** — Показывает пакеты конкретного IP и пробивает его страну/провайдера."
    )
    await message.answer(welcome_text, parse_mode="Markdown")

@dp.message(Command("capture"))
async def cmd_capture(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("🔴 *Запись трафика*\nВведите время записи в секундах (например: 30):", parse_mode="Markdown")
    await state.set_state(CaptureState.waiting_for_duration)

@dp.message(CaptureState.waiting_for_duration)
async def process_capture(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Введите число.")
        return

    duration = int(message.text)
    if duration > 600:
        await message.answer("⚠️ Максимум 600 секунд.")
        return

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"capture_{timestamp}.pcap"
    filepath = os.path.join(LOGS_DIR, filename)

    await message.answer(f"⏳ *Пишу трафик {duration} сек...*\nФайл: `{filename}`", parse_mode="Markdown")

    cmd = f"timeout {duration} tcpdump -i any -w {filepath} 2>/dev/null"
    proc = await asyncio.create_subprocess_shell(cmd)
    await proc.wait()

    if os.path.exists(filepath):
        size = get_readable_size(filepath)
        await message.answer(f"✅ *Готово!*\nСоздан: `{filename}` ({size})\nЖми /stats для анализа.", parse_mode="Markdown")
    else:
        await message.answer("❌ Ошибка: Файл не создан. Проверьте права root.")

    await state.clear()

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    kb = file_keyboard("file")
    if kb:
        await message.answer("📂 *Меню анализа:*\nВыбери файл:", reply_markup=kb, parse_mode="Markdown")
    else:
        await message.answer("📂 Папка пуста.")

@dp.message(Command("download"))
async def cmd_download(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    kb = file_keyboard("down")
    if kb:
        await message.answer("📥 *Скачать файл:*", reply_markup=kb, parse_mode="Markdown")
    else:
        await message.answer("📂 Нет файлов.")

@dp.callback_query(F.data.startswith("file:"))
async def file_chosen(callback: types.CallbackQuery):
    filename = callback.data.split(":")[1]
    path = os.path.join(LOGS_DIR, filename)
    if not os.path.exists(path):
        await callback.answer("Файл не найден!", show_alert=True)
        return
    size = get_readable_size(path)
    await callback.message.edit_text(
        f"📁 *{filename}*\n📦 Размер: {size}\nЧто анализируем?",
        reply_markup=analysis_keyboard(filename),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.contains(":"))
async def execute_command(callback: types.CallbackQuery, state: FSMContext):
    data_parts = callback.data.split(":")
    action = data_parts[0]
    filename = data_parts[1]
    path = os.path.join(LOGS_DIR, filename)

    if action != "file" and not os.path.exists(path) and action != "search_ip":
        await callback.answer("Файл удален.", show_alert=True)
        return

    if action == "down":
        await callback.answer("Загружаю...")
        await callback.message.answer_document(FSInputFile(path))
        return

    if action == "del":
        try:
            os.remove(path)
            await callback.answer("Удалено!")
            await callback.message.edit_text(f"🗑 Файл *{filename}* удален.", parse_mode="Markdown")
        except:
            await callback.answer("Ошибка удаления", show_alert=True)
        return

    if action == "search_ip":
        await callback.message.answer(f"✍️ Введите IP для поиска в *{filename}*:", parse_mode="Markdown")
        await state.update_data(filename=filename)
        await state.set_state(SearchState.waiting_for_ip)
        await callback.answer()
        return

    commands = {
        "dns": rf"tcpdump -r {path} -n port 53 2>/dev/null | head -n 100",
        "last": rf"tcpdump -r {path} -n -c 100 2>/dev/null",
        "sni": rf"tcpdump -r {path} -nn -A 2>/dev/null | grep -Ei 'host:|..[a-z0-9.-]+\.(com|net|org|ru|io|lol|xyz)' | head -n 100",
        "top_ip": rf"tcpdump -nn -r {path} 2>/dev/null | awk -F' ' '{{print $3}}' | cut -d. -f1-4 | sort | uniq -c | sort -nr | head -n 10",
        "ua": rf"tcpdump -nn -A -r {path} 2>/dev/null | grep -E 'User-Agent' | head -n 3000 | sort | uniq -c | sort -nr | head -n 20"
    }

    if action in commands:
        await callback.answer("Анализирую...", show_alert=False)
        await bot.send_chat_action(chat_id=callback.message.chat.id, action="typing")
        res = await run_command_async(commands[action])
        await send_result(callback.message, res, f"{action} — {filename}")

@dp.message(SearchState.waiting_for_ip)
async def process_ip_search(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return

    ip = message.text.strip()
    data = await state.get_data()
    filename = data.get("filename")
    path = os.path.join(LOGS_DIR, filename)

    if any(c in ip for c in [";", "|", "&", "$", "`"]):
        await message.answer("⚠️ Неверные символы.")
        await state.clear()
        return

    await message.answer(f"🔎 Ищу пакеты *{ip}*...", parse_mode="Markdown")
    cmd = rf"tcpdump -r {path} -n host {ip} 2>/dev/null | head -n 100"
    res = await run_command_async(cmd)

    if res:
        await send_result(message, res, f"Трафик IP {ip}")
        await message.answer("🌍 *Пробиваю GeoIP...*", parse_mode="Markdown")
        geo_info = await get_ip_info(ip)
        await message.answer(geo_info, parse_mode="Markdown")
    else:
        await message.answer("Трафик с этим IP не найден.")

    await state.clear()

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
