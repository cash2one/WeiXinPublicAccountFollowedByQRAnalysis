#功能#

方便微信公众号管理二维码的网站,[点此实用](http://162.243.152.178/manage/QR/),帐号smie2012,密码:123456.很多公众号通过让用户扫描二维码来进行关注,这个网站可以快速生成二维码,对每个二维码添加备注进行区分,并且能统计通过每个二维码关注的用户数量,这样就方便微信公众号的管理者了解不同时间不同地点对微信公众号的宣传效果,以便今后进行更好的宣传.

#使用#

下载工程,替换 server.py 中 APPID, SECRET为自己公众号的即可.然后运行在公众号所绑定的服务器上.需要安装 urllib, urllib2, json, MySQLdb, wechat_sdk, flask 等库.数据库中建立 QR 数据库:

	create database QR;
	
建立两个表:

	create table QR(scene_id int,remark text,pic text,time datetime,web text,ticket text,primary key (scene_id));
	
	create table event(openID varchar(10),ticket text,time datetime,primary key (openID));

