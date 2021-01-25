import json
import requests
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime, timedelta

class Hospital():
    channel_secret = None
    channel_access_token = None
    redis_channel = None
    line_bot_api = None
    parser = None
    redis = None
    cache_time = None

    all_list = None
    list_update_time = None
    
    def __init__(self,sct, asst, rdc, lba = None, ps = None):
        self.channel_secret = sct
        self.channel_access_token = asst
        self.redis_channel = rdc
        self.line_bot_api = lba
        self.parser = ps

    def set_url(self):
        pass

    def crawl_list(self):
        return None

    def crawl_doctor(self):
        return None

class CCGH_Hospital(Hospital):
    url = 'http://api.ccgh.com.tw/api/GetClinicMainList/GetClinicMainData'
    
    def crawl_data(self, part):
        if (self.crawl_list() == False):
            return "還未開始看診"
        if str(part).isnumeric():
            try:
                part = int(part)
                part = list(self.all_list)[part-1]
            except Exception as e:
                print(e)
                part = 'error'
        if part not in self.all_list:
            return "醫生還未開始看診"
        text = part + "\r\n--------------------------------\r\n"
        for i in self.all_list[part]:
            print(i)
            text += i['doctor'] + '\r\n'
            text += '尚未看診:' + str(i['NotYetNumber'])+ '\r\n'
            text += '完成看診:' + str(i['FinishNumber']) + '\r\n'
            text += '目前號碼:' + str(i['LastNumberNew']) + '\r\n'
            text += "--------------------------------\r\n"
        text += '最後更新時間:' + str(self.all_list['last_update_time'])
        return text

    def crawl_list(self,refresh = False):
        all_list = self.redis.get('all_list')
        if all_list != None and refresh == False:
            print("history all_list data")
            self.all_list = json.loads(all_list)
        else:
            r = requests.get(self.url)
            if (r.status_code != 200):
                return False
            j = json.loads(r.text)
            all_list = {}
            for a in j:
                all_list[a['Clinic']] = []
            for a in j:
                all_list[a['Clinic']].append(
                {
                    'doctor': a['DoctorName'],
                    'NotYetNumber': a['NotYetNumber'],
                    'FinishNumber': a['FinishNumber'],
                    'LastNumberNew': a['LastNumberNew'],
                    'doctor': a['DoctorName'],
                })
            all_list['last_update_time'] = datetime.now().strftime("%Y/%m/%d %H:%M")
            self.redis.setex("all_list", self.cache_time,json.dumps(all_list))
            self.all_list = all_list
            self.list_update_time = datetime.now()
        i=1
        text=''
        if (len(self.all_list) == 0):
            return "還未開始看診"
        for a in self.all_list:
            if a=='last_update_time':
                continue
            text += str(i) + ":" + str(a) + "\r\n"
            i += 1
        return text


class KT_Hospital(Hospital):
    _id = None
    web_url = 'http://www.ktgh.com.tw/'
    list_url = None
    all_list = None

    def set_url(self, _id):
        self._id = _id
        self.list_url = 'http://www.ktgh.com.tw/Reg_Clinic_Progress.asp?CatID={_id}&ModuleType=Y'.format(_id=_id)

    def crawl_data(self, part, refresh = False):
        if (self.all_list == None or ((datetime.fromtimestamp(time.time()) - datetime.fromtimestamp(self.list_update_time)).seconds > self.cache_time) ):
            print("object don't has all list")
            self.crawl_list()
        if str(part).isnumeric():
            try:
                part = int(part)
                part = list(self.all_list)[part-1]
            except Exception as e:
                print(e)
                part = 'error'
        if part not in self.all_list:
            return "醫生還未開始看診"
        data = self.redis.get('doctor_' + part)
        if data != None and refresh == False:
            print("history doctor data")
            data = json.loads(data)
            return data['str']
        else:
            print("refresh doctor data")
            r = requests.get("http://www.ktgh.com.tw/" + self.all_list[c])
            rt = r.text
            rs = BeautifulSoup(rt, 'html.parser')
            _str = str(c) + '\r\n--------------------------------\r\n'
            table = rs.find_all(attrs={'summary': '排版用表格'})[10]
            doctors = table.find_all("a")
            for doctor in doctors:
                _time = doctor.parent.findNext('td')
                if ('已' in str(_time.text)):
                    text1 = str(_time.text).split('已')[0] + '\r\n'
                    text1 = text1 + '已' + str(_time.text).split('已')[1]
                else:
                    text1 = str(_time.text)

                if ('(' in doctor.text):
                    continue
                _str += doctor.text + "\r\n" + text1 + "\r\n" + "--------------------------------\r\n"
            _str = _str + '最後更新時間:' + str(datetime.now().strftime("%Y/%m/%d %H:%M"))
            pkl = {
                'str': _str,
                'time': time.time(),
            }
            self.redis.setex("doctor_" + part, self.cache_time,json.dumps(pkl))
            return _str

    def crawl_list(self,refresh = False):
        rlinks = self.redis.get('links')
        if rlinks != None and refresh == False:
            print("history links data")
            self.all_list = json.loads(rlinks)
        else:
            print("refresh links data")
            r = requests.get(self.list_url)
            rt = r.text
            rs = BeautifulSoup(rt, 'html.parser')
            sizebox = rs.find(id='Sizebox')
            links = sizebox.find_all(attrs={"onclick": re.compile("^javascript:location.href")})
            self.all_list = {}
            for link in links:
                _link = (link['onclick'].split('\'')[1])
                _title = (link.find('a')['title'])
                self.all_list[_title] = _link
            self.redis.setex("links", self.cache_time,json.dumps(self.all_list))
        self.list_update_time = time.time()
        text = ""
        i = 1
        for a,value in self.all_list.items():
            if a=='time':
                continue
            text += str(i) + ":" + str(a) + "\r\n"
            i += 1
        if (len(self.all_list) == 0):
            text = "還未開始看診"
        return text