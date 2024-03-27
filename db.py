from time import time_ns
import logging
import sqlite3
from config import MAX_PROJECT_TOKENS, MAX_USERS, MAX_SESSIONS, MAX_TOKENS_IN_SESSION

def create_db(db_file):
    db_connection = sqlite3.connect(db_file, check_same_thread=False)
    cursor = db_connection.cursor()

    cursor.execute(
        'CREATE TABLE IF NOT EXISTS Sessions ('
        'id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'user_id INTEGER, '
        'genre TEXT, '
        'character TEXT, '
        'entourage TEXT, '
        't_start INT, '
        'task TEXT, '
        'answer TEXT'
        ')'
    )

    cursor.execute(
        'CREATE TABLE IF NOT EXISTS Prompts ('
        'id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'user_id INTEGER, '
        'session_id INTEGER, '
        'role TEXT, '
        'content TEXT, '
        'tokens INT'
        ')'
    )

    cursor.execute(
        'CREATE TABLE IF NOT EXISTS Tokenizer ('
        'id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'user_id INTEGER, '
        'session_id INTEGER, '
        't_start INTEGER, '
        'content TEXT, '
        'tokens INT'
        ')'
    )

    cursor.execute(
        'CREATE TABLE IF NOT EXISTS Full_Stories ('
        'id INTEGER PRIMARY KEY, '
        'user_id INTEGER, '
        'session_id INTEGER, '
        'content TEXT'
        ')'
    )

    return db_connection


def is_limit_users(db_connection):
    global MAX_USERS

    cursor = db_connection.cursor()
    query = 'SELECT COUNT(DISTINCT user_id) FROM Sessions;'
    cursor.execute(query)
    res = cursor.fetchone()
    if res is None:
        return False
    print(f"is_limit_users {res[0]}")
    logging.warning(f"Есть {res[0]} отдельных пользователей в сеансах")

    return res[0] >= MAX_USERS


def is_limit_sessions(db_connection, user_id):
    global MAX_SESSIONS

    cursor = db_connection.cursor()
    query = 'SELECT COUNT(id) FROM Sessions WHERE user_id = ?;'
    cursor.execute(query, (user_id,))
    res = cursor.fetchone()
    if res is None:
        return False
    print(f"is_limit_sessions {res[0]}")
    logging.warning(f"Пользователь {user_id} имеет {res[0]} сессий")

    return res[0] >= MAX_SESSIONS


def get_tokens_in_session(db_connection, user):
    cursor = db_connection.cursor()
    query = ('SELECT tokens FROM Prompts '
             'WHERE user_id = ? '
             'AND session_id = ? '
             'ORDER BY id DESC LIMIT 1;')

    try:
        cursor.execute(query, (user['user_id'], user['session_id'],))
        res = cursor.fetchone()

        if res is None:
            print(f"get_tokens_in_session None = 0")
            logging.warning(f"get_tokens_in_session None = 0")
            return 0
        else:
            print(f"is_limit_tokens_in_session {res[0]}")
            logging.warning(f"Пользователь {user['user_id']} "
                            f"имеет {res[0]} токенов на текущей сессии")
            return res[0]
    except Exception as e:
        return 0


def is_limit_tokens_in_session(db_connection, user, t):
    global MAX_TOKENS_IN_SESSION

    return (MAX_TOKENS_IN_SESSION <=
            (get_tokens_in_session(db_connection, user) + t))


def create_user(db_connection, user):
    cursor = db_connection.cursor()
    logging.warning(f"Insert сеанс для user_id - {user['user_id']}:... ")
    data = (
        user['user_id'],
        user['genre'],
        user['character'],
        user['entourage'],
        time_ns()
    )

    try:
        cursor.execute('INSERT INTO Sessions '
                       '(user_id, genre, character, entourage, t_start) '
                       'VALUES (?, ?, ?, ?, ?);',
                       data)
        db_connection.commit()
        logging.warning(f"... OK id={cursor.lastrowid}")
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        logging.warning("... Error")
        return False


