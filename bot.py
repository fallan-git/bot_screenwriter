import logging
from telebot import TeleBot, types
from telebot.types import Message
from config import TOKEN_TG, MAX_TOKENS_IN_SESSION, ADMIN
from db import create_db, is_limit_users, is_limit_sessions, get_tokens_in_session, is_limit_tokens_in_session, create_user, insert_tokenizer_info, insert_prompt, insert_full_story, get_tokens_info
from gpt import count_tokens, ask_gpt, create_system_prompt
from keyboard import markup_menu, hideKeyboard, markup_genre, markup_start, markup_help, markup_generate, markup_limit
from text import Settings

db_file = "db.db"
db_conn = create_db(db_file)

log_file = "log.txt"
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt="%F %T",
    filename=log_file,
    filemode="w",
)

bot = TeleBot(TOKEN_TG)

user_data = {}


def check_user(m):
    global user_data, db_conn

    user_id = m.from_user.id

    if user_id not in user_data:
        user_data[user_id] = {}
        user_data[user_id]['user_id'] = user_id

        user_data[user_id]['task'] = ""
        user_data[user_id]['answer'] = ""
        user_data[user_id]['busy'] = False
        user_data[user_id]['t_start'] = 0
        user_data[user_id]['t_result'] = 0


@bot.message_handler(commands=['start'])
def handle_start(m: Message):
    user_id = m.from_user.id
    check_user(m)
    bot.send_message(user_id, '✌ Привет! Я бот с искусственным интеллектом который поможет тебе сочинить сценарий.\n\n'
        'Если хочешь узнать дополнительную информацию - напиши /help\n'
        'Для того что бы начать сочинять сценарий нужно написать /story', reply_markup=markup_menu)

@bot.message_handler(commands=['help'])
def handle_help(m: Message):
    user_id = m.from_user.id
    check_user(m)
    bot.send_message(user_id, 'Доступные команды📘:\n'
        '/tokens - информация по ваш баланс токенов, а так же общие ограничения\n'
        '/story - начало генерации сценария, вам на выбор будут предложенны: жанр, персонажа, антураж\n\n'
        'Бот🤖 на GitHub, - <a href="https://github.com/fallan-git/scenario-gpt-bot">клац</a>\n',
        parse_mode="HTML", reply_markup=markup_help)


@bot.message_handler(commands=['debug'])
def handle_debug(m: Message):
    user_id = m.from_user.id
    check_user(m)
    logging.warning(f"{user_id}: get tokens statistics from TG-bot")

    if user_id in ADMIN:
        try:
            with open(log_file, "rb") as file:
                bot.send_document(user_id, file, reply_markup=markup_menu)
        except Exception:
            logging.error(f"{user_id}: cannot send log-file to tg-user")
            bot.send_message(user_id, 'Не могу найти лог-файл', reply_markup=markup_menu)
    else:
        bot.send_message(user_id, 'У вас нет доступа!❌', reply_markup=markup_menu)

@bot.message_handler(commands=['tokens'])
def handle_tokens(m: Message):
    global db_conn
    user_id = m.from_user.id
    check_user(m)
    logging.warning(f"{user_id}: Любопытный пользователь спрашивает про токены")

    bot.send_message(user_id, "\n".join(get_tokens_info(db_conn, user_data[user_id])), reply_markup=markup_menu)

@bot.message_handler(commands=['story'])
def handle_settings(m: Message):
    user_id = m.from_user.id
    check_user(m)
    bot.send_message(user_id, 'Выбери сначала жанр, потом персонажа, потом антураж', reply_markup=markup_genre)
    bot.register_next_step_handler(m, settings_genre)


def settings_genre(m: Message):
    global db_conn, markup_genre, user_data
    user_id = m.from_user.id
    check_user(m)
    if m.text in list(Settings.keys()):
        user_data[user_id]['genre'] = m.text
        genre = user_data[user_id]['genre']
        characters = list(Settings[genre]['characters'])
        markup_characters = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup_characters.add(*characters)
        bot.send_message(
            user_id,
            'Теперь выбери персонажа', reply_markup=markup_characters)
        bot.register_next_step_handler(m, settings_characters)
    else:
        bot.send_message(
            user_id,
            'Выбери правильный жанр из списка!', reply_markup=markup_genre)
        bot.register_next_step_handler(m, settings_genre)

    return


