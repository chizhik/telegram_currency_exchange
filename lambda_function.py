import json
import os
import time

import boto3
import requests
from boto3.dynamodb.conditions import Key

# from urllib import parse, request


def lambda_handler(event, context):
    print(event)
    try:
        telegram_bot_main(event)
    except Exception as e:
        notify_admin(event, e)

    return {
        "statusCode": 200,
        "body": json.dumps("telegram message processed")
    }


INSTRUCTION_MESSAGE = "Чтобы начать, выберите валюту, которую вы хотите обменять. " \
            "Если у вас есть тенге и вы хотите обменять их на воны, нажмите /tenge.\n\n" \
            "В обратном случае нажмите /won."
AMOUNT_KZT2KRW_MSG = "Введите сумму, которую вы хотите обменять. " \
                     "Например, если вы хотите обменять 10,000 тенге на воны, введите 10000"
AMOUNT_KRW2KZT_MSG = "Введите сумму, которую вы хотите обменять. " \
                     "Например, если вы хотите обменять 10,000 вон на тенге, введите 10000"
UNKNOWN_MSG = "Я вас не понимаю." + "\n\n" + INSTRUCTION_MESSAGE


def telegram_bot_main(event):
    chat_id = event["message"]["chat"]["id"]
    user_id = event["message"]["from"]["id"]

    # TODO(alisher): check chat type

    text = event["message"]["text"].strip()
    if text == "/start":
        msg = INSTRUCTION_MESSAGE

    elif text == "/tenge":
        msg = AMOUNT_KZT2KRW_MSG
    elif text == "/won":
        msg = AMOUNT_KRW2KZT_MSG

    elif represents_int(text):
        amount = int(text)
        prev_text = previous_message(user_id).strip()
        if prev_text is None:
            print(f"history empty for user_id: {user_id}")
            msg = UNKNOWN_MSG
        if prev_text == "/tenge":
            create_order(event, amount, "kzt2krw")
            msg = open_orders(event, amount, "kzt2krw")
        elif prev_text == "/won":
            create_order(event, amount, "krw2kzt")
            msg = open_orders(event, amount, "krw2kzt")
        else:
            msg = UNKNOWN_MSG

    elif text == "/canceltenge":
        msg = cancel_order(event, "kzt2krw")
    elif text == "/cancelwon":
        msg = cancel_order(event, "krw2kzt")
    else:
        msg = UNKNOWN_MSG

    send_message(msg, chat_id)
    add_history(event)


def send_message(message, chat_id, rm=None):
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
    }
    TELEGRAM_URL = "https://api.telegram.org/bot"
    TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
    if rm is not None:
        data["reply_markup"] = rm

    response = requests.post(f"{TELEGRAM_URL}{TELEGRAM_BOT_TOKEN}/sendMessage",
                             data=data)
    print("request response", response.content)


def create_order(event, amount, tradeType):
    assert tradeType == "kzt2krw" or tradeType == "krw2kzt"
    item = {
        "user_id": event["message"]["from"]["id"],
        "date": int(time.time()),
        "chat_id": event["message"]["chat"]["id"],
        "amount": amount,
        "first_name": event["message"]["from"]["first_name"]
    }
    if "username" in event["message"]["from"]:
        item["username"] = event["message"]["from"]["username"]
    resource = boto3.resource("dynamodb")
    table = resource.Table(tradeType)
    table.put_item(Item=item)


