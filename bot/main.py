import telebot
from telebot import types
import sqlite3
from config import *
import io

# Основной бот
main_bot = telebot.TeleBot(MAIN_BOT_TOKEN, parse_mode='HTML')

# Административный бот
admin_bot = telebot.TeleBot(ADMIN_BOT_TOKEN, parse_mode='HTML')

#Бот для приема заявок
feedback_bot = telebot.TeleBot(FEEDBACK_BOT_TOKEN, parse_mode='HTML')

class FeedbackBotHandler:
    def __init__(self, bot):
        self.bot = bot
        @bot.message_handler(commands=['start'])
        def send_welcome_main(message):
            if message.chat.id == ADMIN_ID:
                welcome_message = (
                    "🎉 <b>Добро пожаловать!</b> 🎉\n\n"
                )
                self.bot.send_message(message.chat.id, welcome_message)
            else:
                bot.send_message(message.chat.id, "У вас нет доступа к этому боту.")

class FeedbackHandler:
    def __init__(self, bot):
        self.bot = bot
        self.user_fio = None
        self.user_phone = None
        self.complex_name = None

    def start_feedback(self, message, complex_name=None):
        self.complex_name = complex_name
        self.bot.send_message(message.chat.id, "Пожалуйста, введите ваше ФИО:")
        self.bot.register_next_step_handler(message, self.get_fio)

    def get_fio(self, message):
        self.user_fio = message.text
        self.bot.send_message(message.chat.id, f'{self.user_fio}, введите пожалуйста свой номер телефона:')
        self.bot.register_next_step_handler(message, self.get_phone)

    def get_phone(self, message):
        self.user_phone = message.text
        feeback_message = f"Новый запрос обратной связи:\n\nФИО: {self.user_fio}\nНомер телефона: {self.user_phone}\n\nЖилой комплекс: {self.complex_name}"
        try:
            feedback_bot.send_message(ADMIN_ID, feeback_message)
        except Exception as e:
            self.bot.send_message(message.chat.id, f"Ошибка при отправке сообщения")
        else:
            self.bot.send_message(message.chat.id, "Спасибо! Ваш запрос был отправлен.")
