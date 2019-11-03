import math
import random
import time
import requests
from requests.exceptions import SSLError
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning
disable_warnings(InsecureRequestWarning)

class Auth_code:
    session = None
    retry_time = 5

    def __init__(self,session):
        self.session = session

    @classmethod
    def get_auth_code(cls, session):
        '''
        验证码流程
        '''
        self = cls(session)
        image = self.download_code()
        if image:
            position = self.get_img_position(image)
            if not position:  # 打码失败
                return self.retry_get_auth_code()

            answer = ','.join(map(str, position))

            if not self.check_code(answer):
                return self.retry_get_auth_code()
            return position

        return None

    def retry_get_auth_code(self): # TODO 安全次数检测
        time.sleep(self.retry_time)
        return self.get_auth_code(self.session)

    def get_img_position(self, img):
        """
        获取图像坐标
        :param img_path:
        :return:
        """
        data = {
            'img': img
        }
        response = requests.post("https://12306-ocr.pjialin.com/check/", data=data, timeout=30)
        result = response.json()
        if result.get('msg') == 'success':
            pos = result.get('result')
            return self.get_image_position_by_offset(pos)
        else:
            print("从免费打码获取结果失败")
        return None

    def get_image_position_by_offset(self, offsets):
        positions = []
        width = 75
        height = 75
        for offset in offsets:
            random_x = random.randint(-5, 5)
            random_y = random.randint(-5, 5)
            offset = int(offset)
            x = width * ((offset - 1) % 4 + 1) - width / 2 + random_x
            y = height * math.ceil(offset / 4) - height / 2 + random_y
            positions.append(int(x))
            positions.append(int(y))
        return positions

    def download_code(self):
        '''
        获取验证码图片
        :return:
        '''
        try:
            url = "https://kyfw.12306.cn/passport/captcha/captcha-image64?login_site=E&module=login&rand=sjrand&_={}".format(
                int(time.time() * 1000))
            response = self.session.get(url)
            result = response.json()
            if result.get('result_code') == "0":
                if result.get('image'):
                    return result.get('image')
                raise SSLError('返回数据为空')
            elif result.get('result_code') == -4:
                print(result.get("result_message"))
                return False

        except SSLError:
            time.sleep(self.retry_time)
            return self.download_code()

        except:
            print("生成验证码失败")
            return False

    def check_code(self, answer):
        """
        校验验证码
        :return:
        """
        response = self.session.get(
            'https://kyfw.12306.cn/passport/captcha/captcha-check?answer={answer}&rand=sjrand&login_site=E&_={random}'.format(
                answer=answer, random=int(time.time())))
        result = response.json()
        if result.get('result_code') == '4':
            return True
        else:
            # {'result_message': '验证码校验失败', 'result_code': '5'}
            self.session.cookies.clear_session_cookies()

        return False