def open_orders(event, amount, tradeType):
    assert tradeType == "kzt2krw" or tradeType == "krw2kzt"
    if tradeType == "kzt2krw":
        currency_from = "тенге"
        currency_to = "вон"
        cancel_cmd = "/canceltenge"
        cancel_cmd_others = "/cancelwon"
        tablename = "krw2kzt"
    elif tradeType == "krw2kzt":
        currency_from = "вон"
        currency_to = "тенге"
        cancel_cmd = "/cancelwon"
        cancel_cmd_others = "/canceltenge"
        tablename = "kzt2krw"
    else:
        assert False
    resource = boto3.resource("dynamodb")
    table = resource.Table(tablename)
    response = table.scan()
    items = response["Items"]
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response['Items'])

    if len(items) > 0:
        msg = ""
        for item in items:
            notification = f"[{event['message']['from']['first_name']}](tg://user?id={event['message']['from']['id']}) хочет обменять {amount:,} {currency_from} на {currency_to}"
            notification += f"\n\nЕсли вы больше не нуждаетесь в обмене {item['amount']:,} {currency_to} на {currency_from} нажмите {cancel_cmd_others}."
            send_message(notification, item['chat_id'])

            msg += f"[{item['first_name']}](tg://user?id={item['user_id']}) хочет обменять {item['amount']:,} {currency_to} на {currency_from} _{relTimeToText(item['date'])}_\n"
    else:
        msg = f"На данный момент в системе нет людей, которые хотят обменять {currency_to} на {currency_from}. Как только кто-нибудь объявится, я сразу же свяжу вас.\n"
    msg += f"\nЕсли вы больше не нуждаетесь в обмене {amount:,} {currency_from} на {currency_to} нажмите {cancel_cmd}."
    return msg


def cancel_order(event, tradeType):
    if tradeType == "kzt2krw":
        currency_from = "тенге"
        currency_to = "вон"
    elif tradeType == "krw2kzt":
        currency_from = "вон"
        currency_to = "тенге"
    else:
        assert False
    resource = boto3.resource("dynamodb")
    table = resource.Table(tradeType)
    response = table.get_item(Key={"user_id": event['message']['from']['id']})
    print("GET_ITEM response", response)
    try:
        item = response["Item"]
    except Exception as e:
        print("GET_ITEM empty")
        return f"Я отменил вашу заявку на обмен. Вы больше не будете получать сообщения по этому поводу."
    item['type'] = tradeType
    msg = f"Я отменил вашу заявку на обмен {item['amount']:,} {currency_from} на {currency_to}. Вы больше не будете получать сообщения по этому поводу."
    response = table.delete_item(
        Key={"user_id": event['message']['from']['id']})
    print("DELETE_ITEM response", response)
    table = resource.Table("transaction_history")
    response = table.put_item(Item=item)
    print("PUT_ITEM response", response)
    return msg


def add_history(event):
    item = {
        "user_id": event["message"]["from"]["id"],
        "date": int(time.time()),
        "chat_id": event["message"]["chat"]["id"],
        "text": event["message"]["text"],
        "first_name": event["message"]["from"]["first_name"]
    }
    if "username" in event["message"]["from"]:
        item["username"] = event["message"]["from"]["username"]
    resource = boto3.resource("dynamodb")
    table = resource.Table("telegram_hist")
    table.put_item(Item=item)


def previous_message(user_id):
    resource = boto3.resource("dynamodb")
    table = resource.Table("telegram_hist")
    response = table.query(KeyConditionExpression=Key('user_id').eq(user_id),
                           ScanIndexForward=False,
                           Limit=1)
    print(response)
    if response["Count"] == 0:
        return None
    return response["Items"][0]["text"]


def represents_int(s):
    try:
        i = int(s)
        return i > 0
    except ValueError:
        return False


def notify_admin(event, error):
    msg = f"ERROR: {error}\nEVENT:{event}"
    print(msg)
    admin_chat_id = int(os.environ["ADMIN_CHAT_ID"])
    send_message(msg, admin_chat_id)
    return


def timehelper(n):
    assert n > 0
    r = n % 10
    r10 = (n // 10) % 10
    if r10 == 1:
        return ["дней", "часов", "минут", "секунд"]
    elif r == 1:
        return ["день", "час", "минуту", "секунду"]
    elif r > 1 and r < 5:
        return ["дня", "часа", "минуты", "секунды"]
    else:
        return ["дней", "часов", "минут", "секунд"]


def relTimeToText(unixtimestamp):
    secs = ts = int(time.time()) - unixtimestamp
    days = secs // 86400
    if days > 0:
        return f"{days} {timehelper(days)[0]} назад"
    hours = secs // 3600
    if hours > 0:
        return f"{hours} {timehelper(hours)[1]} назад"
    minutes = secs // 60
    if minutes > 0:
        return f"{minutes} {timehelper(minutes)[2]} назад"
    seconds = secs
    if seconds > 0:
        return f"{seconds} {timehelper(seconds)[3]} назад"
    return "только что"
