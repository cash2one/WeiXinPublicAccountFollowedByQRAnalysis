# -*-coding:utf-8-*-
# __author__ = "lufo"

import urllib, urllib2
import json
import time, datetime
import MySQLdb
import io
from wechat_sdk import WechatBasic
from wechat_sdk.messages import EventMessage
from flask import Flask, request, redirect, url_for, render_template, make_response, send_file

app = Flask(__name__)
app.debug = True

access_token = ""
valid_time = 0  # accsee_token 剩余有效时间
SESSION_TIMEOUT = 60 * 30
DEFAULT_BEGIN = "0001-01-01 00:00:00"
DEFAULT_END = "9999-01-01 00:00:00"


# functions
def getAccessToken():
    """
    获取 access token
    :return:access token
    """
    APPID = "wx1e7e366133874e70"
    SECRET = "ace70e4b8df4ad339fd9862d6b429207"
    global access_token, valid_time  # valid_time is the time when access_token is valid
    URL = "https://api.weixin.qq.com/cgi-bin/token"
    data = {
        "grant_type": "client_credential",
        "appid": APPID,
        "secret": SECRET
    }
    para = urllib.urlencode(data)
    res = json.loads(urllib2.urlopen(URL + "?" + para).read())
    access_token = res["access_token"]
    expires_in = res["expires_in"]
    print access_token, expires_in
    valid_time = time.time() + expires_in / 2  # expires_in为有效的时间,单位s


def getQR():
    """
    生成一个二维码
    """
    global access_token, valid_time
    db = MySQLdb.connect(host="localhost", user="root", passwd="lxb", db="QR", charset="utf8")
    cursor = db.cursor()
    count = cursor.execute("""select * from QR""")
    action_name = "QR_LIMIT_SCENE"
    scene_id = count + 1
    para = {
        "action_name": action_name,
        "action_info": {
            "scene": {
                "scene_id": scene_id
            }
        }
    }
    if time.time() > valid_time:
        getAccessToken()
    url_to_get_ticket = "https://api.weixin.qq.com/cgi-bin/qrcode/create?access_token=" + access_token
    req = urllib2.Request(url_to_get_ticket, json.dumps(para))
    res = urllib2.urlopen(req)
    dict_res = json.loads(res.read())
    ticket = dict_res["ticket"]
    url = dict_res["url"]
    temp = {
        "ticket": ticket
    }
    encode_ticket = urllib.urlencode(temp).split("ticket=")[1]
    # print encode_ticket
    url_to_get_QR = "https://mp.weixin.qq.com/cgi-bin/showqrcode?ticket=" + encode_ticket
    # print url_to_get_QR
    # QR = urllib.urlopen(url_to_get_QR).read()
    cursor.execute("""select now()""")
    date = cursor.fetchone()
    print "scene_id=%s,remark=%s,pic=%s,time=%s,web=%s" % (str(scene_id), str(scene_id), url_to_get_QR,
                                                           date[0], url)
    # create table QR(scene_id int,remark text,pic text,time datetime,web text,ticket text,primary key (scene_id));
    cursor.execute("""insert into QR values(%s,%s,%s,%s,%s,%s)""", (str(scene_id), str(scene_id), url_to_get_QR,
                                                                    date[0], url, encode_ticket ))

    print dict_res
    db.commit()
    cursor.close()
    db.close()


def QRRequest(n):
    """
    生成一个二维码
    :param n:生成二维码的数量
    """
    for i in range(n):
        getQR()


def changeQRName(scene_id, remark):
    """
    修改二维码备注
    :param scene_id:二维码参数
    :param remark:二维码备注
    :return:修改成功返回 true,否则返回 false
    """
    db = MySQLdb.connect(host="localhost", user="root", passwd="lxb", db="QR", charset="utf8")
    cursor = db.cursor()
    changed = cursor.execute("""update QR set remark = %s where scene_id = %s""", ((remark), str(scene_id),))
    if changed:
        # print "QR which scene_id=%s remark changed to %s" % (scene_id, remark)
        db.commit()
        cursor.close()
        db.close()
        return True
    else:
        print "remark didn\"t changed"
        return False


def receiveQRFollowInfo(xml):
    """
    收到微信发来的通过二维码关注的事件数据,记录到数据库
    :param xml:表示时间的xml
    :return:成功记录返回 true,否则返回 false
    """
    token = "test"
    wechat = WechatBasic(token=token)
    body_text = xml
    wechat.parse_data(body_text)
    # 获得解析结果, message 为 WechatMessage 对象 (wechat_sdk.messages中定义)
    message = wechat.get_message()
    response = None
    if isinstance(message, EventMessage):  # 事件信息
        if message.type == "subscribe":  # 关注事件(包括普通关注事件和扫描二维码造成的关注事件)
            if message.key and message.ticket:  # 如果 key 和 ticket 均不为空，则是扫描二维码造成的关注事件
                response = "用户尚未关注时的二维码扫描关注事件"
                db = MySQLdb.connect(host="localhost", user="root", passwd="lxb", db="QR", charset="utf8")
                cursor = db.cursor()
                cursor.execute("""select now()""")
                date = cursor.fetchone()
                openID = message.source
                ticket = message.ticket
                print "%s followed by %s in %s" % (str(openID), str(ticket), date[0])
                # create table event(openID varchar(10),ticket text,time datetime,primary key (openID));
                cursor.execute("""insert into event values(%s,%s,%s)""", (str(openID), str(ticket), date[0],))
                db.commit()
                cursor.close()
                db.close()
    print "不是二维码关注事件"
    return False


