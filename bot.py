import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from config import TOKEN

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

# Подключение к базе данных и создание таблицы students
def init_db():
    conn = sqlite3.connect("school_data.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            age INTEGER,
            grade TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Создаем классы состояний для FSM (Finite State Machine)
class StudentForm(StatesGroup):
    name = State()
    age = State()
    grade = State()

# Команда /start
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    button_start = KeyboardButton("Добавить студента")
    keyboard.add(button_start)
    await message.answer("Привет! Я бот для записи студентов. Нажмите на кнопку ниже, чтобы добавить студента.", reply_markup=keyboard)

# Обработка кнопки "Добавить студента"
@dp.message_handler(lambda message: message.text == "Добавить студента")
async def add_student(message: types.Message):
    await StudentForm.name.set()
    await message.answer("Введите имя студента:")

# Сохранение имени студента и переход к следующему состоянию (возраст)
@dp.message_handler(state=StudentForm.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await StudentForm.next()
    await message.answer("Введите возраст студента:")

# Сохранение возраста студента и переход к следующему состоянию (класс)
@dp.message_handler(state=StudentForm.age)
async def process_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите возраст числом.")
        return
    await state.update_data(age=int(message.text))
    await StudentForm.next()
    await message.answer("Введите класс студента (например, 5А):")

# Сохранение класса студента и завершение ввода
@dp.message_handler(state=StudentForm.grade)
async def process_grade(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    name = user_data['name']
    age = user_data['age']
    grade = message.text

    # Сохранение данных в базу данных
    conn = sqlite3.connect("school_data.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO students (name, age, grade) VALUES (?, ?, ?)", (name, age, grade))
    conn.commit()
    conn.close()

    await state.finish()
    await message.answer(f"Студент {name}, возраст {age}, класс {grade} успешно добавлен в базу данных!")

# Команда /show для отображения всех записей из базы данных
@dp.message_handler(commands=['show'])
async def show_students(message: types.Message):
    # Подключаемся к базе данных и извлекаем данные
    conn = sqlite3.connect("school_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students")
    rows = cursor.fetchall()
    conn.close()

    # Если таблица пуста
    if not rows:
        await message.answer("В базе данных пока нет записей.")
        return

    # Формируем сообщение с данными студентов
    response = "Список студентов:\n\n"
    for row in rows:
        student_id, name, age, grade = row
        response += f"ID: {student_id}\nИмя: {name}\nВозраст: {age}\nКласс: {grade}\n\n"

    # Отправляем сообщение пользователю
    await message.answer(response)

# Запуск бота
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)