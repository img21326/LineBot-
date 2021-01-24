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
from ._class.Hospital import KT_Hospital

def create_app():

    app = Flask(__name__)

    config = configparser.ConfigParser()
    config.read('app/config.ini')
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

    return app