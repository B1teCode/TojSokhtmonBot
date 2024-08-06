import telebot
from telebot import types
import sqlite3
import openpyxl
from openpyxl import Workbook
from config import *

# Основной бот
main_bot = telebot.TeleBot(MAIN_BOT_TOKEN, parse_mode='HTML')

# Административный бот
admin_bot = telebot.TeleBot(ADMIN_BOT_TOKEN, parse_mode='HTML')

class FeedbackHandler:
    def __init__(self, bot):
        self.bot = bot
        self.user_fio = None
        self.user_phone = None
        self.init_excel()

    def init_excel(self):
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Обратная связь"
            ws.append(["ФИО", "Номер телефона"])
            wb.save("feedback.xlsx")
        except Exception as e:
            print(f"Ошибка при инициализации Excel-файла: {e}")

    def start_feedback(self, message):
        self.bot.send_message(message.chat.id, "Пожалуйста, введите ваше ФИО:")
        self.bot.register_next_step_handler(message, self.get_fio)

    def get_fio(self, message):
        self.user_fio = message.text
        self.bot.send_message(message.chat.id, "Теперь введите ваш номер телефона:")
        self.bot.register_next_step_handler(message, self.get_phone)

    def get_phone(self, message):
        self.user_phone = message.text
        self.save_to_excel(self.user_fio, self.user_phone)
        admin_message = f"Новый запрос обратной связи:\n\nФИО: {self.user_fio}\nНомер телефона: {self.user_phone}"
        admin_bot.send_message(ADMIN_ID, admin_message)
        self.bot.send_message(message.chat.id, "Спасибо! Ваш запрос был отправлен.")

    @staticmethod
    def save_to_excel(fio, phone):
        try:
            wb = openpyxl.load_workbook("feedback.xlsx")
            ws = wb.active
            ws.append([fio, phone])
            wb.save("feedback.xlsx")
        except Exception as e:
            print(f"Ошибка при сохранении в Excel: {e}")