def followQuantityCheck(begin, end):
    """
    查询一段时间内各个二维码带来的关注数量
    :param begin:开始时间
    :param end:结束时间
    :return:list,list 的每个元素为一个含有两个元素的 dict,第一个为 scene_id,第二个为这个二维码带来的关注数
    """
    db = MySQLdb.connect(host="localhost", user="root", passwd="lxb", db="QR")
    cursor = db.cursor()
    cursor.execute("""select * from QR""")
    records = cursor.fetchall()
    QR_list = []
    for record in records:
        QR_list.append([int(record[0]), str(record[5])])
    # print QR_list
    result = []
    for QR in QR_list:
        scene_id = QR[0]
        ticket = urllib.unquote(QR[1])  # 对url 编码进行解码
        count = cursor.execute("""select * from event where time >= %s and time < %s and ticket=%s""",
                               (str(begin), str(end), str(ticket),))
        # print ticket, count
        result.append({"scene_id": scene_id, "count": int(count)})
    # print result
    return result


def fraudQRFollowCheck(openID):
    """
    查询这个用户是否曾经关注过
    :param openID:关注者openID
    :return:关注过则为 true,否则为 false
    """
    db = MySQLdb.connect(host="localhost", user="root", passwd="lxb", db="QR", charset="utf8")
    cursor = db.cursor()
    followed = cursor.execute("""select * from event where openID = %s""", (str(openID),))
    if followed:
        print openID + " has followed"
        return True
    else:
        print openID + " hasn't followed"
        return False


def loginCheck(uid, psw):
    """
    检测账户是否合法
    :param uid:用户名
    :param psw:密码
    :return:合法为 True,否则 False
    """
    if uid == "smie2012" and psw == "123456":
        print "login successful"
        return True
    else:
        print "login error"
        return False


def loggedIn():
    """
    Check whether a user is logged in
    """
    # print request.cookies.get("uid") and request.cookies.get("psw")
    return request.cookies.get("uid") and request.cookies.get("psw")


def getDataToShow(begin=DEFAULT_BEGIN, end=DEFAULT_END):
    """
    从数据库获取将要在网页上显示的内容,添加事件从begin 到 end
    :return:list,每个元素为 dict,表示要显示的信息
    """
    follower_list = followQuantityCheck(begin, end)
    db = MySQLdb.connect(host="localhost", user="root", passwd="lxb", db="QR", charset="utf8")
    cursor = db.cursor()
    cursor.execute("""select * from QR""")
    records = cursor.fetchall()
    data = []
    for record in records:
        scene_id = record[0]
        follower = [i for i in follower_list if i["scene_id"] == scene_id]
        # print (record[1])
        # remark = unicode(urllib.unquote(str(record[1])), "utf-8")  # 将url 编码转为 unicode 对象
        remark = (record[1])
        # print "remark=" + remark
        item = {
            "scene_id": int(scene_id),
            "pic": str(record[2]),
            "type": "永久性",
            "count": int(follower[0]["count"]),
            "remark": remark,
            "time": str(record[3])
        }
        data.append(item)
        # for item in data:
        # print item
    return data


def getOneDataToShow(scene_id=1):
    """
    获取展示某一二维码详情页的 data
    :param scene_id: 该二维码的scene_id
    :return: dict,有一个字典item,一个字典数组hold,item内容有scene_id,图片的链接pic,二维码的备注remark,二维码的总的关注数count,hold里面的每一项有两个成员,第一个是date,代表关注的时间,第二个是num,代表今天关注的数量
    """
    data = {}
    temp_data = getDataToShow()
    for item in temp_data:
        if item["scene_id"] == scene_id:
            data["info"] = item
            break
    begin_str = data["info"]["time"]  # 最早有人关注的时间为二维码的创建时间
    begin = datetime.datetime.strptime(begin_str, '%Y-%m-%d %H:%M:%S')
    begin.replace(hour=0, minute=0, second=0)
    end = datetime.datetime.today()
    hold = []
    while begin < end:
        next_day = begin + datetime.timedelta(1)
        begin_temp = begin.strftime('%Y-%m-%d %H:%M:%S')
        end_temp = next_day.strftime('%Y-%m-%d %H:%M:%S')
        follow_info = followQuantityCheck(begin_temp, end_temp)
        for item in follow_info:
            if item["scene_id"] == scene_id:
                count = item["count"]
                break
        if count > 0:
            item = {"date": begin_temp, "num": count}
            hold.append(item)
        begin = next_day
    data["hold"] = hold
    data_list = []
    data_list.append(data)
    print data_list
    return data_list


