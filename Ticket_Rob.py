'''
抢票逻辑
'''
import json
import time

import requests
from base64 import b64decode

from Auth_code import Auth_code
from time_helper import isVaildTime
from Query import Query
from Order import Order
from config import config_data

from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning
disable_warnings(InsecureRequestWarning)
class UserJob:
    #TODO 看header变化
    def __init__(self):
        self.config = config_data
        self.username = self.config['username']
        self.password = self.config['password']
        self.session = requests.session()
        self.session.verify = False
        self.session.proxies = {
            #'https': '127.0.0.1:8000'
        }
        self.session.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:69.0) Gecko/20100101 Firefox/69.0",
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'Accept-Encoding': 'gzip, deflate',
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://kyfw.12306.cn/otn/confirmPassenger/initDc',
        }

    def login(self):
        data = {
            'username': self.username,
            'password': self.password,
            'appid': 'otn'
        }
        answer = Auth_code.get_auth_code(self.session)
        if answer:
            data["answer"] = answer
            self.request_device_id()
            response = self.session.post("https://kyfw.12306.cn/passport/web/login",data,allow_redirects=False)
            if response.status_code == 200:
                result = response.json()
                if result.get("result_code") == 0 : #登录成功
                    '''
                    login 获得 cookie uamtk
                    auth/uamtk      不请求，会返回 uamtk票据内容为空
                    /otn/uamauthclient 能拿到用户名
                    '''
                    new_tk =self.auth_uamtk()
                    user_name = self.auth_uamauthclient(new_tk)
                    print('Hello,{}'.format(user_name))
                    self.check_user_is_login()
                    return self.session

                elif result.get('result_code') == 2:  # 账号之内错误
                    print("登录失败 错误原因: {}".format(result.get('result_message')))

                elif result.get('result_code') == "5":
                    print("登录失败 错误原因: {}".format(result.get('result_message')))
                    return self.login()

                else:
                    print("登录失败 错误原因: {}".format(result.get('result_message')))
            else:
                print("登录失败 错误原因: 状态码为{}".format(response.status_code))

            return False

        else:
            time.sleep(5)
            self.session.cookies.clear_session_cookies()
            return self.login()




    def request_device_id(self):
        """
        获取加密后的浏览器特征 ID
        :return:
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36"
        }
        response = self.session.get(url="https://12306-rail-id-v2.pjialin.com/",headers=headers)
        if response.status_code == 200:
            try:
                result = json.loads(response.text)
                response = self.session.get(b64decode(result['id']).decode())
                if response.text.find('callbackFunction') >= 0:
                    result = response.text[18:-2]
                result = json.loads(result)
                self.session.cookies.update({
                    'RAIL_EXPIRATION': result.get('exp'),
                    'RAIL_DEVICEID': result.get('dfp'),
                })
            except:
                return False


    def auth_uamtk(self):
        response = self.session.post("https://kyfw.12306.cn/passport/web/auth/uamtk", {'appid': 'otn'})
        result = response.json()
        if result.get('newapptk'):
            return result.get('newapptk')
        # TODO 处理获取失败情况
        return False

    def auth_uamauthclient(self, tk):
        response = self.session.post("https://kyfw.12306.cn/otn/uamauthclient", {'tk': tk})
        result = response.json()
        if result.get('username'):
            return result.get('username')
        # TODO 处理获取失败情况
        return False

    def check_user_is_login(self):
        response = self.session.get("https://kyfw.12306.cn/otn/login/conf")
        is_login = response.json().get('data').get('is_login',False) == 'Y'
        if is_login:
            return self.get_user_info()  # 检测应该是不会维持状态，这里再请求下个人中心看有没有用，01-10 看来应该是没用  01-22 有时拿到的状态 是已失效的再加上试试

        return is_login

    def get_user_info(self):
        response = self.session.get("https://kyfw.12306.cn/otn/modifyUser/initQueryUserInfoApi")
        result = response.json()
        user_data = result.get('data.userDTO.loginUserDTO')
        # 子节点访问会导致主节点登录失效 TODO 可快考虑实时同步 cookie
        if user_data:
            return True
        return False



def main():
    if not isVaildTime():
        return None
    userjob = UserJob()
    login_session = userjob.login()
    if not login_session:
        return None
    # 登陆成功
    while True:
        query = Query(login_session)
        result_query = query.Query()
        if not result_query:
            return None
        #查询有票
        final_session= result_query[0]
        xd_data = result_query[1]
        order = Order(final_session,xd_data)
        buy = order.order()
        if buy:
            #下单成功 30分钟内支付
            print("购票成功")
            # 发送通知
        else:
            continue



if __name__ == '__main__':
    main()