# Класс для работы с жилыми комплексами
class ResidentialComplexHandler:
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('Data/tojsokhtmon.db', check_same_thread=False)
        self.current_complex_id = None
        self.complex_name = None
        self.complex_description = None
        self.current_apartment = {}

    def add_complex(self, message):
        self.bot.send_message(message.chat.id, "Введите название нового жилого комплекса:")
        self.bot.register_next_step_handler(message, self.save_complex_name)

    def save_complex_name(self, message):
        self.complex_name = message.text
        self.bot.send_message(message.chat.id, "Введите описание жилого комплекса:")
        self.bot.register_next_step_handler(message, self.save_complex_description)

    def save_complex_description(self, message):
        self.complex_description = message.text
        self.bot.send_message(message.chat.id, "Отправьте фото жилого комплекса:")
        self.bot.register_next_step_handler(message, self.save_complex_photo)

    def save_complex_photo(self, message):
        if message.photo:
            file_id = message.photo[-1].file_id
            file_info = self.bot.get_file(file_id)
            downloaded_file = self.bot.download_file(file_info.file_path)

            with self.conn:
                self.conn.execute('''
                    INSERT INTO residential_complex (name, description, photo, location, finishing, improvement, smart_home, architecture, infrastructure, ecology)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    self.complex_name, self.complex_description, sqlite3.Binary(downloaded_file), "", "", "", "", "", "", ""
                ))

            self.bot.send_message(message.chat.id, f"Жилой комплекс '{self.complex_name}' добавлен.")
            self.show_admin_menu(message)
        else:
            self.bot.send_message(message.chat.id, "Пожалуйста, отправьте фото.")
            self.bot.register_next_step_handler(message, self.save_complex_photo)

    def add_apartment(self, message):
        self.bot.send_message(message.chat.id, "Выберите жилой комплекс для квартиры:")
        self.show_complex_list(message, callback=self.get_complex_id_for_apartment)

    def get_complex_id_for_apartment(self, message):
        complex_name = message.text
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM residential_complex WHERE name = ?", (complex_name,))
        complex_id = cursor.fetchone()
        if complex_id:
            self.current_complex_id = complex_id[0]
            self.bot.send_message(message.chat.id, "Отправьте фото планировки квартиры:")
            self.bot.register_next_step_handler(message, self.get_apartment_photo)
        else:
            self.bot.send_message(message.chat.id, "Жилой комплекс не найден. Попробуйте снова.")
            self.add_apartment(message)

    def get_apartment_photo(self, message):
        if message.photo:
            self.current_apartment['photo'] = message.photo[-1].file_id
            self.bot.send_message(message.chat.id, "Введите количество комнат:")
            self.bot.register_next_step_handler(message, self.get_apartment_rooms)
        else:
            self.bot.send_message(message.chat.id, "Пожалуйста, отправьте фото планировки.")
            self.bot.register_next_step_handler(message, self.get_apartment_photo)

    def get_apartment_rooms(self, message):
        self.current_apartment['rooms'] = message.text
        self.bot.send_message(message.chat.id, "Добавьте описание к квартире/дому:")
        self.bot.register_next_step_handler(message, self.get_apartment_description)

    def get_apartment_description(self, message):
        self.current_apartment['description'] = message.text
        self.bot.send_message(message.chat.id, "Введите цену квартиры/дома:")
        self.bot.register_next_step_handler(message, self.get_apartment_price)

    def get_apartment_price(self, message):
        self.current_apartment['price'] = message.text
        self.show_apartment_confirmation_menu(message)

    def show_apartment_confirmation_menu(self, message):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn_save = types.KeyboardButton('Сохранить')
        btn_cancel = types.KeyboardButton('Отменить')
        btn_back = types.KeyboardButton('Назад')
        keyboard.add(btn_save, btn_cancel, btn_back)
        self.bot.send_message(message.chat.id, "Проверьте данные и выберите действие:", reply_markup=keyboard)
        self.bot.register_next_step_handler(message, self.confirm_apartment_action)

    def confirm_apartment_action(self, message):
        if message.text == 'Сохранить':
            self.save_apartment()
            self.bot.send_message(message.chat.id, "Квартира успешно добавлена.")
            self.show_admin_menu(message)
        elif message.text == 'Отменить':
            self.current_apartment.clear()
            self.bot.send_message(message.chat.id, "Добавление квартиры отменено.")
            self.add_apartment(message)
        elif message.text == 'Назад':
            self.show_admin_menu(message)

    def save_apartment(self):
        file_info = self.bot.get_file(self.current_apartment['photo'])
        downloaded_file = self.bot.download_file(file_info.file_path)
        with self.conn:
            self.conn.execute('''
                INSERT INTO apartments (photo, rooms, description, price, residential_complex_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                sqlite3.Binary(downloaded_file),
                self.current_apartment['rooms'],
                self.current_apartment['description'],
                self.current_apartment['price'],
                self.current_complex_id
            ))
        self.current_apartment.clear()

    def delete_apartment(self, message):
        self.bot.send_message(message.chat.id, "Выберите жилой комплекс для удаления квартиры:")
        self.show_complex_list(message, callback=self.get_complex_id_for_deletion)

    def get_complex_id_for_deletion(self, message):
        complex_name = message.text
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM residential_complex WHERE name = ?", (complex_name,))
        complex_id = cursor.fetchone()
        if complex_id:
            self.current_complex_id = complex_id[0]
            self.show_apartment_list_for_deletion(message)
        else:
            self.bot.send_message(message.chat.id, "Жилой комплекс не найден. Попробуйте снова.")
            self.delete_apartment(message)

    def show_apartment_list_for_deletion(self, message):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, rooms FROM apartments WHERE residential_complex_id = ?", (self.current_complex_id,))
        apartments = cursor.fetchall()
        if not apartments:
            self.bot.send_message(message.chat.id, "Нет добавленных квартир в этом жилом комплексе.")
            self.show_admin_menu(message)
            return

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        room_map = {1: 'Однокомнатная', 2: 'Двухкомнатная', 3: 'Трехкомнатная', 4: 'Четырехкомнатная'}
        for apartment_id, rooms in apartments:
            keyboard.add(types.KeyboardButton(room_map.get(rooms, f'{rooms}-комнатная')))
        keyboard.add(types.KeyboardButton('Назад'))

        self.bot.send_message(message.chat.id, "Выберите квартиру для удаления:", reply_markup=keyboard)
        self.bot.register_next_step_handler(message, self.confirm_delete_apartment)

    def confirm_delete_apartment(self, message):
        room_map = {'Однокомнатная': 1, 'Двухкомнатная': 2, 'Трехкомнатная': 3, 'Четырехкомнатная': 4}
        rooms = room_map.get(message.text)
        if rooms:
            cursor = self.conn.cursor()
            cursor.execute("SELECT id FROM apartments WHERE residential_complex_id = ? AND rooms = ?", (self.current_complex_id, rooms))
            apartment_id = cursor.fetchone()
            if apartment_id:
                with self.conn:
                    self.conn.execute("DELETE FROM apartments WHERE id = ?", (apartment_id[0],))
                self.bot.send_message(message.chat.id, f"Квартира '{message.text}' удалена.")
                self.show_admin_menu(message)
            else:
                self.bot.send_message(message.chat.id, "Квартира не найдена.")
                self.show_apartment_list_for_deletion(message)
        elif message.text == 'Назад':
            self.show_admin_menu(message)
        else:
            self.bot.send_message(message.chat.id, "Неверный выбор. Попробуйте снова.")
            self.show_apartment_list_for_deletion(message)

    def show_admin_menu(self, message):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton('Включить бота')
        btn2 = types.KeyboardButton('Выключить бота')
        btn3 = types.KeyboardButton('Отправить уведомление')
        btn4 = types.KeyboardButton('Добавить жилой комплекс')
        btn5 = types.KeyboardButton('Удалить жилой комплекс')
        btn6 = types.KeyboardButton('Показать жилые комплексы')
        btn7 = types.KeyboardButton('Добавить квартиру')
        btn8 = types.KeyboardButton('Удалить квартиру')
        keyboard.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7, btn8)

        self.bot.send_message(message.chat.id, "Выберите опцию:", reply_markup=keyboard)

    def show_complex_list(self, message, callback=None):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name FROM residential_complex")
        complexes = cursor.fetchall()
        if not complexes:
            self.bot.send_message(message.chat.id, "Нет добавленных жилых комплексов.")
            return

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for complex_id, complex_name in complexes:
            keyboard.add(types.KeyboardButton(complex_name))
        keyboard.add(types.KeyboardButton('Назад'))

        self.bot.send_message(message.chat.id, "Выберите жилой комплекс:", reply_markup=keyboard)
        if callback:
            self.bot.register_next_step_handler(message, callback)

    def delete_complex(self, message):
        self.bot.send_message(message.chat.id, "Введите название жилого комплекса для удаления:")
        self.bot.register_next_step_handler(message, self.confirm_delete_complex)

    def confirm_delete_complex(self, message):
        complex_name = message.text
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM residential_complex WHERE name = ?", (complex_name,))
        complex_id = cursor.fetchone()
        if complex_id:
            with self.conn:
                self.conn.execute("DELETE FROM residential_complex WHERE id = ?", (complex_id[0],))
            self.bot.send_message(message.chat.id, f"Жилой комплекс '{complex_name}' удален.")
            self.show_admin_menu(message)
        else:
            self.bot.send_message(message.chat.id, "Жилой комплекс не найден. Попробуйте снова.")
            self.delete_complex(message)

    def send_complex_info(self, chat_id, complex_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT name, description, photo FROM residential_complex WHERE id = ?", (complex_id,))
        complex_info = cursor.fetchone()
        if complex_info:
            name, description, photo = complex_info
            self.bot.send_photo(chat_id, photo, caption=f"Название: {name}\nОписание: {description}")

    # def handle_complex_detail(self, message, detail_field):
    #     self.bot.send_message(message.chat.id, f"Введите новое значение для '{message.text}':")
    #     self.bot.register_next_step_handler(message, lambda msg: self.save_complex_detail(msg, detail_field))
    #
    # def save_complex_detail(self, message, detail_field):
    #     new_value = message.text
    #     with self.conn:
    #         self.conn.execute(f"UPDATE residential_complex SET {detail_field} = ? WHERE id = ?",
    #                           (new_value, self.current_complex_id))
    #     self.bot.send_message(message.chat.id, f"Поле '{detail_field}' обновлено.")
    #     self.show_complex_menu(message, self.current_complex_id)
    #
    # def show_complex_menu(self, message, complex_id):
    #     self.current_complex_id = complex_id
    #     keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    #     btn1 = types.KeyboardButton('Расположение')
    #     btn2 = types.KeyboardButton('Отделка')
    #     btn3 = types.KeyboardButton('Благоустройство')
    #     btn4 = types.KeyboardButton('Умный дом')
    #     btn5 = types.KeyboardButton('Архитектура')
    #     btn6 = types.KeyboardButton('Инфраструктура')
    #     btn7 = types.KeyboardButton('Экология')
    #     btn8 = types.KeyboardButton('Редактировать')
    #     btn9 = types.KeyboardButton('Подобрать квартиру')
    #     btn10 = types.KeyboardButton('Назад')
    #     keyboard.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7, btn8, btn9, btn10)
    #     self.bot.send_message(message.chat.id, "1Выберите опцию для редактирования:", reply_markup=keyboard)
    #     self.bot.register_next_step_handler(message, self.handle_complex_menu_selection)
    # def handle_complex_menu_selection(self, message):
    #     field_map = {
    #         'Расположение': 'location',
    #         'Отделка': 'finishing',
    #         'Благоустройство': 'improvement',
    #         'Умный дом': 'smart_home',
    #         'Архитектура': 'architecture',
    #         'Инфраструктура': 'infrastructure',
    #         'Экология': 'ecology'
    #     }
    #     if message.text in field_map:
    #         field = field_map[message.text]
    #         cursor = self.conn.cursor()
    #         cursor.execute(f"SELECT {field} FROM residential_complex WHERE id = ?", (self.current_complex_id,))
    #         field_value = cursor.fetchone()[0]
    #         if not field_value:
    #             self.bot.send_message(message.chat.id, f"Поле '{message.text}' пусто.")
    #         else:
    #             self.bot.send_message(message.chat.id, f"{message.text}: {field_value}")
    #     elif message.text == 'Редактировать':
    #         self.show_edit_menu(message)
    #     elif message.text == 'Подобрать квартиру':
    #         self.show_apartment_selection_menu(message)
    #     elif message.text == 'Назад':
    #         self.show_admin_menu(message)
    #     else:
    #         self.bot.send_message(message.chat.id, "Неверный выбор. Попробуйте снова.")
    #         self.show_complex_menu(message, self.current_complex_id)
    #
    # def show_edit_menu(self, message):
    #     keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    #     btn1 = types.KeyboardButton('Расположение')
    #     btn2 = types.KeyboardButton('Отделка')
    #     btn3 = types.KeyboardButton('Благоустройство')
    #     btn4 = types.KeyboardButton('Умный дом')
    #     btn5 = types.KeyboardButton('Архитектура')
    #     btn6 = types.KeyboardButton('Инфраструктура')
    #     btn7 = types.KeyboardButton('Экология')
    #     btn8 = types.KeyboardButton('Назад')
    #     keyboard.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7, btn8)
    #     self.bot.send_message(message.chat.id, "Выберите опцию для редактирования:", reply_markup=keyboard)
    #     self.bot.register_next_step_handler(message, self.handle_complex_detail)

    def handle_complex_detail(self, message, detail_field):
        self.bot.send_message(message.chat.id, f"Введите новое значение для '{detail_field}':")
        self.bot.register_next_step_handler(message, lambda msg: self.save_complex_detail(msg, detail_field))

    def save_complex_detail(self, message, detail_field):
        new_value = message.text
        try:
            with self.conn:
                self.conn.execute(f"UPDATE residential_complex SET {detail_field} = ? WHERE id = ?",
                                  (new_value, self.current_complex_id))
            self.bot.send_message(message.chat.id, f"Поле '{detail_field}' обновлено.")
        except sqlite3.Error as e:
            self.bot.send_message(message.chat.id, f"Ошибка при обновлении поля '{detail_field}': {e}")
        self.show_complex_menu(message, self.current_complex_id)

    def show_complex_menu(self, message, complex_id):
        self.current_complex_id = complex_id
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        options = ['Расположение', 'Отделка', 'Благоустройство', 'Умный дом', 'Архитектура', 'Инфраструктура',
                   'Экология', 'Редактировать', 'Подобрать квартиру', 'Назад']

        # Располагаем кнопки в несколько рядов
        row_width = 2
        keyboard.add(*[types.KeyboardButton(option) for option in options[:row_width]])
        keyboard.add(*[types.KeyboardButton(option) for option in options[row_width:2 * row_width]])
        keyboard.add(*[types.KeyboardButton(option) for option in options[2 * row_width:3 * row_width]])
        keyboard.add(*[types.KeyboardButton(option) for option in options[3 * row_width:4 * row_width]])
        keyboard.add(*[types.KeyboardButton(option) for option in options[4 * row_width:]])

        self.bot.send_message(message.chat.id, "Выберите опцию для просмотра:", reply_markup=keyboard)
        self.bot.register_next_step_handler(message, self.handle_complex_menu_selection)

    def handle_complex_menu_selection(self, message):
        field_map = {
            'Расположение': 'location',
            'Отделка': 'finishing',
            'Благоустройство': 'improvement',
            'Умный дом': 'smart_home',
            'Архитектура': 'architecture',
            'Инфраструктура': 'infrastructure',
            'Экология': 'ecology'
        }
        selected_option = message.text
        if selected_option in field_map:
            field = field_map[selected_option]
            try:
                cursor = self.conn.cursor()
                cursor.execute(f"SELECT {field} FROM residential_complex WHERE id = ?", (self.current_complex_id,))
                field_value = cursor.fetchone()[0]
                if not field_value:
                    self.bot.send_message(message.chat.id, f"Поле '{selected_option}' пусто.")
                else:
                    self.bot.send_message(message.chat.id, f"{selected_option}: {field_value}")
            except sqlite3.Error as e:
                self.bot.send_message(message.chat.id, f"Ошибка при получении данных: {e}")
            self.show_complex_menu(message, self.current_complex_id)
        elif selected_option == 'Редактировать':
            self.show_edit_menu(message)
        elif selected_option == 'Подобрать квартиру':
            self.show_apartment_selection_menu(message)
        elif selected_option == 'Назад':
            self.show_admin_menu(message)
        else:
            self.bot.send_message(message.chat.id, "Неверный выбор. Попробуйте снова.")
            self.show_complex_menu(message, self.current_complex_id)

    def show_edit_menu(self, message):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        options = ['Расположение', 'Отделка', 'Благоустройство', 'Умный дом', 'Архитектура', 'Инфраструктура',
                   'Экология', 'Назад']

        # Располагаем кнопки в несколько рядов
        row_width = 2
        keyboard.add(*[types.KeyboardButton(option) for option in options[:row_width]])
        keyboard.add(*[types.KeyboardButton(option) for option in options[row_width:2 * row_width]])
        keyboard.add(*[types.KeyboardButton(option) for option in options[2 * row_width:]])

        self.bot.send_message(message.chat.id, "Выберите опцию для редактирования:", reply_markup=keyboard)
        self.bot.register_next_step_handler(message, self.handle_complex_detail_selection)

    def handle_complex_detail_selection(self, message):
        field_map = {
            'Расположение': 'location',
            'Отделка': 'finishing',
            'Благоустройство': 'improvement',
            'Умный дом': 'smart_home',
            'Архитектура': 'architecture',
            'Инфраструктура': 'infrastructure',
            'Экология': 'ecology'
        }
        selected_option = message.text
        if selected_option in field_map:
            self.handle_complex_detail(message, field_map[selected_option])
        elif selected_option == 'Назад':
            self.show_complex_menu(message, self.current_complex_id)
        else:
            self.bot.send_message(message.chat.id, "Неверный выбор. Попробуйте снова.")
            self.show_edit_menu(message)

    def show_apartment_selection_menu(self, message):
        cursor = self.conn.cursor()
        cursor.execute("SELECT rooms FROM apartments WHERE residential_complex_id = ?", (self.current_complex_id,))
        apartments = cursor.fetchall()
        if not apartments:
            self.bot.send_message(message.chat.id, "Нет добавленных квартир в этом жилом комплексе.")
            self.show_complex_menu(message, self.current_complex_id)
            return

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        room_map = {1: 'Однокомнатная', 2: 'Двухкомнатная', 3: 'Трехкомнатная', 4: 'Четырехкомнатная'}
        added_rooms = set()
        for rooms, in apartments:
            if rooms not in added_rooms:
                added_rooms.add(rooms)
                keyboard.add(types.KeyboardButton(room_map.get(rooms, f'{rooms}-комнатная')))
        keyboard.add(types.KeyboardButton('Назад'))

        self.bot.send_message(message.chat.id, "Выберите тип квартиры:", reply_markup=keyboard)
        self.bot.register_next_step_handler(message, self.handle_apartment_selection)

    def handle_apartment_selection(self, message):
        room_map = {'Однокомнатная': 1, 'Двухкомнатная': 2, 'Трехкомнатная': 3, 'Четырехкомнатная': 4}
        rooms = room_map.get(message.text)
        if rooms:
            cursor = self.conn.cursor()
            cursor.execute("SELECT photo, rooms, description, price FROM apartments WHERE residential_complex_id = ? AND rooms = ?", (self.current_complex_id, rooms))
            apartment = cursor.fetchone()
            if apartment:
                photo, rooms, description, price = apartment
                self.bot.send_photo(message.chat.id, photo, caption=f"Количество комнат: {rooms}\nОписание: {description}\nЦена: {price}")
                self.show_apartment_selection_menu(message)
            else:
                self.bot.send_message(message.chat.id, "Квартира не найдена.")
                self.show_apartment_selection_menu(message)
        elif message.text == 'Назад':
            self.show_complex_menu(message, self.current_complex_id)
        else:
            self.bot.send_message(message.chat.id, "Неверный выбор. Попробуйте снова.")
            self.show_apartment_selection_menu(message)

class AdminBotHandler:
    def __init__(self, bot):
        self.bot = bot
        self.residential_complex_handler = ResidentialComplexHandler(bot)
        self.main_bot_active = True

        @bot.message_handler(commands=['start'])
        def send_welcome(message):
            if message.chat.id == ADMIN_ID:
                self.residential_complex_handler.show_admin_menu(message)
            else:
                bot.send_message(message.chat.id, "У вас нет доступа к этому боту.")

        @bot.message_handler(func=lambda message: message.chat.id == ADMIN_ID)
        def handle_admin_commands(message):
            if message.text == 'Включить бота':
                self.main_bot_active = True
                bot.send_message(message.chat.id, "Основной бот включен.")
            elif message.text == 'Выключить бота':
                self.main_bot_active = False
                bot.send_message(message.chat.id, "Основной бот выключен.")
            elif message.text == 'Отправить уведомление':
                bot.send_message(message.chat.id, "Введите сообщение для отправки всем пользователям:")
                bot.register_next_step_handler(message, self.send_notification)
            elif message.text == 'Добавить жилой комплекс':
                self.residential_complex_handler.add_complex(message)
            elif message.text == 'Удалить жилой комплекс':
                self.residential_complex_handler.delete_complex(message)
            elif message.text == 'Показать жилые комплексы':
                self.residential_complex_handler.show_complex_list(message)
            elif message.text == 'Добавить квартиру':
                self.residential_complex_handler.add_apartment(message)
            elif message.text == 'Удалить квартиру':
                self.residential_complex_handler.delete_apartment(message)
            elif message.text == 'Назад':
                self.residential_complex_handler.show_admin_menu(message)
            elif message.text == 'Подобрать квартиру':
                self.residential_complex_handler.show_apartment_selection_menu(message)
            else:
                cursor = self.residential_complex_handler.conn.cursor()
                cursor.execute("SELECT id FROM residential_complex WHERE name = ?", (message.text,))
                complex_id = cursor.fetchone()
                if complex_id:
                    self.residential_complex_handler.send_complex_info(message.chat.id, complex_id[0])
                    self.residential_complex_handler.show_complex_menu(message, complex_id[0])
                else:
                    field_map = {
                        'Расположение': 'location',
                        'Отделка': 'finishing',
                        'Благоустройство': 'improvement',
                        'Умный дом': 'smart_home',
                        'Архитектура': 'architecture',
                        'Инфраструктура': 'infrastructure',
                        'Экология': 'ecology'
                    }
                    if message.text in field_map:
                        self.residential_complex_handler.handle_complex_detail(message, field_map[message.text])
                    elif message.text == 'Редактировать':
                        self.residential_complex_handler.show_edit_menu(message)

class MainBotHandler:
    def __init__(self, bot, admin_bot_handler):
        self.bot = bot
        self.admin_bot_handler = admin_bot_handler
        self.feedback_handler = FeedbackHandler(bot)
        self.residential_complex_handler = ResidentialComplexHandler(bot)
        self.current_complex_id = None
        self.current_selection_mode = None  # Указывает режим выбора: "complex" или "apartment"

        @bot.message_handler(commands=['start'])
        def send_welcome_main(message):
            if self.admin_bot_handler.main_bot_active:
                self.show_main_menu(message.chat.id)
            else:
                self.bot.send_message(message.chat.id, "Извините, бот временно не доступен.")

        @bot.message_handler(func=lambda message: self.admin_bot_handler.main_bot_active and message.text == '📞 Запрос обратной связи')
        def handle_feedback_button(message):
            self.feedback_handler.start_feedback(message)

        @bot.message_handler(func=lambda message: self.admin_bot_handler.main_bot_active and message.text == '🏢 Жилой комплекс')
        def handle_complex_button(message):
            self.show_complex_menu(message.chat.id)

        @bot.message_handler(func=lambda message: self.admin_bot_handler.main_bot_active and message.text == '🏠 Подобрать квартиру')
        def handle_select_apartment_button(message):
            self.current_selection_mode = 'apartment'
            self.show_complex_menu(message.chat.id)

        @bot.message_handler(func=lambda message: self.admin_bot_handler.main_bot_active and message.text == 'Назад')
        def handle_back_button(message):
            self.current_selection_mode = None
            self.show_main_menu(message.chat.id)

        @bot.message_handler(func=lambda message: self.admin_bot_handler.main_bot_active and message.text in self.get_complex_names())
        def handle_complex_selection(message):
            complex_name = message.text
            cursor = self.residential_complex_handler.conn.cursor()
            cursor.execute("SELECT id FROM residential_complex WHERE name = ?", (complex_name,))
            complex_id = cursor.fetchone()
            if complex_id:
                self.current_complex_id = complex_id[0]
                if self.current_selection_mode == 'apartment':
                    self.show_apartment_selection_menu(message.chat.id)
                else:
                    self.residential_complex_handler.send_complex_info(message.chat.id, self.current_complex_id)
                    self.show_complex_details_menu(message.chat.id, self.current_complex_id)

        @bot.message_handler(func=lambda message: self.admin_bot_handler.main_bot_active and message.text in ['Расположение', 'Отделка', 'Благоустройство', 'Умный дом', 'Архитектура', 'Инфраструктура', 'Экология'])
        def handle_complex_detail(message):
            if self.current_complex_id:
                field_map = {
                    'Расположение': 'location',
                    'Отделка': 'finishing',
                    'Благоустройство': 'improvement',
                    'Умный дом': 'smart_home',
                    'Архитектура': 'architecture',
                    'Инфраструктура': 'infrastructure',
                    'Экология': 'ecology'
                }
                field = field_map[message.text]
                cursor = self.residential_complex_handler.conn.cursor()
                cursor.execute(f"SELECT {field} FROM residential_complex WHERE id = ?", (self.current_complex_id,))
                field_value = cursor.fetchone()[0]
                if not field_value:
                    self.bot.send_message(message.chat.id, f"Поле '{message.text}' пусто.")
                else:
                    self.bot.send_message(message.chat.id, f"{message.text}: {field_value}")

        @bot.message_handler(func=lambda message: self.admin_bot_handler.main_bot_active and message.text in ['Однокомнатная', 'Двухкомнатная', 'Трехкомнатная', 'Четырехкомнатная'])
        def handle_apartment_selection(message):
            if self.current_complex_id:
                room_map = {'Однокомнатная': 1, 'Двухкомнатная': 2, 'Трехкомнатная': 3, 'Четырехкомнатная': 4}
                rooms = room_map.get(message.text)
                if rooms:
                    cursor = self.residential_complex_handler.conn.cursor()
                    cursor.execute("SELECT photo, rooms, description, price FROM apartments WHERE residential_complex_id = ? AND rooms = ?", (self.current_complex_id, rooms))
                    apartment = cursor.fetchone()
                    if apartment:
                        photo, rooms, description, price = apartment
                        self.bot.send_photo(message.chat.id, photo, caption=f"Количество комнат: {rooms}\nОписание: {description}\nЦена: {price}")
                    else:
                        self.bot.send_message(message.chat.id, "Квартира не найдена.")
                elif message.text == 'Назад':
                    self.show_main_menu(message.chat.id)
            else:
                self.bot.send_message(message.chat.id, "Пожалуйста, выберите жилой комплекс сначала.")

    def show_main_menu(self, chat_id):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton('🏢 Жилой комплекс')
        btn2 = types.KeyboardButton('🏠 Подобрать квартиру')
        btn3 = types.KeyboardButton('💼 Текущие акции и предложения')
        btn4 = types.KeyboardButton('📞 Запрос обратной связи')
        btn5 = types.KeyboardButton('❓ Часто задаваемые вопросы (FAQ)')
        keyboard.add(btn1, btn2)
        keyboard.add(btn3)
        keyboard.add(btn4, btn5)
        welcome_message = (
            "🎉 <b>Добро пожаловать!</b> 🎉\n\n"
            "Приветствуем вас в нашем боте по подбору квартир! 🏠\n\n"
            "Выберите один из пунктов меню, чтобы продолжить."
        )
        self.bot.send_message(chat_id, welcome_message, reply_markup=keyboard)

    def show_complex_menu(self, chat_id):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        cursor = self.residential_complex_handler.conn.cursor()
        cursor.execute("SELECT name FROM residential_complex")
        complex_names = [name for (name,) in cursor.fetchall()]
        for name in complex_names:
            keyboard.add(types.KeyboardButton(name))
        keyboard.add(types.KeyboardButton('Назад'))
        self.bot.send_message(chat_id, "Выберите жилой комплекс:", reply_markup=keyboard)

    def show_complex_details_menu(self, chat_id, complex_id):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton('Расположение')
        btn2 = types.KeyboardButton('Отделка')
        btn3 = types.KeyboardButton('Благоустройство')
        btn4 = types.KeyboardButton('Умный дом')
        btn5 = types.KeyboardButton('Архитектура')
        btn6 = types.KeyboardButton('Инфраструктура')
        btn7 = types.KeyboardButton('Экология')
        btn8 = types.KeyboardButton('Назад')
        keyboard.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7, btn8)
        self.bot.send_message(chat_id, "Выберите категорию:", reply_markup=keyboard)

    def show_apartment_selection_menu(self, chat_id):
        cursor = self.residential_complex_handler.conn.cursor()
        cursor.execute("SELECT DISTINCT rooms FROM apartments WHERE residential_complex_id = ?", (self.current_complex_id,))
        apartments = cursor.fetchall()
        if not apartments:
            self.bot.send_message(chat_id, "Нет добавленных квартир в этом жилом комплексе.")
            self.show_complex_details_menu(chat_id, self.current_complex_id)
            return

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        room_map = {1: 'Однокомнатная', 2: 'Двухкомнатная', 3: 'Трехкомнатная', 4: 'Четырехкомнатная'}
        for rooms, in apartments:
            keyboard.add(types.KeyboardButton(room_map.get(rooms, f'{rooms}-комнатная')))
        keyboard.add(types.KeyboardButton('Назад'))

        self.bot.send_message(chat_id, "Выберите тип квартиры:", reply_markup=keyboard)

    def get_complex_names(self):
        cursor = self.residential_complex_handler.conn.cursor()
        cursor.execute("SELECT name FROM residential_complex")
        return [name for (name,) in cursor.fetchall()]


if __name__ == '__main__':
    admin_bot_handler = AdminBotHandler(admin_bot)
    main_bot_handler = MainBotHandler(main_bot, admin_bot_handler)
    from threading import Thread
    Thread(target=lambda: main_bot.polling(none_stop=True)).start()
    admin_bot.polling(none_stop=True)