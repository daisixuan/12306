import json
import re
import time
from urllib import parse
from config import config_data

class Order:
    session = None

    max_queue_wait = 60 * 5  # 最大排队时长
    current_queue_wait = 0
    retry_time = 3
    wait_queue_interval = 3

    order_id = 0

    notification_sustain_time = 60 * 30  # 通知持续时间 30 分钟
    notification_interval = 5 * 60  # 通知间隔

    def __init__(self, session,xd_data):
        self.session = session
        self.xd_data = xd_data
        self.config = config_data
        self.chezhan_code = self.chezhan()
        self.from_city_name = self.config['stations']['left']
        self.to_city_name = self.config['stations']['arrive']
        self.choose_seats = self.config["seats_type"]
        self.from_station_code = self.chezhan_code[self.from_city_name]
        self.to_station_code = self.chezhan_code[self.to_city_name]
        self.date = self.config['left_dates'][0]
        self.ticket_info_for_passenger_form = None
        self.key_check_isChange = None
        self.submit_token = None
        self.passengers_info = None
        self.seatType = None
        self.order_id =""
        self.passengerTicketStr = ""
        self.oldPassengerStr = ""
        self.seattype = {
            '特等座': 'P',
            '商务座': 9,
            '一等座': 'M',
            '二等座': 'O',
            '软卧': 4,
            '硬卧': 3,
            '动卧': 1,
            '软座': 2,
            '硬座': 1,
            '无座': 1,
        }
    def chezhan(self):
        f = open('chezhan.txt', 'r')
        chezhan_code = eval(f.read())
        return chezhan_code

    def order(self):
        order_request_res = self.submit_order_request()
        if not order_request_res:
            return None
        if not self.request_init_dc_page():
            return None
        if not self.get_passenger():
            return None
        if not self.check_order_info():
            return None
        if not self.get_queue_count():
            return None
        if not self.confirm_single_for_queue():
            return None
        if not self.query_order_wait_time():
            return None
        if self.order_id:
            return True

    def submit_order_request(self):
        xd_code = self.xd_data["xd_code"]
        data = {
            "secretStr": parse.unquote(xd_code),
            "train_date": self.date,
            "back_train_date": time.strftime("%Y-%m-%d", time.localtime()),
            "tour_flag": "dc",
            "purpose_codes": "ADULT",
            "query_from_station_name": self.from_city_name,
            "query_to_station_name": self.to_city_name,
        }
        res =self.session.post(url="https://kyfw.12306.cn/otn/leftTicket/submitOrderRequest",
                                data=data)
        result = res.json()
        if result.get('data') == 'N':
            return True
        else:
            if (str(result.get('messages', '')).find('未处理') >= 0):
               print("有未处理的订单")
               pass
        return False

    def request_init_dc_page(self):
        data = {
            "_json_att": "",
        }
        res = self.session.post(url="https://kyfw.12306.cn/otn/confirmPassenger/initDc",
                                 data=data)
        html = res.text
        form = re.search(r'var ticketInfoForPassengerForm *= *(\{.+\})', html)
        pattern2 = re.compile('\'key_check_isChange\':\'(.*?)\',', re.S)
        pattern1 = re.compile('globalRepeatSubmitToken = \'(.*?)\';', re.S)

        if html.find('系统忙，请稍后重试') != -1:
            return False
        try:
            self.ticket_info_for_passenger_form = json.loads(form.groups()[0].replace("'", '"'))
            self.key_check_isChange = str(re.search(pattern2, html).group(1))
            self.submit_token = str(re.search(pattern1, html).group(1))
        except:
            return False
        return True

    def get_passenger(self):
        data = {
            "_json_att": "",
            "REPEAT_SUBMIT_TOKEN": self.submit_token
        }
        res = self.session.post(url="https://kyfw.12306.cn/otn/confirmPassenger/getPassengerDTOs",
                                data=data)

        result = json.loads(res.text)
        self.passengers_info = result["data"]["normal_passengers"]
        seat = self.config['seats'][0]
        self.seatType = self.seattype[seat]
        name_list = self.config['members']


        for name in name_list:
            pts, ops = self.passenager_info_helper(name)
            self.passengerTicketStr += ''.join(pts) + "_"
            self.oldPassengerStr += ''.join(ops)
        self.passengerTicketStr.rstrip("_")
        if not self.passengerTicketStr and not self.oldPassengerStr:
            return False
        return True


    def passenager_info_helper(self,name):
        for i in range(len(self.passengers_info)):
            if name == self.passengers_info[i]["passenger_name"]:
                passenger_type = self.passengers_info[i]["passenger_type"]
                passenger_id_type_code = self.passengers_info[i]["passenger_id_type_code"]
                passenger_id_no = self.passengers_info[i]["passenger_id_no"]
                mobile_no = self.passengers_info[i]["mobile_no"]
                allEncStr = self.passengers_info[i]["allEncStr"]
                passengerTicketStr = "{},0,{},{},{},{},{},N,{}".format(self.seatType,
                                                                       passenger_type,
                                                                       name,
                                                                       passenger_id_type_code,
                                                                       passenger_id_no,
                                                                       mobile_no,
                                                                       allEncStr)
                oldPassengerStr = "{},{},{},{}_".format(name, passenger_id_type_code, passenger_id_no,
                                            passenger_type)
                return passengerTicketStr, oldPassengerStr

    def check_order_info(self):
        data = {
            "cancel_flag": 2,
            "bed_level_order_num": "000000000000000000000000000000",
            "passengerTicketStr": self.passengerTicketStr,
            "oldPassengerStr": self.oldPassengerStr,
            "tour_flag": "dc",
            "randCode": "",
            "whatsSelect": 1,
            "_json_att": "",
            "REPEAT_SUBMIT_TOKEN": self.submit_token
        }
        res = self.session.post(url="https://kyfw.12306.cn/otn/confirmPassenger/checkOrderInfo",
                                 data=data)
        result = json.loads(res.text)
        if result.get("data").get("submitStatus"):
            return True
        else:
            if not result.get('data.isNoActive'):
                print("网络错误")
            else:
                if result.get('data.checkSeatNum'):
                    error = '无法提交您的订单! ' + result.get('data.errMsg')
                else:
                    error = '出票失败! ' + result.get('data.errMsg')
        return False

    def get_queue_count(self):
        timeArray = time.strptime(self.date, "%Y-%m-%d")
        timeStamp = int(time.mktime(timeArray))
        train_date_change = time.strftime("%a %b %d %Y", time.localtime(timeStamp))
        data = {
                "train_date": "{} 00:00:00 GMT+0800 (中国标准时间)".format(train_date_change),
                "train_no": self.xd_data["train_no"],
                "stationTrainCode": self.xd_data["stationTrainCode"],
                "seatType": self.seatType,
                "fromStationTelecode": self.from_station_code,
                "toStationTelecode": self.to_station_code,
                "leftTicket": self.xd_data["leftTicket"],
                "purpose_codes": self.ticket_info_for_passenger_form['purpose_codes'],
                "train_location": self.ticket_info_for_passenger_form['train_location'],
                "_json_att": "",
                "REPEAT_SUBMIT_TOKEN": self.submit_token,
            }
        res = self.session.post(url="https://kyfw.12306.cn/otn/confirmPassenger/getQueueCount",
                                data=data)
        result = res.json()
        ticket = result.get("data").get("ticket")
        if ticket:
            return True
        print("目前该列车无票")
        return False

    def confirm_single_for_queue(self):
        data = {
            "passengerTicketStr": self.passengerTicketStr,
            "oldPassengerStr": self.oldPassengerStr,
            "randCode": "",
            "purpose_codes": self.ticket_info_for_passenger_form['purpose_codes'],
            "key_check_isChange": self.key_check_isChange,
            "leftTicketStr": self.xd_data["leftTicket"],
            "train_location": self.ticket_info_for_passenger_form['train_location'],
            "choose_seats": self.choose_seats,
            "seatDetailType": "000",
            "whatsSelect": 1,
            "roomType": "00",
            "dwAll": "N",
            "_json_att": "",
            "REPEAT_SUBMIT_TOKEN": self.submit_token,
        }
        res6 = self.session.post(url="https://kyfw.12306.cn/otn/confirmPassenger/confirmSingleForQueue",
                                 data=data)
        result = res6.json()
        if 'data' in result:
            if result.get('data').get('submitStatus'):  # 成功
                return True
        return False

    def query_order_wait_time(self):
        data = {
            'random': str(int(time.time() * 1000)),
            'tourFlag': 'dc',
            '_json_att': '',
            'REPEAT_SUBMIT_TOKEN': self.submit_token,
        }
        res = self.session.get(url="https://kyfw.12306.cn/otn/confirmPassenger/queryOrderWaitTime?{}".format(parse.urlencode(data)))
        result = res.json()
        if result.get('status') and 'data' in result:
            result_data = result['data']
            order_id = result_data.get('orderId')
            if order_id:  # 成功
                self.order_id = order_id
                return True
            elif result_data.get("msg"):
                print(result_data.get("msg"))
                return False
            else:
                waittime = int(result_data['waitTime'])
                print("正在排队,还需要%d秒" % waittime)
                time.sleep(waittime)
                return self.query_order_wait_time()