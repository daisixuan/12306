import json
import time
from urllib import parse

import requests
from prettytable import PrettyTable

from config import config_data
class Query:

    def __init__(self,session):
        self.session = session
        self.config = config_data
        self.chezhan_code = self.chezhan()
        self.from_city_name = self.config['stations']['left']
        self.to_city_name = self.config['stations']['arrive']
        self.from_station = self.encoding_station(self.from_city_name)
        self.to_station = self.encoding_station(self.to_city_name)
        self.from_station_code = self.chezhan_code[self.from_city_name]
        self.to_station_code = self.chezhan_code[self.to_city_name]
        self.date = self.config['left_dates'][0]
        self.add_station_cookie()

    def chezhan(self):
        f = open('chezhan.txt', 'r')
        chezhan_code = eval(f.read())
        return chezhan_code

    def encoding_station(self,city_name):
        station_name = "{}{}".format(str(city_name.encode('unicode-escape'),
                                        encoding="utf-8").replace("\\", "%")
                                     + parse.quote(","),self.chezhan_code[city_name])
        return station_name

    def add_station_cookie(self):
        buycookies = {
            "_jc_save_fromStation": self.from_station,
            "_jc_save_toStation": self.to_station,
            "_jc_save_fromDate": self.date,
            "_jc_save_toDate": time.strftime("%Y-%m-%d", time.localtime()),
            "_jc_save_wfdc_flag": "dc"
        }
        requests.utils.add_dict_to_cookiejar(self.session.cookies, buycookies)

    def Query(self):
        url = "https://kyfw.12306.cn/otn/leftTicket/query?" \
              "leftTicketDTO.train_date={}&" \
              "leftTicketDTO.from_station={}&" \
              "leftTicketDTO.to_station={}&" \
              "purpose_codes=ADULT".format(self.date,
                                           self.from_station_code,
                                           self.to_station_code)
        r = self.session.get(url)
        try:
            result = json.loads(r.text)
        except:
            print("无查询结果")
            return None

        for i in result['data']['result']:
            item = i.split('|')
            if item[3] == self.config['train_code'][0]:
                xd_data = {
                    "xd_code": item[0],
                    "train_no": item[2],
                    "stationTrainCode": item[3],
                    "leftTicket": item[12],
                    "train_location": item[15],
                }
                data = {
                    "swz_num": item[32] or item[25],  # 商务座
                    "ydz_num": item[31],  # 一等座
                    "edz_num": item[30],  # 二等座
                    "gjrw_num": item[21],  # 高级软卧
                    "rw_num": item[23],  # 软卧
                    "dw_num": item[27],  # 动卧
                    "yw_num": item[28],  # 硬卧信息在28号位置
                    "rz_num": item[24],  # 软座信息在24号位置
                    "yz_num": item[29],  # 硬座信息在29号位置
                    "wz_num": item[26],  # 无座信息在26号位置
                }

                Seat_type_parse = {
                     '商务座': 'swz_num',
                     '一等座': 'ydz_num',
                     '二等座': 'edz_num',
                     '高级软卧': 'gjrw_num',
                     '软卧': 'rw_num',
                     '动卧': 'dw_num',
                     '硬卧': 'yw_num',
                     '软座': 'rz_num',
                     '硬座': 'yz_num',
                     '无座': 'wz_num',
                     '其他信息': 'qt_num'
                }

                for key, value in data.items():
                    if value == "无":
                        data[key] = ""

                seat_num = Seat_type_parse[self.config['seats'][0]]
                if data[seat_num]:
                    if data[seat_num] == "有":
                        print("{}当前还有位置".format(self.config['seats'][0]))
                        return self.session,xd_data
                    else:
                        print("{}当前还有{}个位置".format(self.config['seats'][0],data[seat_num]))
                        return self.session,xd_data
                else:
                    print("{}当前没有位置".format(self.config['seats'][0]))
                    time.sleep(60)
                    return self.Query


