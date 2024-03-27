import requests
import logging
from config import IAM_TOKEN, FOLDER_ID
from config import GPT_MODEL
from config import MAX_PROJECT_TOKENS, MAX_USERS, MAX_SESSIONS, MAX_TOKENS_IN_SESSION, MAX_MODEL_TOKENS, MAX_ANSWER_TOKENS

CONTINUE_STORY = ('Продолжи сюжет в 1-3 предложения и оставь интригу. '
                  'Не пиши никакой пояснительный текст от себя. ')
END_STORY = ('Напиши завершение истории c неожиданной развязкой. '
             'Не пиши никакой пояснительный текст от себя. ')

SYSTEM_PROMPT = ('Ты составитель коротких детских развлекательных '
                 'математических задач в жанре')

def count_tokens(text):
    global IAM_TOKEN, FOLDER_ID, GPT_MODEL, MAX_MODEL_TOKENS

    headers = {
        'Authorization': f'Bearer {IAM_TOKEN}',
        'Content-Type': 'application/json'
    }
    data = {
        "modelUri": f"gpt://{FOLDER_ID}/{GPT_MODEL}/latest",
        "maxTokens": MAX_MODEL_TOKENS,
        "text": text
    }
    return len(
        requests.post(
            "https://llm.api.cloud.yandex.net/foundationModels/v1/tokenize",
            json=data,
            headers=headers
        ).json()['tokens']
    )

def create_system_prompt(user):
    global SYSTEM_PROMPT

    print(f"{SYSTEM_PROMPT} {user['genre']}. "
          f"Ты помогаешь пользователю составлять условия детских текстовых "
          f"математических задач. С указанными параметрами ты кратко "
          f"начинаешь (1-2 предложения), пользователь продолжает, потом "
          f"снова ты. "
          f"Не пиши никакого пояснительного текста, не относящегося "
          f"к задаче, просто логично продолжай историю! "
          f"Указанный жанр - {user['genre']}, "
          f"главный герой - {user['character']}, "
          f"место действия - {user['entourage']}. ")

    return (f"{SYSTEM_PROMPT} {user['genre']}. "
            f"Ты помогаешь придумывать условия детских текстовых "
            f"математических задач. Пользователь начинает короткой фразой, "
            f"а ты дополняешь 1-2 коротких предложения, сохраняя интригу. "
            f"Не пиши от себя никакого пояснительного текста, "
            f"просто логично продолжай историю! "
            f"Жанр текста: {user['genre']}, "
            f"главный персонаж: {user['character']}, "
            f"место действия: {user['entourage']}. ")


def ask_gpt(user, mode='continue'):
    global IAM_TOKEN, FOLDER_ID, GPT_MODEL, MAX_ANSWER_TOKEN

    collection = user['collection']
    url = f"https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        'Authorization': f'Bearer {IAM_TOKEN}',
        'Content-Type': 'application/json'
    }
    data = {
        "modelUri": f"gpt://{FOLDER_ID}/{GPT_MODEL}/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.7,
            "maxTokens": MAX_ANSWER_TOKENS
        },
        "messages": []
    }

    for row in collection:
        data["messages"].append(
            {
                "role": row["role"],
                "text": row['content']
            }
        )

    print(data["messages"])
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            result = f"Error(?) status code {response.status_code}"
            logging.error(result)
            return result
        result = response.json()['result']['alternatives'][0]['message']['text']

    except Exception as e:
        result = f"Error '{e}' while requesting GPT"
        logging.error(result)

    return result


def backup_ask_gpt(collection, mode='continue'):
    global IAM_TOKEN, FOLDER_ID, GPT_MODEL, MAX_ANSWER_TOKEN
    url = f"https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        'Authorization': f'Bearer {IAM_TOKEN}',
        'Content-Type': 'application/json'
    }
    data = {
        "modelUri": f"gpt://{FOLDER_ID}/{GPT_MODEL}/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": MAX_ANSWER_TOKENS
        },
        "messages": []
    }

    for row in collection:
        content = row['content']
        if mode == 'continue' and row['role'] == 'user':
            content += CONTINUE_STORY
            pass
        elif mode == 'end' and row['role'] == 'user':
            content += END_STORY
            pass

        data["messages"].append(
            {
                "role": row["role"],
                "text": content
            }
        )

    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            result = f"Error(?) status code {response.status_code}"
            logging.error(result)
            return result
        result = response.json()['result']['alternatives'][0]['message']['text']

    except Exception as e:
        result = f"Error '{e}' while requesting GPT"
        logging.error(result)

    return result


def main(user_id=1):
    print("Привет! Я помогу тебе составить классный сценарий!")
    genre = input(
        "Для начала напиши жанр, в котором хочешь составить сценарий: ")
    character = input("Теперь опиши персонажа, который будет главным героем: ")
    setting = input(
        "И последнее. Напиши сеттинг, в котором будет жить главный герой: ")

    user_data += genre + character + setting

    user_collection += create_system_prompt(genre, character, setting)

    user_content = input('Напиши начало истории: \n')
    while user_content.lower() != 'end':

        user_collection += user_content.lower()

        assistant_content = ask_gpt(user_collection[user_id])


        user_collection += assistant_content.lower()

        print('YandexGPT: ', assistant_content)
        user_content = input(
            'Напиши продолжение истории. Чтобы закончить введи end: \n')

    assistant_content = ask_gpt(user_collection[user_id], 'end')

    user_collection += assistant_content.lower()

    print('\nВот, что у нас получилось:\n')

    return user_collection

    input('\nКонец... ')
