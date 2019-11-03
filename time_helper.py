import time
def isVaildTime():
    now_time = time.strftime("%H:%M:%S", time.localtime())
    print("当前时间为%s"%now_time)
    if now_time < "23:00:00" and now_time > "06:00:00":
        return True
    else:
        print("06:00:00到23:00:00是服务器维护时间，期间无法登陆买票")
        #TODO 加上到6点自动开启抢票
        return False