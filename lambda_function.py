import json
import os
import time
from typing import Tuple

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


def telegram_bot_main(event):
    chat_id = event["message"]["chat"]["id"]
    user_id = event["message"]["from"]["id"]

    # TODO(alisher): check chat type

    text = event["message"]["text"].strip()
    if text == "/start":
        msg = instruction_msg()

    elif text == command(is_a2b=True):
        msg = amount_msg(is_a2b=True)
    elif text == command(is_a2b=False):
        msg = amount_msg(is_a2b=False)

    elif represents_int(text):
        amount = int(text)
        prev_text = previous_message(user_id).strip()
        if prev_text is None:
            print(f"history empty for user_id: {user_id}")
            msg = unknown_msg()
        if prev_text == command(is_a2b=True):
            create_order(event, amount, is_a2b=True)
            msg = open_orders(event, amount, is_a2b=True)
        elif prev_text == command(is_a2b=False):
            create_order(event, amount, is_a2b=False)
            msg = open_orders(event, amount, is_a2b=False)
        else:
            msg = unknown_msg()

    elif text == cancel_command(is_a2b=True):
        msg = cancel_order(event, is_a2b=True)
    elif text == cancel_command(is_a2b=False):
        msg = cancel_order(event, is_a2b=False)
    else:
        msg = unknown_msg()

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


def create_order(event: dict, amount: int, is_a2b: bool):
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
    table = resource.Table(table_name(is_a2b))
    table.put_item(Item=item)


def open_orders(event: dict, amount: int, is_a2b: bool):
    tablename = table_name(not is_a2b)

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
            notification = notification_msg(event, item, amount, is_a2b)
            send_message(notification, item['chat_id'])
            msg += orderbook_msg(item, not is_a2b)
    else:
        msg = empty_orderbook_msg(not is_a2b)
    msg += "\n" + cancel_request_msg(is_a2b, amount)
    return msg


def cancel_order(event: dict, is_a2b: bool):
    resource = boto3.resource("dynamodb")
    table = resource.Table(table_name(is_a2b))
    response = table.get_item(Key={"user_id": event['message']['from']['id']})
    print("GET_ITEM response", response)
    try:
        item = response["Item"]
    except Exception as e:
        print("GET_ITEM empty")
        return cancelled_msg(is_a2b)
    currency_from, _ = currency_from_to(is_a2b)
    item['type'] = currency_from
    msg = cancelled_msg(is_a2b, item['amount'])
    response = table.delete_item(
        Key={"user_id": event['message']['from']['id']})
    print("DELETE_ITEM response", response)
    table = resource.Table(f"{table_name(True)}_transaction_history")
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
    table = resource.Table(f"{table_name(True)}_telegram_hist")
    table.put_item(Item=item)


def previous_message(user_id):
    resource = boto3.resource("dynamodb")
    table = resource.Table(f"{table_name(True)}_telegram_hist")
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


def instruction_msg():
    return f"Чтобы начать, выберите валюту, которую вы хотите обменять. " \
           f"Если у вас есть {os.environ['CURRENCY_A_RUS']} и вы хотите " \
           f"обменять их на {os.environ['CURRENCY_B_RUS']}, нажмите " \
           f"/{os.environ['CURRENCY_A']}.\n\nВ обратном случае нажмите /{os.environ['CURRENCY_B']}."


def amount_msg(is_a2b: bool) -> str:
    if is_a2b:
        currency_from_rus = os.environ['CURRENCY_A_RUS']
        currency_to_rus = os.environ['CURRENCY_B_RUS']
    else:
        currency_from_rus = os.environ['CURRENCY_B_RUS']
        currency_to_rus = os.environ['CURRENCY_A_RUS']

    return f"Введите сумму, которую вы хотите обменять. " \
           f"Например, если вы хотите обменять 10,000 " \
           f"{currency_from_rus} на {currency_to_rus}, введите 10000"


def unknown_msg():
    return "Я вас не понимаю." + "\n\n" + instruction_msg()


def currency_from_to(is_a2b: bool) -> Tuple:
    if is_a2b:
        currency_from = os.environ["CURRENCY_A_RUS"]
        currency_to = os.environ["CURRENCY_B_RUS"]
    else:
        currency_from = os.environ["CURRENCY_B_RUS"]
        currency_to = os.environ["CURRENCY_A_RUS"]
    return currency_from, currency_to


def notification_msg(event: dict, ob_entry: dict, amount: int,
                     is_a2b: bool) -> str:
    currency_from, currency_to = currency_from_to(is_a2b)
    return f"[{event['message']['from']['first_name']}](tg://user?id={event['message']['from']['id']}) " \
           f"хочет обменять {amount:,} {currency_from} на {currency_to}\n\n" \
           f"{cancel_request_msg(not is_a2b, ob_entry['amount'])}."


def orderbook_msg(ob_entry: dict, is_a2b: bool) -> str:
    currency_from, currency_to = currency_from_to(is_a2b)
    return f"[{ob_entry['first_name']}](tg://user?id={ob_entry['user_id']}) хочет обменять " \
           f"{ob_entry['amount']:,} {currency_from} на {currency_to} _{relTimeToText(ob_entry['date'])}_\n"


def empty_orderbook_msg(is_a2b: bool) -> str:
    currency_from, currency_to = currency_from_to(is_a2b)
    return f"На данный момент в системе нет людей, которые хотят обменять {currency_from} на {currency_to}. " \
           f"Как только кто-нибудь объявится, я сразу же свяжу вас.\n"


def cancel_request_msg(is_a2b: bool, amount: int) -> str:
    currency_from, currency_to = currency_from_to(is_a2b)
    return f"Если вы больше не нуждаетесь в обмене {amount:,} {currency_from} " \
           f"на {currency_to} нажмите {cancel_command(is_a2b)}."


def cancelled_msg(is_a2b: bool, amount: int = -1) -> str:
    currency_from, currency_to = currency_from_to(is_a2b)
    msg = ""
    if amount > 0:
        msg = f"Я отменил вашу заявку на обмен {amount:,} {currency_from} на {currency_to}. "
    else:
        msg = f"Я отменил вашу заявку на обмен {currency_from} на {currency_to}. "
    msg += "Вы больше не будете получать сообщения по этому поводу."
    return msg


def command(is_a2b: bool) -> str:
    if is_a2b:
        curr = os.environ['CURRENCY_A']
    else:
        curr = os.environ['CURRENCY_B']
    return f"/{curr}"


def cancel_command(is_a2b: bool) -> str:
    if is_a2b:
        curr = os.environ['CURRENCY_A']
    else:
        curr = os.environ['CURRENCY_B']
    return f"/cancel{curr}"


def table_name(is_a2b: bool) -> str:
    if is_a2b:
        return f"{os.environ['CURRENCY_A']}2{os.environ['CURRENCY_B']}"
    else:
        return f"{os.environ['CURRENCY_B']}2{os.environ['CURRENCY_A']}"