def insert_tokenizer_info(db_connection, user, content, tokens):
    cursor = db_connection.cursor()
    logging.warning(f"Asking tokenizer for user_id={user['user_id']}... ")
    data = (
        user['user_id'],
        user['session_id'],
        time_ns(),
        content,
        tokens
    )

    try:
        cursor.execute('INSERT INTO Tokenizer '
                       '(user_id, session_id, t_start, content, tokens) '
                       'VALUES (?, ?, ?, ?, ?);',
                       data)
        db_connection.commit()
        logging.warning(f"... OK id={cursor.lastrowid}")
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        logging.warning("... Error")
        return False


def insert_full_story(db_connection, user, content):
    cursor = db_connection.cursor()
    logging.warning(f"Сохранение полной истории user_id - {user['user_id']}... ")
    data = (
        user['user_id'],
        user['session_id'],
        content,
    )

    try:
        cursor.execute('INSERT INTO Full_Stories '
                       '(user_id, session_id, content) '
                       'VALUES (?, ?, ?);',
                       data)
        db_connection.commit()
        logging.warning(f"... OK id={cursor.lastrowid}")
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        logging.warning("... Error")
        return False


def get_full_story(db_connection):
    cursor = db_connection.cursor()
    query = ('SELECT content FROM Full_Stories '
             'ORDER BY RANDOM() LIMIT 1;')

    cursor.execute(query)
    res = cursor.fetchone()

    if res is None:
        logging.warning(f"get_full_story None = 0")
        return "Нет готовых сочинений"
    else:
        logging.warning(f"Получение полной истории")
        return res[0]


def insert_prompt(db_connection, user, role, content, tokens):
    cursor = db_connection.cursor()
    logging.warning(f"Finding the last prompt session_id={user['session_id']}")
    tokens_prev = get_tokens_in_session(db_connection, user)

    logging.warning(f"Добавление prompt user_id={user['user_id']}, role={role}... ")
    data = (
        user['user_id'],
        user['session_id'],
        role,
        content,
        tokens + tokens_prev
    )

    try:
        cursor.execute('INSERT INTO Prompts '
                       '(user_id, session_id, role, content, tokens) '
                       'VALUES (?, ?, ?, ?, ?);',
                       data)
        db_connection.commit()
        logging.warning(f"... OK id={cursor.lastrowid}")
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        logging.warning("... Error")
        return False


def get_tokens_info(db_connection, user):
    result = []

    result.append("\nСтандартные переменные📊:")
    result.append(f"Максимальное количество токенов на весь проект - {MAX_PROJECT_TOKENS}")
    result.append(f"Максимальное количество пользователей на весь проект - {MAX_USERS}")
    result.append(f"Максимальное количество сессий у пользователя - {MAX_SESSIONS}")
    result.append(f"Максимальное количество токенов за сессию пользователя - {MAX_TOKENS_IN_SESSION}")

    result.append("\nВаши значения перменных📜:")

    r = get_tokens_in_session(db_connection, user)
    result.append(f"Токенов в твоей текущей сессии - {r}")

    cursor = db_connection.cursor()
    query = 'SELECT COUNT(id) FROM Sessions WHERE user_id = ?;'
    cursor.execute(query, (user['user_id'],))
    res = cursor.fetchone()
    if res is None:
        r = 0
    else:
        r = res[0]
    result.append(f"Сессий у тебя - {r}")

    result.append("\nПеременные всех пользователей🗂:")

    cursor = db_connection.cursor()
    query = 'SELECT COUNT(DISTINCT user_id) FROM Sessions WHERE 1;'
    cursor.execute(query)
    res = cursor.fetchone()
    if res is None:
        r = 0
    else:
        r = res[0]
    result.append(f"Всего пользователей - {r}")

    cursor = db_connection.cursor()
    query = 'SELECT COUNT(id) FROM Sessions WHERE 1;'
    cursor.execute(query)
    res = cursor.fetchone()
    if res is None:
        r = 0
    else:
        r = res[0]
    result.append(f"Всего сессий у всех пользователей - {r}")

    return result
