import os
import psutil
import subprocess
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import locale
import requests
import json

os.system("chcp 65001")  
locale.setlocale(locale.LC_ALL, "")  
with open("./config.json", "r", encoding="utf-8") as file:
    parsed_data = json.load(file) 

bot = Bot(token=parsed_data["Bot"]["BOT_TOKEN"])
dp = Dispatcher(bot)

@dp.message_handler(commands=['run'])
async def execute_command(message: types.Message):
    command = message.get_args()
    if not command:
        await message.reply("Укажите команду для выполнения. Пример: /run dir")
        return

    try:
        # Выполнение команды через PowerShell
        result = subprocess.check_output(command, shell=True, text=True, stderr=subprocess.STDOUT)
        await message.reply(f"Результат:\n```\n{result}\n```", parse_mode="Markdown")
    except subprocess.CalledProcessError as e:
        await message.reply(f"Ошибка при выполнении:\n```\n{e.output}\n```", parse_mode="Markdown")

# Команда: Показать состояние системы
@dp.message_handler(commands=['status'])
async def system_status(message: types.Message):
    cpu = psutil.cpu_percent()
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage('C:\\').percent  # Состояние диска C:
    await message.reply(
        f"📊 Состояние системы:\n"
        f"🖥 CPU: {cpu}%\n"
        f"💾 RAM: {memory}%\n"
        f"📂 Диск C: {disk}%"
    )
@dp.message_handler(commands=['temp'])
async def get_hardware_monitor_data(message: types.Message):
    try:
        url = "http://localhost:8085/data.json"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        def parse_hardware(hardware):
            """Парсит JSON и извлекает данные."""
            output = []
            name = hardware.get('Text', 'Неизвестное устройство')
            for child in hardware.get('Children', []):
                if 'Value' in child and child['Value']:
                    output.append(f"{child['Text']}: {child['Value']}")
                if 'Children' in child:
                    output.extend(parse_hardware(child))
            return output

        # Парсим все данные
        result = []
        for device in data.get('Children', []):
            device_name = device.get('Text', 'Устройство')
            device_data = parse_hardware(device)
            if device_data:
                result.append(f"*{device_name}*\n" + "\n".join(device_data))

        # Формируем ответ
        if result:
            await message.reply("\n\n".join(result), parse_mode="Markdown")
        else:
            await message.reply("Данные не найдены.")
    except requests.exceptions.RequestException as e:
        await message.reply(f"Ошибка подключения к OpenHardwareMonitor: {e}")
    except Exception as e:
        await message.reply(f"Ошибка: {e}")



# Команда: Показать процессы
@dp.message_handler(commands=['processes'])
async def list_processes(message: types.Message):
    processes = [(p.info["name"], p.info["cpu_percent"]) for p in psutil.process_iter(attrs=["name", "cpu_percent"])]
    processes = sorted(processes, key=lambda x: x[1], reverse=True)[:10]  # Топ 10 процессов
    process_list = "\n".join([f"{name}: {cpu}%" for name, cpu in processes])
    await message.reply(f"🔍 Топ процессов по CPU:\n```\n{process_list}\n```", parse_mode="Markdown")

# Команда: Завершение работы системы
@dp.message_handler(commands=['shutdown'])
async def shutdown_system(message: types.Message):
    await message.reply("🛑 Завершаю работу системы...")
    os.system("shutdown /s /t 0")  # Завершение работы Windows

# Уведомления о критических состояниях (фоновый процесс)
async def notify_critical():
    import asyncio
    while True:
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory().percent
        if cpu > 90 or memory > 90:
            await bot.send_message(
                chat_id="ваш_chat_id",
                text=f"⚠️ Внимание! Высокая загрузка:\n"
                     f"CPU: {cpu}%\nRAM: {memory}%"
            )
        await asyncio.sleep(60)  # Проверка каждые 60 секунд

# Запуск бота
if __name__ == "__main__":
    import asyncio
    loop = asyncio.get_event_loop()
    loop.create_task(notify_critical())  # Запуск фонового процесса
    executor.start_polling(dp)