def settings_characters(m: Message):
    global db_conn, markup_genre, user_data
    user_id = m.from_user.id
    check_user(m)
    genre = user_data[user_id]['genre']
    characters = list(Settings[genre]['characters'])
    entourages = list(Settings[genre]['entourages'])

    markup_characters = types.ReplyKeyboardMarkup(
        row_width=2,
        resize_keyboard=True)
    markup_characters.add(*characters)

    markup_entourages = types.ReplyKeyboardMarkup(
        row_width=2,
        resize_keyboard=True)
    markup_entourages.add(*entourages)

    if m.text in characters:
        user_data[user_id]['character'] = m.text
        bot.send_message(
            user_id,
            'Теперь выбери антураж', reply_markup=markup_entourages)
        bot.register_next_step_handler(m, settings_entourages)
    else:
        bot.send_message(
            user_id,
            'Выбери персонажа из списка!', reply_markup=markup_characters)
        bot.register_next_step_handler(m, settings_characters)

    return


def settings_entourages(m: Message):
    global db_conn, markup_genre, user_data
    user_id = m.from_user.id
    check_user(m)
    genre = user_data[user_id]['genre']
    entourages = list(Settings[genre]['entourages'])

    markup_entourages = types.ReplyKeyboardMarkup(
        row_width=2,
        resize_keyboard=True)
    markup_entourages.add(*entourages)

    if m.text in entourages:
        user_data[user_id]['entourage'] = m.text
        bot.send_message(user_id, 'Отлично, полный набор настроек!\n\n'
            f'Жанр: {user_data[user_id]["genre"]}\n'
            f'Персонаж: {user_data[user_id]["character"]}\n'
            f'Антураж: {user_data[user_id]["entourage"]}\n\n'
            'Пора генерить сценарий! /generate\n'
            '(Помни про ограничения сессий и токенов)', reply_markup=markup_start)
        return
    else:
        bot.send_message(
            user_id,
            'Выбери из списка!', reply_markup=markup_entourages)
        bot.register_next_step_handler(m, settings_entourages)

    return


@bot.message_handler(commands=['generate'])
def handle_generate(m: Message):
    global db_conn, user_data, MAX_TOKENS_IN_SESSION
    user_id = m.from_user.id
    check_user(m)

    if is_limit_users(db_conn):
        logging.warning(f"MAX_USERS limit exceeded, user_id: {user_id}")
        bot.send_message(
            user_id,
            'Превышено количество пользователей бота!\n'
            'Для вас доступен просмотр статистики токенов /tokens, а так информация о боте /help', reply_markup=markup_limit)
        return False

    if is_limit_sessions(db_conn, user_id):
        logging.warning(f"MAX_SESSIONS limit exceeded, user_id: {user_id}")
        bot.send_message(
            user_id,
            'Превышено количество сессий на одного пользователя!\n'
            'Для вас доступен просмотр статистики токенов: /tokens, а так информация о боте /help', reply_markup=markup_limit)
        return False

    if ('genre' not in user_data[user_id]
            or 'character' not in user_data[user_id]
            or 'entourage' not in user_data[user_id]):
        bot.send_message(
            user_id,
            'Для начала новой сессии перейди в настройки: /story\n'
            'Там выбери сначала жанр, потом персонажа, потом антураж.', reply_markup=hideKeyboard)
    else:
        bot.send_message(
            user_id,
            f'Жанр: {user_data[user_id]["genre"]}\n'
            f'Персонаж: {user_data[user_id]["character"]}\n'
            f'Антураж: {user_data[user_id]["entourage"]}\n\n'
            f''
            f'Ограничение токенов в этой сессии: {MAX_TOKENS_IN_SESSION}', reply_markup=hideKeyboard)

        session_id = create_user(db_conn, user_data[user_id])

        if session_id:
            user_data[user_id]['session_id'] = session_id
            logging.warning(f"New session id={session_id} "
                            f"has been created: user_id={user_id}")

            user_data[user_id]['collection'] = []
            bot.send_message(
                user_id,
                'Введи начало задачи (одно-два предложения). '
                'Бот-сценарист продолжит сюжет. Потом снова ты.\n\n'
                'Когда надоест - напиши: Конец', reply_markup=markup_generate)
            bot.register_next_step_handler(m, handle_ask_gpt)

        else:
            logging.error(f"Cannot create new session: user_id={user_id}")
            bot.send_message(
                user_id,
                'Не получилось создать новую сессию!\n'
                'Общение с GPT невозможно без этого.', reply_markup=hideKeyboard)
            return False


