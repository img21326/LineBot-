from flask import Flask, request, abort
import os,sys
from linebot import (
    LineBotApi, WebhookParser
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

import requests
from bs4 import BeautifulSoup
import re
import pickle
import time
import redis
import json
from datetime import datetime, timedelta
import configparser
from _class.Hospital import KT_Hospital

app = Flask(__name__)

config = configparser.ConfigParser()
config.read('config.ini')
hospitals = {}

for h in config['DEFAULT']['hospital'].split(','):
    channel_secret = config[h]['channel_secret']
    channel_access_token = config[h]['channel_access_token']
    redis_channel = config[h]['redis_channel']
    if (config[h]['class_extend'] == 'KT'):
        hostipal = KT_Hospital(channel_secret,channel_access_token,redis_channel)
        hostipal.set_url(config[h]['_id'])
    hospitals[h] = hostipal

redis_host = config['REDIS']['host']
redis_port = config['REDIS']['port']
redis_password = config['REDIS']['pwd']
cache_time = config['DEFAULT']['cache_time']

for h in hospitals:
    if (hospitals[h].channel_secret is None)  or (hospitals[h].channel_access_token is None):
        print('Specify LINE_CHANNEL_SECRET and LINE_CHANNEL_ACCESS_TOKEN as environment variables.')
        sys.exit(1)
    hospitals[h].cache_time = int(cache_time)
if redis_host is None or redis_port is None:
    print('Specify REDIS_HOME and REDIS_PORT as environment variables.')
    sys.exit(1)

pool = redis.ConnectionPool(host=redis_host, port=redis_port, decode_responses=True, password=redis_password)
redis_client = redis.Redis(connection_pool=pool)

try:
    redis_client.ping()
except Exception as e:
    print('---------[Error]---------')
    print(e)
    print('redis connect error')
    print('host:'+redis_host)
    print('port:'+redis_port)
    print('pwd:' + redis_password)
    sys.exit(1)
print('connected to redis "{}"'.format(redis_host)) 

# 此為 Webhook callback endpoint
@app.route("/callback/<hospital>", methods=['POST'])
def callback(hospital):
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body（負責）
    try:
        if (hospitals[hospital].parser == None):
            parser = WebhookParser(hospitals[hospital].channel_secret)
            hospitals[hospital].parser = parser
        if (hospitals[hospital].line_bot_api == None):
            line_bot_api = LineBotApi(hospitals[hospital].channel_access_token)
            hospitals[hospital].line_bot_api = line_bot_api
        if (hospitals[hospital].redis == None):
            pool = redis.ConnectionPool(host=redis_host, port=redis_port, decode_responses=True, password=redis_password, db=hospitals[hospital].redis_channel)
            hospitals[hospital].redis = redis.Redis(connection_pool=pool)
        parser =  hospitals[hospital].parser
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)
    
    for event in events:
        if not isinstance(event, MessageEvent):
            continue
        if not isinstance(event.message, TextMessage):
            continue
        if (event.message.text == '列表' or event.message.text == '0'):
            text = hospitals[hospital].crawl_list()
        else:
            text = hospitals[hospital].crawl_data(part = event.message.text)
        line_bot_api = hospitals[hospital].line_bot_api
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=text)
        )

    return 'OK'

# decorator 負責判斷 event 為 MessageEvent 實例，event.message 為 TextMessage 實例。所以此為處理 TextMessage 的 handler
# @handler.add(MessageEvent, message=TextMessage)
# def handle_message(event):
#     # 決定要回傳什麼 Component 到 Channel
#     global redis_client
#     user_id = event.source.user_id
#     redis_client.pfadd("usrcnt_" + datetime.today().strftime("%Y/%m/%d"),user_id)
#     if (event.message.text == '列表' or event.message.text == '0'):
#         all_links = get_doctors_url()
#         text = ""
#         i = 1
#         for a,value in all_links.items():
#             if a=='time':
#                 continue
#             text += str(i) + ":" + str(a) + "\r\n"
#             i += 1
#     elif ('admin' in str(event.message.text)):
#         message = str(event.message.text).split(' ')
#         pwd = message[1]
#         if (pwd == '666'):
#             cmd = message[2]
#             if (cmd == 'usrcnt'):
#                 text = "今日使用人數:" + str(redis_client.pfcount("usrcnt_" + datetime.today().strftime("%Y/%m/%d")))
#             if (cmd == 'daycnt'):
#                 text = ""
#                 for x in redis_client.keys("daycnt_*"):
#                     text += str(x) + " = "+ str(redis_client.get(x)) + "\r\n"
#                     redis_client.expire(x, 5 * 60)

#     else:
#         cnt = redis_client.get("daycnt_" + str(datetime.now().strftime("%Y/%m/%d-%H")))
#         if (cnt == None):
#             redis_client.set("daycnt_" + str(datetime.now().strftime("%Y/%m/%d-%H")), 1)
#         else:
#             redis_client.incr("daycnt_" + str(datetime.now().strftime("%Y/%m/%d-%H")), 1)
#         text = get_doctor_str(event.message.text)
#         print(user_id)
#         print("text:" + text)

#     line_bot_api.reply_message(
#         event.reply_token,
#         TextSendMessage(text=text))


if __name__ == "__main__":
    # Only for debugging while developing
    app.run(host='0.0.0.0', debug=True, port=8787)