# Класс для работы с жилыми комплексами
class ResidentialComplexHandler:
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('../data/tojsokhtmon.db', check_same_thread=False)
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
                    INSERT INTO residential_complex (name, description, photo)
                    VALUES (?, ?, ?)
                ''', (
                    self.complex_name, self.complex_description, sqlite3.Binary(downloaded_file)
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
        if message.text == 'Назад':
            self.show_admin_menu(message)
            return
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
        btn11 = types.KeyboardButton('Войти в админ панель tojsokhtmon.tj', web_app=types.WebAppInfo(url="https://tojsokhtmon.tj/login"))
        btn1 = types.KeyboardButton('Включить бота')
        btn2 = types.KeyboardButton('Выключить бота')
        btn3 = types.KeyboardButton('Добавить акцию')
        btn9 = types.KeyboardButton('Список акций')
        btn4 = types.KeyboardButton('Добавить жилой комплекс')
        btn5 = types.KeyboardButton('Удалить жилой комплекс')
        btn6 = types.KeyboardButton('Показать жилые комплексы')
        btn7 = types.KeyboardButton('Добавить квартиру')
        btn8 = types.KeyboardButton('Удалить квартиру')
        btn10 = types.KeyboardButton('Часто задаваемые вопросы (FAQ)')
        keyboard.add(btn11)
        keyboard.add(btn1, btn2, btn3, btn9, btn4, btn5, btn6, btn7, btn8, btn10)

        self.bot.send_message(message.chat.id, "Выберите опцию:", reply_markup=keyboard)

    def show_complex_list(self, message, callback=None):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name FROM residential_complex")
        complexes = cursor.fetchall()
        if not complexes:
            self.bot.send_message(message.chat.id, "Нет добавленных жилых комплексов.")
            return

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        row = []
        for i, (complex_id, complex_name) in enumerate(complexes, start=1):
            row.append(types.KeyboardButton(complex_name))
            if i % 3 == 0:
                keyboard.row(*row)
                row = []
        if row:
            keyboard.row(*row)

        keyboard.add(types.KeyboardButton('Назад'))

        self.bot.send_message(message.chat.id, "Выберите жилой комплекс:", reply_markup=keyboard)
        if callback:
            self.bot.register_next_step_handler(message, callback)

    def delete_complex(self, message):
        self.bot.send_message(message.chat.id, "Введите название жилого комплекса для удаления:")
        self.bot.register_next_step_handler(message, self.confirm_delete_complex)

    def confirm_delete_complex(self, message):
        if message.text == 'Назад':
            self.show_admin_menu(message)
            return

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
            self.bot.send_photo(chat_id, photo, caption=f"<b>{name}</b>\n\nОписание: {description}", parse_mode='HTML')

    def show_complex_menu(self, message, complex_id):
        self.current_complex_id = complex_id
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        options = ['Подобрать квартиру', 'Назад']

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

        selected_option = message.text
        if selected_option == 'Подобрать квартиру':
            self.show_apartment_selection_menu(message)
        elif selected_option == 'Назад':
            self.show_admin_menu(message)
        else:
            self.bot.send_message(message.chat.id, "Неверный выбор. Попробуйте снова.")
            self.show_complex_menu(message, self.current_complex_id)

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
                self.bot.send_photo(message.chat.id, photo, caption=f"<b>Количество комнат: {rooms}</b>\n\nОписание: {description}\n\n<b>Цена от: {price} сомон</b>", parse_mode='HTML')
                self.show_apartment_selection_menu(message)
            else:
                self.bot.send_message(message.chat.id, "Квартира не найдена.")
                self.show_apartment_selection_menu(message)
        elif message.text == 'Назад':
            self.show_complex_menu(message, self.current_complex_id)
        else:
            self.bot.send_message(message.chat.id, "Неверный выбор. Попробуйте снова.")
            self.show_apartment_selection_menu(message)

class PromotionHandler:
    def __init__(self, bot, residential_complex_handler):
        self.bot = bot
        self.residential_complex_handler = residential_complex_handler
        self.conn = sqlite3.connect('../data/tojsokhtmon.db', check_same_thread=False)
        self.promotion_title = None
        self.promotion_photo = None
        self.promotion_description = None
        self.current_promotion_id = None  # Для хранения ID текущей акции

    def start_promotion_creation(self, message):
        self.bot.send_message(message.chat.id, "Напишите название акции:")
        self.bot.register_next_step_handler(message, self.get_promotion_title)

    def get_promotion_title(self, message):
        self.promotion_title = message.text
        self.bot.send_message(message.chat.id, "Добавьте фото к акции (отправьте фото):")
        self.bot.register_next_step_handler(message, self.get_promotion_photo)

    def get_promotion_photo(self, message):
        if message.photo:
            file_id = message.photo[-1].file_id  # Получаем ID фото
            file_info = self.bot.get_file(file_id)  # Получаем информацию о файле

            try:
                downloaded_file = self.bot.download_file(file_info.file_path)  # Скачиваем файл
            except Exception as e:
                self.bot.send_message(message.chat.id, f"Ошибка при скачивании файла: {e}")
                return

            self.promotion_photo = sqlite3.Binary(downloaded_file)  # Преобразуем файл в бинарные данные
            self.bot.send_message(message.chat.id, "Добавьте описание к акции:")
            self.bot.register_next_step_handler(message, self.get_promotion_description)
        else:
            self.bot.send_message(message.chat.id, "Пожалуйста, отправьте фото, а не текст.")
            self.bot.register_next_step_handler(message, self.get_promotion_photo)

    def get_promotion_description(self, message):
        self.promotion_description = message.text

        # Сохраняем все данные в базу данных
        try:
            with self.conn:
                self.conn.execute('''
                    INSERT INTO promotions (title, photo, description) VALUES (?, ?, ?)
                ''', (self.promotion_title, self.promotion_photo, self.promotion_description))
            self.bot.send_message(message.chat.id, "Акция успешно добавлена!")
        except sqlite3.Error as e:
            self.bot.send_message(message.chat.id, f"Ошибка при добавлении акции: {e}")

    def show_promotion_list(self, message):
        if message.text == 'Назад':
            self.residential_complex_handler.show_admin_menu(message)
            return
        elif message.text == 'Удалить акцию':
            self.delete_promotion(message)
            return

        try:
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute("SELECT id, title FROM promotions")
                promotions = cursor.fetchall()
        except sqlite3.Error as e:
            self.bot.send_message(message.chat.id, f"Ошибка при получении списка акций: {e}")
            return

        if promotions:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            row = []
            for promo in promotions:
                row.append(types.KeyboardButton(promo[1]))
                if len(row) == 3:
                    markup.add(*row)
                    row = []
            if row:
                markup.add(*row)
            markup.add(types.KeyboardButton("Назад"))
            markup.add(types.KeyboardButton("Удалить акцию"))

            self.bot.send_message(message.chat.id, "Выберите акцию:", reply_markup=markup)
            self.bot.register_next_step_handler(message, self.process_selected_action)
        else:
            self.bot.send_message(message.chat.id, "Акций пока нет.", reply_markup=types.ReplyKeyboardRemove())
            self.residential_complex_handler.show_admin_menu(message)

    def process_selected_action(self, message):
        if message.text == 'Назад':
            self.residential_complex_handler.show_admin_menu(message)
        elif message.text == 'Удалить акцию':
            self.delete_promotion(message)
        else:
            self.show_promotion_details(message)
            # После отображения деталей акции снова показывайте список акций
            self.show_promotion_list(message)

    def show_promotion_details(self, message):
        try:
            with sqlite3.connect('../data/tojsokhtmon.db') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT photo, description FROM promotions WHERE title = ?", (message.text,))
                promotion = cursor.fetchone()
        except sqlite3.Error as e:
            self.bot.send_message(message.chat.id, f"Ошибка при получении данных акции: {e}")
            return

        if promotion:
            photo, description = promotion
            if photo:
                photo_stream = io.BytesIO(photo)  # Преобразуем бинарные данные в поток
                photo_stream.seek(0)  # Убедимся, что указатель находится в начале потока

                self.bot.send_photo(message.chat.id, photo_stream, caption=f"{message.text}\n\n{description}")
            else:
                self.bot.send_message(message.chat.id, f"{message.text}\n\n{description}")
        else:
            self.bot.send_message(message.chat.id, "Акция не найдена.")

    def delete_promotion(self, message):
        if message.text == 'Назад':
            self.show_promotion_list(message)
            return

        try:
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute("SELECT id, title FROM promotions")
                promotions = cursor.fetchall()

            if promotions:
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                for promo in promotions:
                    markup.add(types.KeyboardButton(promo[1]))  # Название акции как кнопка для удаления
                markup.add(types.KeyboardButton("Назад"))

                self.bot.send_message(message.chat.id, "Выберите акцию для удаления:", reply_markup=markup)
                self.bot.register_next_step_handler(message, self.delete_selected_promotion)
            else:
                self.bot.send_message(message.chat.id, "Нет акций для удаления.",
                                      reply_markup=types.ReplyKeyboardRemove())
                self.residential_complex_handler.show_admin_menu(message)
        except sqlite3.Error as e:
            self.bot.send_message(message.chat.id, f"Ошибка при получении списка акций: {e}")

    def delete_selected_promotion(self, message):
        promotion_title = message.text
        try:
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM promotions WHERE title = ?", (promotion_title,))
                self.conn.commit()
            self.bot.send_message(message.chat.id, f"Акция '{promotion_title}' была удалена.")
        except sqlite3.Error as e:
            self.bot.send_message(message.chat.id, f"Ошибка при удалении акции: {e}")

        self.show_promotion_list(message)  # Показываем обновленный список акций

class FAQHandler:
    def __init__(self, bot, residential_complex_handler):
        self.bot = bot
        self.conn = sqlite3.connect('../data/tojsokhtmon.db', check_same_thread=False)
        self.residential_complex_handler = residential_complex_handler
        self.current_faq_title = None  # Для хранения текущего заголовка FAQ

    def show_faq_menu(self, message):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, title FROM faq")
        faqs = cursor.fetchall()

        if not faqs:
            markup = self._get_empty_faq_menu_markup()
            self.bot.send_message(message.chat.id, "Вопросы не добавлены.", reply_markup=markup)
            # return markup
            # self.bot.register_next_step_handler(message, self._get_empty_faq_menu_markup)
        else:
            markup = self._get_faq_menu_markup(faqs)
            self.bot.send_message(message.chat.id, "Выберите вопрос для просмотра или управления FAQ:", reply_markup=markup)
            self.bot.register_next_step_handler(message, self._handle_faq_menu_selection)

    def _get_empty_faq_menu_markup(self):
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add('Добавить вопрос', 'Назад')
        return markup

    def _get_faq_menu_markup(self, faqs):
        markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
        for faq in faqs:
            markup.add(faq[1])  # Добавляем названия вопросов как кнопки
        markup.add('Добавить вопрос', 'Удалить вопрос', 'Назад')
        return markup

    def _handle_faq_menu_selection(self, message):
        if message.text == 'Добавить вопрос':
            self.add_faq(message)
        elif message.text == 'Удалить вопрос':
            self.delete_faq(message)
        elif message.text == 'Назад':
            self.handle_back(message)
        else:
            # Обработка выбора конкретного FAQ
            self.send_faq_details(message, message.text)

    def add_faq(self, message):
        self.bot.send_message(message.chat.id, "Введите вопрос:")
        self.bot.register_next_step_handler(message, self._save_faq_title)

    def _save_faq_title(self, message):
        self.current_faq_title = message.text
        self.bot.send_message(message.chat.id, "Введите ответ на вопрос:")
        self.bot.register_next_step_handler(message, self._save_faq_description)

    def _save_faq_description(self, message):
        faq_description = message.text
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO faq (title, description) VALUES (?, ?)", (self.current_faq_title, faq_description))
        self.conn.commit()
        self.bot.send_message(message.chat.id, "Вопрос добавлен.")
        self.show_faq_menu(message)

    def delete_faq(self, message):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, title FROM faq")
        faqs = cursor.fetchall()

        if not faqs:
            self.bot.send_message(message.chat.id, "Нет вопросов для удаления.")
            self.show_faq_menu(message)
            return

        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        for faq in faqs:
            markup.add(faq[1])  # Название вопроса как кнопка для удаления
        markup.add('Назад')
        self.bot.send_message(message.chat.id, "Выберите вопрос для удаления:", reply_markup=markup)
        self.bot.register_next_step_handler(message, self._confirm_faq_deletion)

    def _confirm_faq_deletion(self, message):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM faq WHERE title = ?", (message.text,))
        faq_id = cursor.fetchone()
        if faq_id:
            cursor.execute("DELETE FROM faq WHERE id = ?", (faq_id[0],))
            self.conn.commit()
            self.bot.send_message(message.chat.id, "Вопрос удален.")
        else:
            self.bot.send_message(message.chat.id, "Вопрос не найден.")
        self.show_faq_menu(message)

    def send_faq_details(self, message, faq_title):
        cursor = self.conn.cursor()
        cursor.execute("SELECT title, description FROM faq WHERE title = ?", (faq_title,))
        faq = cursor.fetchone()
        if faq:
            self.bot.send_message(message.chat.id, f"{faq[0]}\n\n{faq[1]}")
        else:
            self.bot.send_message(message.chat.id, "Вопрос не найден.")
        self.show_faq_menu(message)

    def handle_back(self, message):
        self.residential_complex_handler.show_admin_menu(message)

class AdminBotHandler:
    def __init__(self, bot):
        self.bot = bot
        self.residential_complex_handler = ResidentialComplexHandler(bot)
        self.promotion_handler = PromotionHandler(bot, self.residential_complex_handler)
        self.faq_handler = FAQHandler(bot, self.residential_complex_handler)
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
            elif message.text == 'Добавить акцию':
                self.promotion_handler.start_promotion_creation(message)
            elif message.text == 'Список акций':
                self.promotion_handler.show_promotion_list(message)
            elif message.text == 'Удалить акцию':
                self.promotion_handler.delete_promotion(message)
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
            elif message.text == 'Часто задаваемые вопросы (FAQ)':
                self.faq_handler.show_faq_menu(message)
            elif message.text == 'Добавить вопрос':
                self.faq_handler.add_faq(message)
            elif message.text == 'Удалить вопрос':
                self.faq_handler.delete_faq(message)
            else:
                cursor = self.residential_complex_handler.conn.cursor()
                cursor.execute("SELECT id FROM residential_complex WHERE name = ?", (message.text,))
                complex_id = cursor.fetchone()
                if complex_id:
                    self.residential_complex_handler.send_complex_info(message.chat.id, complex_id[0])
                    self.residential_complex_handler.show_complex_menu(message, complex_id[0])

class MainBotHandler:
    def __init__(self, bot, admin_bot_handler):
        self.bot = bot
        self.admin_bot_handler = admin_bot_handler
        self.feedback_handler = FeedbackHandler(bot)
        self.residential_complex_handler = ResidentialComplexHandler(bot)
        self.promotion_handler = PromotionHandler(bot, self.residential_complex_handler)
        self.current_complex_id = None
        self.current_selection_mode = None  # Указывает режим выбора: "complex" или "apartment"

        @bot.message_handler(commands=['start'])
        def send_welcome_main(message):
            if self.admin_bot_handler.main_bot_active:
                self.show_main_menu(message.chat.id)
                welcome_message = (
                    "🎉 <b>Добро пожаловать!</b> 🎉\n\n"
                    "Приветствуем вас в нашем боте по подбору квартир! 🏠\n\n"
                    "Выберите один из пунктов меню, чтобы продолжить."
                )
                self.bot.send_message(message.chat.id, welcome_message)
            else:
                self.bot.send_message(message.chat.id, "Извините, бот временно не доступен.")

        @bot.message_handler(
            func=lambda message: self.admin_bot_handler.main_bot_active and message.text == '📞 Запрос обратной связи')
        def handle_feedback_button(message):
            self.feedback_handler.start_feedback(message)

        @bot.message_handler(
            func=lambda message: self.admin_bot_handler.main_bot_active and message.text == '💼 Текущие акции и предложения')
        def handle_promotion_button(message):
            self.show_promotion_list(message)

        @bot.message_handler(
            func=lambda
                    message: self.admin_bot_handler.main_bot_active and message.text == '❓ Часто задаваемые вопросы (FAQ)')
        def handle_faq_button(message):
            self.show_faq_menu(message)

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
            complex_id = self.get_complex_id_by_name(complex_name)
            if complex_id:
                self.current_complex_id = complex_id
                if self.current_selection_mode == 'apartment':
                    self.show_apartment_selection_menu(message.chat.id)
                else:
                    self.residential_complex_handler.send_complex_info(message.chat.id, self.current_complex_id)
                    self.show_complex_details_menu(message.chat.id, self.current_complex_id)
            else:
                self.bot.send_message(message.chat.id, "Не удалось найти выбранный жилой комплекс.")

        @bot.message_handler(
            func=lambda message: self.admin_bot_handler.main_bot_active and message.text == 'Выбрать квартиру')
        def handle_complex_detail_select_apartments(message):
            self.show_apartment_selection_menu(message.chat.id)

        @bot.message_handler(
            func=lambda message: self.admin_bot_handler.main_bot_active and message.text == 'Оставить заявку')
        def handle_complex_detail_feedback(message):
            complex_name = self.get_complex_field_value(self.current_complex_id, 'name')
            self.feedback_handler.start_feedback(message, complex_name)

        @bot.message_handler(func=lambda message: self.admin_bot_handler.main_bot_active and message.text in ['Однокомнатная', 'Двухкомнатная', 'Трехкомнатная', 'Четырехкомнатная'])
        def handle_apartment_selection(message):
            if self.current_complex_id:
                room_map = {'Однокомнатная': 1, 'Двухкомнатная': 2, 'Трехкомнатная': 3, 'Четырехкомнатная': 4}
                rooms = room_map.get(message.text)
                if rooms:
                    apartment = self.get_apartment(self.current_complex_id, rooms)
                    if apartment:
                        photo, rooms, description, price = apartment
                        self.bot.send_photo(message.chat.id, photo, caption=f"<b>Количество комнат: {rooms}</b>\n\nОписание: {description}\n\n<b>Цена от: {price} сомон</b>", parse_mode='HTML')
                    else:
                        self.bot.send_message(message.chat.id, "Квартира не найдена.")
                elif message.text == 'Назад':
                    self.show_main_menu(message.chat.id)
            else:
                self.bot.send_message(message.chat.id, "Пожалуйста, выберите жилой комплекс сначала.")

        @bot.message_handler(
            func=lambda message: self.admin_bot_handler.main_bot_active and message.text == 'Выбрать квартиру на сайте')
        def handle_select_real_estate_button(message):
            # Отправляем сообщение с кнопкой WebApp
            keyboard = types.InlineKeyboardMarkup()
            webapp_button = types.InlineKeyboardButton(text="Перейти",
                                                       web_app=types.WebAppInfo(url="https://tojsokhtmon.tj"))
            keyboard.add(webapp_button)
            self.bot.send_message(message.chat.id, "Вы можете оставить заявку на выбранную недвижимость\nВоспользуйтесь фильтром подбора недвижимости 👇",
                                  reply_markup=keyboard)

    def show_main_menu(self, chat_id):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton('🏢 Жилой комплекс')
        btn2 = types.KeyboardButton('🏠 Подобрать квартиру')
        btn3 = types.KeyboardButton('🏘 Подобрать Недвижимость', web_app=types.WebAppInfo(url="https://tojsokhtmon.tj"))  # Новая кнопка
        btn4 = types.KeyboardButton('💼 Текущие акции и предложения')
        btn5 = types.KeyboardButton('📞 Запрос обратной связи')
        btn6 = types.KeyboardButton('❓ Часто задаваемые вопросы (FAQ)')
        keyboard.add(btn1, btn2)
        keyboard.add(btn3, btn4)
        keyboard.add(btn5, btn6)
        # keyboard.add(btn4, btn5)
        # keyboard.add(btn6)
        message = "Выберите опцию"
        self.bot.send_message(chat_id, message, reply_markup=keyboard)

    def show_complex_menu(self, chat_id):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        complex_names = self.get_complex_names()
        if not complex_names:
            self.bot.send_message(chat_id, "Нет доступных жилых комплексов.")
            self.show_main_menu(chat_id)
            return

        row = []
        for index, name in enumerate(complex_names):
            row.append(types.KeyboardButton(name))
            if (index + 1) % 3 == 0:
                keyboard.add(*row)
                row = []
        if row:
            keyboard.add(*row)
        keyboard.add(types.KeyboardButton('Назад'))
        self.bot.send_message(chat_id, "Выберите жилой комплекс:", reply_markup=keyboard)

    def show_complex_details_menu(self, chat_id, complex_id):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton('Выбрать квартиру')
        btn2 = types.KeyboardButton('Оставить заявку')
        btn3 = types.KeyboardButton('Назад')
        keyboard.add(btn1, btn2, btn3)
        self.bot.send_message(chat_id, "Выберите категорию:", reply_markup=keyboard)

    def show_apartment_selection_menu(self, chat_id):
        apartments = self.get_apartments_by_complex(self.current_complex_id)
        if not apartments:
            self.bot.send_message(chat_id, "Нет добавленных квартир в этом жилом комплексе.")
            self.show_complex_details_menu(chat_id, self.current_complex_id)
            return

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        room_map = {1: 'Однокомнатная', 2: 'Двухкомнатная', 3: 'Трехкомнатная', 4: 'Четырехкомнатная'}
        for rooms, in apartments:
            keyboard.add(types.KeyboardButton(room_map.get(rooms, f'{rooms}-комнатная')))
        btn1 = types.KeyboardButton('Назад')
        btn2 = types.KeyboardButton('Выбрать квартиру на сайте')
        keyboard.add(btn1, btn2)

        self.bot.send_message(chat_id, "Выберите тип квартиры:", reply_markup=keyboard)

    def get_complex_names(self):
        try:
            cursor = self.residential_complex_handler.conn.cursor()
            cursor.execute("SELECT name FROM residential_complex")
            return [name for (name,) in cursor.fetchall()]
        except Exception as e:
            self.bot.send_message(ADMIN_ID, f"Ошибка при получении списка жилых комплексов: {e}")
            return []

    def get_complex_id_by_name(self, name):
        try:
            cursor = self.residential_complex_handler.conn.cursor()
            cursor.execute("SELECT id FROM residential_complex WHERE name = ?", (name,))
            result = cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            self.bot.send_message(ADMIN_ID, f"Ошибка при получении ID жилого комплекса: {e}")
            return None

    def get_complex_field_value(self, complex_id, field):
        try:
            cursor = self.residential_complex_handler.conn.cursor()
            cursor.execute(f"SELECT {field} FROM residential_complex WHERE id = ?", (complex_id,))
            result = cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            self.bot.send_message(ADMIN_ID, f"Ошибка при получении значения поля '{field}': {e}")
            return None

    def get_apartment(self, complex_id, rooms):
        try:
            cursor = self.residential_complex_handler.conn.cursor()
            cursor.execute("SELECT photo, rooms, description, price FROM apartments WHERE residential_complex_id = ? AND rooms = ?", (complex_id, rooms))
            return cursor.fetchone()
        except Exception as e:
            self.bot.send_message(ADMIN_ID, f"Ошибка при получении информации о квартире: {e}")
            return None

    def get_apartments_by_complex(self, complex_id):
        try:
            cursor = self.residential_complex_handler.conn.cursor()
            cursor.execute("SELECT DISTINCT rooms FROM apartments WHERE residential_complex_id = ?", (complex_id,))
            return cursor.fetchall()
        except Exception as e:
            self.bot.send_message(ADMIN_ID, f"Ошибка при получении списка квартир: {e}")
            return []

    def show_promotion_list(self, message):
        if message.text == 'Назад':
            self.show_main_menu(message)
            return

        try:
            with sqlite3.connect('../data/tojsokhtmon.db') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, title FROM promotions")
                promotions = cursor.fetchall()
        except sqlite3.Error as e:
            self.bot.send_message(message.chat.id, f"Ошибка при получении списка акций: {e}")
            return

        if promotions:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            row = []
            for promo in promotions:
                row.append(types.KeyboardButton(promo[1]))
                if len(row) == 3:
                    markup.add(*row)
                    row = []
            if row:
                markup.add(*row)
            markup.add(types.KeyboardButton("Назад"))

            self.bot.send_message(message.chat.id, "Выберите акцию:", reply_markup=markup)
            self.bot.register_next_step_handler(message, self.process_selected_action)
        else:
            self.bot.send_message(message.chat.id, "Акций пока нет.", reply_markup=types.ReplyKeyboardRemove())
            self.show_main_menu(message.chat.id)

    def process_selected_action(self, message):
        if message.text == 'Назад':
            self.show_main_menu(message.chat.id)
        else:
            self.promotion_handler.show_promotion_details(message)
            # После отображения деталей акции снова показывайте список акций
            self.show_promotion_list(message)

    def show_faq_menu(self, message):
        try:
            with sqlite3.connect('../data/tojsokhtmon.db', check_same_thread=False) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, title FROM faq")
                faqs = cursor.fetchall()

            if not faqs:
                self.bot.send_message(message.chat.id, "Вопросы не добавлены.")
            else:
                markup = self._get_faq_menu_markup(faqs)
                self.bot.send_message(message.chat.id, "Выберите вопрос для просмотра или управления FAQ:",
                                      reply_markup=markup)
                self.bot.register_next_step_handler(message, self._handle_faq_menu_selection)
        except sqlite3.Error as e:
            self.bot.send_message(message.chat.id, f"Ошибка при получении FAQ: {e}")

    def _get_faq_menu_markup(self, faqs):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        row = []
        for faq in faqs:
            row.append(types.KeyboardButton(faq[1]))
            if len(row) == 3:
                markup.add(*row)
                row = []
        if row:
            markup.add(*row)
        markup.add('Назад')
        return markup

    def _handle_faq_menu_selection(self, message):
        if message.text == 'Назад':
            self.show_main_menu(message.chat.id)
        else:
            # Обработка выбора конкретного FAQ
            self.send_faq_details(message, message.text)

    def send_faq_details(self, message, faq_title):
        try:
            with sqlite3.connect('../data/tojsokhtmon.db', check_same_thread=False) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT title, description FROM faq WHERE title = ?", (faq_title,))
                faq = cursor.fetchone()

            if faq:
                self.bot.send_message(message.chat.id, f"{faq[0]}\n\n{faq[1]}")
            else:
                self.bot.send_message(message.chat.id, "Вопрос не найден.")

            # Показать меню FAQ снова после отправки деталей
            self.show_faq_menu(message)
        except sqlite3.Error as e:
            self.bot.send_message(message.chat.id, f"Ошибка при получении деталей FAQ: {e}")


if __name__ == '__main__':
    admin_bot_handler = AdminBotHandler(admin_bot)
    main_bot_handler = MainBotHandler(main_bot, admin_bot_handler)
    feedback_bot_handler = FeedbackBotHandler(feedback_bot)
    from threading import Thread
    Thread(target=lambda: main_bot.polling(none_stop=True)).start()
    Thread(target=lambda: feedback_bot.polling(none_stop=True)).start()
    admin_bot.polling(none_stop=True)