# pages
@app.route("/weChatMsg/", methods=["GET", "POST"])
def verify():
    """
    接收微信发来的事件信息,现在只需要记录一种,即扫描二维码后关注,把数据计入数据库
    """
    token = "test"
    wechat = WechatBasic(token=token)
    if request.method == "GET":
        signature = request.args.get("signature")
        timestamp = request.args.get("timestamp")
        nonce = request.args.get("nonce")
        echostr = request.args.get("echostr")
        if wechat.check_signature(signature=signature, timestamp=timestamp, nonce=nonce):
            return echostr
    if request.method == "POST":
        print "enter post"
        body_text = request.data
        receiveQRFollowInfo(body_text)


@app.route("/manage/QR/")
def index():
    """
    检查cookies,如果没有登录就重定向至/manage/login,如果有且检查通过则返回操作页
    """
    if not loggedIn():
        return redirect(url_for("login"))
        # return render_template("login.html")
    else:
        return redirect(url_for("option"))


@app.route("/manage/login/")
def login():
    """
    用户登录
    """
    action = request.args.get("action", "none")
    if action == "none":
        return render_template("login.html")
    else:
        uid = request.args.get("username")
        psw = request.args.get("password")
        if loginCheck(uid, psw):
            response = make_response(redirect(url_for("index")))
            response.set_cookie("uid", uid, SESSION_TIMEOUT)
            response.set_cookie("psw", psw, SESSION_TIMEOUT)
            # return "login successful"
            # return render_template("index.html")
            return response
        else:
            return "login error"


@app.route("/manage/QR/option/")
def option():
    """
    处理用户对二维码的增,改,查操作
    """
    if not loggedIn():
        return redirect(url_for("login"))
    else:
        action = request.args.get("action", "none")
        print action
        if action == "addQR":  # 生成n个二维码
            n = request.args.get("number", 0)
            if n == "":
                n = 0
            else:
                n = int(n)
            QRRequest(n)
            return render_template("index.html", data=getDataToShow())
        elif action == "search":  # 关注量只显示事件A,B之间的。
            begin_year = str(request.args.get("BYYYY", DEFAULT_BEGIN))
            begin_month = str(request.args.get("BMM", DEFAULT_BEGIN))
            begin_day = str(request.args.get("BDD", DEFAULT_BEGIN))
            end_year = str(request.args.get("EYYYY", DEFAULT_BEGIN))
            end_month = str(request.args.get("EMM", DEFAULT_BEGIN))
            end_day = str(request.args.get("EDD", DEFAULT_BEGIN))
            begin = begin_year + "-" + begin_month + "-" + begin_day + " 00:00:00"
            end = end_year + "-" + end_month + "-" + end_day + " 23:59:59"
            if begin == "":  # 未输入 time 时当做DEFAULT_BEGIN处理
                begin = DEFAULT_BEGIN
            else:
                begin = begin + " 00:00:00"
            if end == "":
                end = DEFAULT_END
            else:
                end = end + " 00:00:00"
            return render_template("index.html", data=getDataToShow(begin, end))
        elif action == "download":  # 下载id为xxx的二维码图片
            scene_id = request.args.get("qid", 1)
            db = MySQLdb.connect(host="localhost", user="root", passwd="lxb", db="QR", charset="utf8")
            cursor = db.cursor()
            cursor.execute("""select pic from QR where scene_id = %s""", (str(scene_id),))
            record = cursor.fetchone()
            pic_url = record[0]
            return send_file(io.BytesIO(urllib.urlopen(pic_url).read()), attachment_filename=str(scene_id) + ".jpeg",
                             as_attachment=True)
            # return urllib.urlopen(pic_url).read()
        elif action == "modify":  # 修改scene_id=i 的二维码备注
            scene_id = request.args.get("qid", 1)
            remark = request.args.get("remark", str(scene_id))
            # print "encode="+encode_remark
            # remark = unicode((encode_remark), "utf-8")  # 将url 编码转为 unicode 对象
            # print remark
            changeQRName(scene_id, remark)
            print "changed"
            return render_template("index.html", data=getDataToShow())
            # return redirect(url_for("option"), code=302)
        elif action == "detail":
            scene_id = request.args.get("qid", 1)
            return render_template("test.html", data=getOneDataToShow(scene_id))
        else:  # 请求获取网页
            return render_template("index.html", data=getDataToShow())


def main():
    getOneDataToShow()
    # QRRequest(0)
    # changeQRName(1, "t")
    # fraudQRFollowCheck("")
    # followQuantityCheck("0000-00-00 00:00:00", "9999-00-00 00:00:00")
    # receiveQRFollowInfo()
    # loginCheck("", "")
    # getDataToShow()


if __name__ == "__main__":
    # main()
    app.run(host="0.0.0.0", port=80)
    # app.run(port=8000)