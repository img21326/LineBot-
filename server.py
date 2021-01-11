from flask import Flask, request, abort
import os
from linebot import (
    LineBotApi, WebhookHandler
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
from datetime import datetime
import pandas as pd

app = Flask(__name__)

# get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
if channel_secret is None or channel_access_token is None:
    print('Specify LINE_CHANNEL_SECRET and LINE_CHANNEL_ACCESS_TOKEN as environment variables.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

def get_doctors_url(refresh = False):
    if os.path.isfile("links.pickle") and (refresh == False):
        with open('links.pickle', 'rb') as handle:
            all_link = pickle.load(handle)
        if (datetime.fromtimestamp(time.time()) - datetime.fromtimestamp(all_link['time'])).seconds > 5 * 60:
            print("refresh links data")
            return get_doctors_url(True)
        else:
            print("history links data")
            return all_link
    else:
        r = requests.get("http://www.ktgh.com.tw/Reg_Clinic_Progress.asp?CatID=39&ModuleType=Y")
        rt = r.text
        rs = BeautifulSoup(rt, 'html.parser')
        sizebox = rs.find(id='Sizebox')
        links = sizebox.find_all(attrs={"onclick": re.compile("^javascript:location.href")})
        all_link = {}
        for link in links:
            _link = (link['onclick'].split('\'')[1])
            _title = (link.find('a')['title'])
            all_link[_title] = _link
        all_link['time'] = time.time()
        with open('links.pickle', 'wb') as handle:
            pickle.dump(all_link, handle, protocol=pickle.HIGHEST_PROTOCOL)
        return all_link

def find_df(dfs):
    for df in dfs:
        print(df)
        if ('看診進度(備註)' in df.columns):
            print("Find df")
            return df
        else:
            print("not found df")

def get_doctor_data(c, all_link,refresh = False):
    if os.path.isfile(c + ".pickle") and (refresh == False):
        df = pd.read_pickle(c+'.pickle')
        if (datetime.fromtimestamp(time.time()) - datetime.fromtimestamp(df['time'][0])).seconds > 5 * 60:
            print("refresh doctor data")
            return get_doctor_data(c, all_link,True)
        else:
            print("history doctor data")
            return df
    else:
        dfs = pd.read_html("http://www.ktgh.com.tw/" + all_link[c])
        df = find_df(dfs)
        # df['doctor'] = df['看診醫師'].map(lambda x:x.split(' ')[-1].split('(')[0])
        # df['num'] = df['看診進度(備註)'].map(lambda x:x.split('號')[1].split(':')[1])
        # df = df.astype({'num': 'int32'})
        df['time'] = time.time()
        df.to_pickle(c + '.pickle')
        return df

def get_doctor_str(c, all_link):
    if c not in all_link:
        return "醫生還未開始看診"
    df = get_doctor_data(c ,all_link)
    arr_doctor = []
    arr_status = []
    str_ = ''
    for d, r in df.iteritems():
        if (d == '看診醫師'):
            arr_doctor = (r.values)
        if (d == '看診進度(備註)'):
            arr_status = (r.values)
    for i in list(zip(arr_doctor, arr_status)):
        str_ += i[0] + "\r\n" + i[1] + "\r\n" + "--------------------------------" + "\r\n"
    return str_

# 此為 Webhook callback endpoint
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body（負責）
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

# decorator 負責判斷 event 為 MessageEvent 實例，event.message 為 TextMessage 實例。所以此為處理 TextMessage 的 handler
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # 決定要回傳什麼 Component 到 Channel
    all_links = get_doctors_url()
    text = get_doctor_str(event.message.text , all_links)
    print("text:" + text)

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=text))


if __name__ == '__main__':
    app.run()