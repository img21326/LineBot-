import json
import requests
from bs4 import BeautifulSoup
import re
class Hospital():
    channel_secret = None
    channel_access_token = None
    redis_channel = None
    line_bot_api = None
    parser = None
    redis = None
    cache_time = None
    
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

    def get_from_redis(self):
        return None
    
    def set_to_redis(self):
        return None

class KT_Hospital(Hospital):
    _id = None
    web_url = 'http://www.ktgh.com.tw/'
    list_url = None
    all_link = None

    def set_url(self, _id):
        self._id = _id
        self.list_url = 'http://www.ktgh.com.tw/Reg_Clinic_Progress.asp?CatID={_id}&ModuleType=Y'.format(_id=_id)

    def crawl_list(self,refresh = False):
        rlinks = self.redis.get('links')
        if rlinks != None and refresh == False:
            print("history links data")
            self.all_link = json.loads(rlinks)
        else:
            print("refresh links data")
            r = requests.get(self.list_url)
            rt = r.text
            rs = BeautifulSoup(rt, 'html.parser')
            sizebox = rs.find(id='Sizebox')
            links = sizebox.find_all(attrs={"onclick": re.compile("^javascript:location.href")})
            self.all_link = {}
            for link in links:
                _link = (link['onclick'].split('\'')[1])
                _title = (link.find('a')['title'])
                self.all_link[_title] = _link
            self.redis.setex("links", self.cache_time,json.dumps(self.all_link))
        print(self.all_link)
        text = ""
        i = 1
        for a,value in self.all_link.items():
            if a=='time':
                continue
            text += str(i) + ":" + str(a) + "\r\n"
            i += 1
        if (len(self.all_link) == 0):
            text = "還未開始看診"
        return text