def handle_ask_gpt(m: Message):
    global user_data, db_conn
    user_id = m.from_user.id
    check_user(m)

    prompt_user_prefix = ("Продолжи описание, но не пиши никакой "
                          "пояснительный текст от себя: ")

    if m.text.lower() == 'конец':
        full_story = ""
        for row in user_data[user_id]['collection']:
            if row['role'] == 'system':
                continue
            full_story += row['content'].replace(prompt_user_prefix, "") + " "
        insert_full_story(db_conn, user_data[user_id], full_story)

        user_data[user_id]['collection'].clear()
        user_data[user_id]['genre'] = ""
        user_data[user_id]['character'] = ""
        user_data[user_id]['entourage'] = ""
        bot.send_message(
            user_id,
            f'Вот итоговый текст, получился с помощью бота:\n\n'
            f'{full_story}\n\n'
            f'Попробуй другие настройки для нового сценария! /story', reply_markup=markup_menu)
        bot.register_next_step_handler(m, handle_settings)
        return False

    if not len(user_data[user_id]['collection']):
        prompt_system = create_system_prompt(user_data[user_id])

        t_system = count_tokens(prompt_system)
        insert_tokenizer_info(db_conn, user_data[user_id],
                              prompt_system, t_system)
        logging.warning(f"Count tokens: user={user_id}, t_system={t_system}")
        user_data[user_id]['collection'].append(
            {
                "role": "system",
                "content": prompt_system,
            }
        )
        logging.info("Adding system prompt")
        insert_prompt(db_conn,
                      user_data[user_id],
                      "system",
                      prompt_system,
                      t_system)



    prompt_user = prompt_user_prefix + m.text
    t = count_tokens(prompt_user)

    insert_tokenizer_info(db_conn, user_data[user_id],
                          prompt_user, t)
    logging.warning(
        f"Count tokens: user={user_id}, t={t}, content={prompt_user}")

    if is_limit_tokens_in_session(db_conn, user_data[user_id], t):
        bot.send_message(
            user_id,
            f'ОШИБКА\n'
            f'Токенайзер насчитал токенов (FAKE): {t}\n'
            f'Это больше, чем осталось токенов в сессии. '
            f'Попробуйте более короткий запрос.', reply_markup=markup_generate)
        logging.warning(f"Not enough tokens ({t}): user_id={user_id}")
        bot.register_next_step_handler(m, handle_ask_gpt)
        return

    user_data[user_id]['collection'].append(
        {
            "role": "user",
            "content": prompt_user,
        }
    )
    logging.info("Adding user prompt")
    insert_prompt(db_conn,
                  user_data[user_id],
                  "user",
                  prompt_user,
                  t)

    res_gpt = ask_gpt(user_data[user_id])
    print(res_gpt)
    t_res = count_tokens(res_gpt)
    insert_tokenizer_info(db_conn, user_data[user_id],
                          res_gpt, t_res)
    user_data[user_id]['collection'].append(
        {
            "role": "assistant",
            "content": res_gpt,
        }
    )
    logging.info("Adding user prompt")
    insert_prompt(db_conn,
                  user_data[user_id],
                  "assistant",
                  res_gpt,
                  t_res)

    bot.send_message(
        user_id,
        f'Ответ от GPT:\n\n'
        f'{res_gpt}', reply_markup=markup_generate)
    bot.register_next_step_handler(m, handle_ask_gpt)


bot.infinity_polling()
db_conn.close()
