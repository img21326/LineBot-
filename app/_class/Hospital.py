import json
import requests
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime, timedelta
from .. import db
from ..model.Usage import UsageModel

class Hospital():
    name = None
    channel_secret = None
    channel_access_token = None
    redis_channel = None
    line_bot_api = None
    parser = None
    redis = None
    cache_time = None

    all_list = None
    list_update_time = None
    
    def __init__(self,name, sct, asst, rdc, lba = None, ps = None):
        self.name = name
        self.channel_secret = sct
        self.channel_access_token = asst
        self.redis_channel = rdc
        self.line_bot_api = lba
        self.parser = ps

    def set_url(self):
        pass

    def num_to_part(self, part):
        if str(part).isnumeric():
            try:
                part = int(part)
                part = list(self.all_list)[part-1]
            except Exception as e:
                print(e)
                part = 'error'
        return part

    def crawl_list(self,refresh=False):
        return None

    def insert_usage(self,part,user_id,hospital):
        usage = UsageModel(
                    user_id=user_id,
                    hospital= hospital,
                    part=part
                    )
        db.session.add(usage)
        db.session.commit()

    def crawl_data(self,part,user_id,refresh=False):
        return None

class eight03_Hospital(Hospital):
    url = 'https://803.mnd.gov.tw/opd/med_info.php'
    def crawl_data(self,part,user_id,refresh=False):
        self.crawl_list()
        part = self.num_to_part(part)
        if part not in self.all_list:
            return "醫生還未開始看診"
        _str = part + '\r\n--------------------------------\r\n'
        for r in self.all_list[part]:
            _str += '醫師:' + r['doctor'] + "(" + str(r['subtitle']) + ")" +'\r\n'
            _str += '目前看診號次:' + str(r['num']) + '\r\n--------------------------------\r\n'
        _str = _str + '最後更新時間:' + str(datetime.now().strftime("%Y/%m/%d %H:%M"))
        return _str

    def crawl_list(self, refresh=False):
        rlinks = self.redis.get('links')
        if rlinks != None and refresh == False:
            print("history links data")
            self.all_list = json.loads(rlinks)
        else:
            print("refresh links data")
            r = requests.get(url)
            j = json.loads(r.text)
            all_list = {}
            for i in j:
                if (len(i['INFO']['title']) > 0):
                    all_list[i['INFO']['title']] = []
            for i in j:
                if (len(i['INFO']['title']) > 0):
                    all_list[i['INFO']['title']].append({
                        'subtitle': i['INFO']['subtitle'],
                        'doctor': i['INFO']['doctor'],
                        'num': i['INFO']['num'],
                    })
            self.list_update_time = time.time()
            all_list['list_update_time'] = self.list_update_time
            self.all_list = all_list
            self.redis.setex("links", self.cache_time,json.dumps(self.all_list))
        text = ""
        i = 1
        for a,value in self.all_list.items():
            if a == 'list_update_time':
                continue
            text += str(i) + ":" + str(a) + "\r\n"
            i += 1
        if (len(self.all_list) == 0):
            text = "還未開始看診"
        return text 

class VGH_Hospital(Hospital):
    list_url = 'https://www.vghtc.gov.tw/APIPage/OutpatientProcess'
    def crawl_data(self, part,user_id, refresh = False):
        self.crawl_list()
        part = self.num_to_part(part)
        if part not in self.all_list:
            return "醫生還未開始看診"
        self.insert_usage(part,user_id,self.name)
        data = self.redis.get('doctor_' + part)
        if data != None and refresh == False:
            print("history doctor data")
            data = json.loads(data)
            return data['str']
        else:
            print("refresh doctor data")
            r = requests.get(self.all_list[part])
            rt = r.text
            rs = BeautifulSoup(rt, 'html.parser')
            result2 = rs.find("div", class_="table-responsive-close").find("tbody" , class_ = "row-i")
            orderlist = ["order-1","order-8","order-4","order-3","order-5","order-6"]
            all_result = []
            for i in range(len(result2.find_all("tr"))): #看診數 or 醫生數
                result3 = result2.find_all("tr")[i]
                result_dict = {}
                for j in range(len(orderlist)): #醫生門診看診進度
                    result_dict[result3.find("td" , class_ = orderlist[j]).get("data-th")] = result3.find("td" , class_ = orderlist[j]).text
                result_dict[(result3.find("td" , class_ = "order-2").get("data-th"))] = int(result3.find("td" , class_ = "order-2").find("span").text)
                all_result.append(result_dict)
            _str = str(part) + '\r\n--------------------------------\r\n'
            
            for r in all_result:
                _str += '醫師:' + r['醫師'] + "(" + str(r['診間']) + ")" +'\r\n'
                _str += '目前看診號次:' + str(r['目前看診號次']) + '\r\n'
                _str += '過號待看人數:' + str(r['過號待看人數'])+ '\r\n--------------------------------\r\n'
            _str = _str + '最後更新時間:' + str(datetime.now().strftime("%Y/%m/%d %H:%M"))
            pkl = {
                'str': _str,
                'time': time.time(),
            }
            print(_str)
            self.redis.setex("doctor_" + part, self.cache_time,json.dumps(pkl))
            return _str
    def crawl_list(self, refresh=False):
        rlinks = self.redis.get('links')
        if rlinks != None and refresh == False:
            print("history links data")
            self.all_list = json.loads(rlinks)
        else:
            print("refresh links data")
            r = requests.get(self.list_url)
            rt = r.text
            soup1 = BeautifulSoup(rt, 'html.parser')
            result1 = soup1.find_all("li", class_="row-p1")
            all_list = {}
            for i in range(len(result1)):
                all_list[result1[i].find("a").get("title")] = "https://www.vghtc.gov.tw" + result1[i].find("a").get("href")
            self.list_update_time = time.time()
            all_list['list_update_time'] = self.list_update_time
            self.all_list = all_list
            self.redis.setex("links", self.cache_time,json.dumps(self.all_list))
        text = ""
        i = 1
        for a,value in self.all_list.items():
            if (a == 'list_update_time'):
                continue
            text += str(i) + ":" + str(a) + "\r\n"
            i += 1
        if (len(self.all_list) == 0):
            text = "還未開始看診"
        return text

class CCGH_Hospital(Hospital):
    url = 'http://api.ccgh.com.tw/api/GetClinicMainList/GetClinicMainData'
    
    def crawl_data(self, part,user_id):
        if (self.crawl_list() == False):
            return "還未開始看診"
        part = self.num_to_part(part)
        if part not in self.all_list:
            return "醫生還未開始看診"
        self.insert_usage(part,user_id,self.name)
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

    def crawl_data(self, part, user_id,refresh = False):
        self.crawl_list()
        part = self.num_to_part(part)
        if part not in self.all_list:
            return "醫生還未開始看診"
        self.insert_usage(part,user_id,self.name)
        data = self.redis.get('doctor_' + part)
        if data != None and refresh == False:
            print("history doctor data")
            data = json.loads(data)
            return data['str']
        else:
            print("refresh doctor data")
            r = requests.get("http://www.ktgh.com.tw/" + self.all_list[part])
            rt = r.text
            rs = BeautifulSoup(rt, 'html.parser')
            _str = str(part) + '\r\n--------------------------------\r\n'
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