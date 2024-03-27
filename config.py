from secret import *

MAX_PROJECT_TOKENS = 10000  # макс количество токенов на весь проект
MAX_USERS = 5  # макс количество пользователей на весь проект
MAX_SESSIONS = 5  # макс количество сессий у пользователя
MAX_TOKENS_IN_SESSION = 777  # макс количество токенов за сессию пользователя

MAX_MODEL_TOKENS = 25  # Для функции count_tokens

MAX_ANSWER_TOKENS = 25  # Ограничить длину ответа GPT

GPT_MODEL = 'yandexgpt-lite'

ADMIN = [1035704315]

TOKEN_TG = tg
FOLDER_ID = folder
IAM_TOKEN = iam