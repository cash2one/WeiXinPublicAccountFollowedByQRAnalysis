# -*-coding:utf-8-*-
# __author__ = "lufo"

from functions import *

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
        # print "enter post"
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
        # print action
        if action == "addQR":  # 生成n个二维码
            n = request.args.get("number", 0)
            if n == "":
                n = 0
            else:
                n = int(n)
            QRRequest(n)
            return render_template("index.html", data=getDataToShow())
        elif action == "search":  # 关注量只显示事件A,B之间的。
            begin, end = getDate()
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
            # print "changed"
            return render_template("index.html", data=getDataToShow())
            # return redirect(url_for("option"), code=302)
        elif action == "detail":
            scene_id = request.args.get("qid", 1)
            return render_template("detail.html", data=getOneDataToShow(int(scene_id)))
        elif action == "detail_search":
            scene_id = request.args.get("qid", 1)
            begin, end = getDate()
            return render_template("detail.html", data=getOneDataToShow(int(scene_id), begin, end))
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
    # app.run(host="0.0.0.0", port=80)
    app.run(port=8000)