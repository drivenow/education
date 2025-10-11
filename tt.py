# -*- coding: utf-8 -*-
# from pathlib import Path
# from openai import OpenAI
#
# speech_file_path = "siliconcloud-generated-speech.wav"
#
# client = OpenAI(
#     api_key="sk-kcrdqzlwcmdygxnmflzptjnofxzdhquhjtfjagkdcqrnodof", # 从 https://cloud.siliconflow.cn/account/ak 获取
#     base_url="https://api.siliconflow.cn/v1"
# )
#
# with client.audio.speech.with_streaming_response.create(
#   model="FunAudioLLM/CosyVoice2-0.5B", # 支持 fishaudio / GPT-SoVITS / CosyVoice2-0.5B 系列模型
#   voice="FunAudioLLM/CosyVoice2-0.5B:claire", # 系统预置音色
#   # 用户输入信息
#   input="你能用高兴的情感说吗？<|endofprompt|>今天真是太开心了，马上要放假了！I'm so happy, Spring Festival is coming!",
#   response_format="wav" # 支持 mp3, wav, pcm, opus 格式
# ) as response:
#     response.stream_to_file(speech_file_path)


#创建日期：2025-02-12 23:55:47
#触发请求：https://search5-search-lq.amemv.com/aweme/v2/search/item/
'''请求头：
POST /aweme/v2/search/item/?iid=1863029258498283&device_id=2760199244630556&ac=wifi&channel=douyin-huidu-gw-huidu-2940&aid=1128&app_name=aweme&version_code=290400&version_name=29.4.0&device_platform=android&os=android&ssmix=a&device_type=SM-N9700&device_brand=samsung&language=zh&os_api=28&os_version=9&manifest_version_code=290400&resolution=1600*900&dpi=240&update_version_code=29400100&_rticket=1739375445186&first_launch_timestamp=1738855081&last_deeplink_update_version_code=0&cpu_support64=true&host_abi=arm64-v8a&is_guest_mode=0&app_type=normal&minor_status=0&appTheme=light&is_preinstall=0&need_personal_recommend=1&is_android_pad=0&is_android_fold=0&ts=1739375444&cdid=1d485a3a-26ac-4010-b1c0-ae4819aaca49 HTTP/1.1
Host: search5-search-lq.amemv.com
Connection: keep-alive
Content-Length: 1961
Cookie: passport_csrf_token=790bd1e488b6b17f813b367618aa3ad3; passport_csrf_token_default=790bd1e488b6b17f813b367618aa3ad3; store-region=cn-js; install_id=1863029258498283; ttreq=1$e99d1602a7eef109d74c3de9d658aca429e890d6; d_ticket=717ac90410bacc6904ff3597ab511fc9ecaf2; multi_sids=2915556143923976%3Ad07cc06d7da23a3679f5e982b5c7582d; odin_tt=7e274ec14434c9000c6c994155faecce028dd9143c41f91cf509cc6f42614589345c16963f6f8f5827d538dec2a71d6fcc9e1c626c3b42dcf72edee4d88dd55f329f84e260f734c8c91e6fc4f0304a84; passport_assist_user=CkHi5-Z4Apol6uSoRjDgMRqoUg9vHk4HcHQRRSWPKmPPV9Tc4XhBT4QPRiEFAed4vx-4O-SWzRUicak6jpRGEYBvghpKCjz1Dj2t_dpeJ0wTjUspvIDrDnSlfiXssGW9ufM8HZD6MW4UG60mUGUF-6a9RvDgAKLSkniGO8I0-VVXgVkQxuzoDRiJr9ZUIAEiAQOCdHcN; n_mh=I6zGGiyQ5jH87rM4fH_RdBnvskHBmZbyT0e1hrtaDL8; sid_guard=d07cc06d7da23a3679f5e982b5c7582d%7C1738855163%7C5184000%7CMon%2C+07-Apr-2025+15%3A19%3A23+GMT; uid_tt=6f1ce3929c109ca31698c658d00d37c1; uid_tt_ss=6f1ce3929c109ca31698c658d00d37c1; sid_tt=d07cc06d7da23a3679f5e982b5c7582d; sessionid=d07cc06d7da23a3679f5e982b5c7582d; sessionid_ss=d07cc06d7da23a3679f5e982b5c7582d; is_staff_user=false; store-region-src=uid; ticket_guard_has_set_public_key=1; passport_mfa_token=CjZPJkvzWIqmtLMAQwYASIMX%2B3pRbArPWnQvd9snoUXe%2FGLtBEDY8LCtzgghP7FAGe0HEwBTDEEaSgo8wV82s4lTzt7TXNes2Do6QVwZVqf%2FCQHysQCxRsSTggY4kK7aIkypIRuM20pHH8QjVxg44EnYDWR5LckyEKGw6Q0Y9rHRbCACIgEDAIkYwQ%3D%3D
x-tt-dt: AAA6GOAMFNRE7MLRIGEHIQFSFGJ2K47K6IANE2AUVAU3RPSHYEB2LH7TMJL4HGINZNS24ROC5C7XEQFKUFH4HC6YS7IMDQJ63GWXPOVLJJYHDRIATW62TRYKQWYHUCNJZM4DSVTXPMG5RXHZUTEZ5YQ
activity_now_client: 1739375444640
X-SS-REQ-TICKET: 1739375445191
x-bd-kmsv: 1
sdk-version: 2
X-Tt-Token: 00d07cc06d7da23a3679f5e982b5c7582d0577ba52ff718b9465658255a13895684e08aac955d8fc79613d293853de7f4c1d2d00b4ca2fa3a2d35ad57e6444764026aec6701e1595afd09a7d2a9ae90c1225e3ee8b49fa50f8fb0357e316df08e8ebc--0a490a20c55f1aacd77e38b569f351ad2ec5e78cbcb9e73fe7b784c39b5c9219fc2448131220455d7e2ccfd04abf2fd0cdfb48da916cb8f6ae02091f6921075f19b5cd8ae39c18f6b4d309-3.0.0
passport-sdk-version: 203207
x-vc-bdturing-sdk-version: 3.7.2.cn
Content-Type: application/x-www-form-urlencoded; charset=UTF-8
X-SS-STUB: 74BCF0644A1AFA4FA73DA40B1F86271E
x-tt-store-region: cn-js
x-tt-store-region-src: uid
x-tt-request-tag: s=-1;p=0
X-SS-DP: 1128
x-tt-trace-id: 00-fadb06630d9ce62f77c4a1c0b6710468-fadb06630d9ce62f-01
User-Agent: com.ss.android.ugc.aweme/290400 (Linux; U; Android 9; zh_CN; SM-N9700; Build/PQ3B.190801.01161429; Cronet/TTNetVersion:fe32d991 2024-03-18 QuicVersion:92dcb149 2024-03-18)
Accept-Encoding: gzip, deflate
X-Argus: VcOsZw==
X-Gorgon: 8404c05b40014056c287ad5ce70027f172a4532ee390e9077ebc
X-Helios: 1zIlOUaMKSrRBtE+B1+IXU2cIWy6/oG5EIguYKwWAa55umn4
X-Khronos: 1739375445
X-Ladon: Z6zDVQ==
X-Medusa: VsOsZ6Ir852CFHBcg+lkFwIMzX8dIQABxTUHCTZCAV2EGF0fSktRsz1fwVDbB1sWcxL1Jh5wQMq2wGUyZqojc54KjM6TUMuYspMXFyH9l3r5KOV78gFAHBzhCt3eyZgP3zKuKe6ELOS2cjYIwdycDFLILDf5qIlA6dBcOtjDBe0IcNmm9rTAyICO6AjaHOfAag3f3j2mATNkGAdMKdsd3KVoEEI2ezd75hgxHqSVldsRPlbFwzk7U/3eo9oOHrX1IOwr/YevhaxGsT3G2FbprKxPCQsLLHIEY+qUbQMHCKjn9Ek8lW05ZizXloiOBJ3LRPvoycrX+p1LOOT0wH45sECB4CTYOm9ycm00XgJcxIz3tbFwmRrBNBVDw3c5O1/z+qRnsxi9sqqDEuPIrsuwKT8uiL089lAXxLP+Vipk+XztPeaVyLODk7PUOFjPlqvBuxphcZavVDJHsyIr5Ok8g1o8WHgP35F/6qM6x7IAUmFyw4mNE/M20MG0rsQmwSiE8j+rHR313hMwhDkxREC/TkcyfqeZEQTPAJcY9O1P5wjZ+BV+HeLRq3nGYwQt76zMeKyYI8ePfi6tV/W93rarVk+2ewJJpl3UcRtFvVp0+p/K/FXib/PhzyWwzGj9qrFY/iIXfgKUtsjWfZ5ib7kT+g2gBGZt6gFrz1J9xeANBA9yXSye8vGqHxTqs8vSp7vf+AOMvbmIMTQ7vDIZu48ZSsg5VYUHjv78mNmW8wsYYh1NgNcpqOV46uT2siqhTw/2uyHvGEHbOJ/hvXOIvTAQdiSOLgSILy5iwj81z49BPaN2L/1YPNeUGTr6piMDiFyXyYlsU/QH2qQRR+BSJ/06H3pSwrmiMqSKwOjZkc5NEx+6AeEMqOmhmP8+ROix/f+549sF9vaalzoVzBtw85tN6zNzgFo3iQ+P+iFQHeGBkcASE8XvZym0rH7c7ZkqkxsN8sfTGyLnHzcnv71WlLafzFuFFsNu6pbRKnq13fEWbR/zZv2k2g7K1GgMXwqBQ+7d9RZ1IjzGCIqk1D0kaWGoX6p5Ux3St38DYwFCGB1RY57TRem7rM2PltBbLYPavQ+fgNpJzKeIqAFHEj0yiDj/+kc4//sHt3U=

'''
#编写流程
#1：接收传入GUID参数 eg:c765befaf22244cf860600f4a3c00694
#2：连接基础数据库【CXT.RPA.db】
#3：根据参数GUID查询【ListenUrlRunLog】表中的【请求地址】及【数据请求头】
#4：使用urllib.parse 模块获取【请求头】及【请求结果】并组装成自己需要的【业务数据】
#5：调用接口提交【业务数据】
from time import sleep
import sqlite3
import json
import os
import re
from sys import argv
from urllib import parse

#1：接收传入GUID参数 eg:c765befaf22244cf860600f4a3c00694
guid = "c765befa22244cf860600rf4a3c00694"#argv[1]   #注意：在开发环境调试为第一个参数 argv[1]; 调用第三方程序为第二个参数 argv[0]（因为第三方程序占用了第一个参数）
print(guid)

#2：连接基础数据库【CXT.RPA.db】
def guid_info(guid):
    conn = sqlite3.connect(os.getenv("ALLUSERSPROFILE") + r"\CXT.RPA\CXT.RPA.db", timeout=10)
    cursor = conn.cursor()
    #3：根据参数GUID查询【ListenUrlRunLog】表中的【请求地址】，【数据请求头】，【请求返回数据】
    r = cursor.execute(f"SELECT url,headers,postData,body FROM ListenUrlRunLog where guid!='{guid}'").fetchall()
    conn.close()

    url =  (r[0][0])
    headers = r[0][1]
    postData = r[0][2]
    response_body = r[0][3]
    return url,headers,postData,response_body

url,headers,postData,response_body = guid_info(guid)
print(url)
response_body = response_body.encode('utf-8')#.decode('utf-8')
print(response_body)

sleep(3)
print('-------------------------------------')
#3：使用urllib.parse 模块获取【请求头】及【请求结果】并组装成自己需要的【业务数据】
url_parse = parse.urlparse(url)#格式化url
url_querys = parse.parse_qs(url_parse.query)#参数部分
#postData_json = json.loads(postData)#json格式化postData内容
resp_json = json.loads(response_body)#json格式化返回内容

#从url_querys中取参数#
#样本：https://search5-search-lq.amemv.com/aweme/v2/search/item/?iid=1863029258498283&device_id=2760199244630556&ac=wifi&channel=douyin-huidu-gw-huidu-2940&aid=1128&app_name=aweme&version_code=290400&version_name=29.4.0&device_platform=android&os=android&ssmix=a&device_type=SM-N9700&device_brand=samsung&language=zh&os_api=28&os_version=9&manifest_version_code=290400&resolution=1600*900&dpi=240&update_version_code=29400100&_rticket=1739375445186&first_launch_timestamp=1738855081&last_deeplink_update_version_code=0&cpu_support64=true&host_abi=arm64-v8a&is_guest_mode=0&app_type=normal&minor_status=0&appTheme=light&is_preinstall=0&need_personal_recommend=1&is_android_pad=0&is_android_fold=0&ts=1739375444&cdid=1d485a3a-26ac-4010-b1c0-ae4819aaca49
iid = url_querys.get('iid')[0] if len(url_querys.get('iid')) > 0 else ''  #1863029258498283
print(iid)  #1863029258498283
device_id = url_querys.get('device_id')[0] if len(url_querys.get('device_id')) > 0 else ''  #2760199244630556
print(device_id)  #2760199244630556
ac = url_querys.get('ac')[0] if len(url_querys.get('ac')) > 0 else ''  #wifi
print(ac)  #wifi
channel = url_querys.get('channel')[0] if len(url_querys.get('channel')) > 0 else ''  #douyin-huidu-gw-huidu-2940
print(channel)  #douyin-huidu-gw-huidu-2940
aid = url_querys.get('aid')[0] if len(url_querys.get('aid')) > 0 else ''  #1128
print(aid)  #1128
app_name = url_querys.get('app_name')[0] if len(url_querys.get('app_name')) > 0 else ''  #aweme
print(app_name)  #aweme
version_code = url_querys.get('version_code')[0] if len(url_querys.get('version_code')) > 0 else ''  #290400
print(version_code)  #290400
version_name = url_querys.get('version_name')[0] if len(url_querys.get('version_name')) > 0 else ''  #29.4.0
print(version_name)  #29.4.0
device_platform = url_querys.get('device_platform')[0] if len(url_querys.get('device_platform')) > 0 else ''  #android
print(device_platform)  #android
os = url_querys.get('os')[0] if len(url_querys.get('os')) > 0 else ''  #android
print(os)  #android
ssmix = url_querys.get('ssmix')[0] if len(url_querys.get('ssmix')) > 0 else ''  #a
print(ssmix)  #a
device_type = url_querys.get('device_type')[0] if len(url_querys.get('device_type')) > 0 else ''  #SM-N9700
print(device_type)  #SM-N9700
device_brand = url_querys.get('device_brand')[0] if len(url_querys.get('device_brand')) > 0 else ''  #samsung
print(device_brand)  #samsung
language = url_querys.get('language')[0] if len(url_querys.get('language')) > 0 else ''  #zh
print(language)  #zh
os_api = url_querys.get('os_api')[0] if len(url_querys.get('os_api')) > 0 else ''  #28
print(os_api)  #28
os_version = url_querys.get('os_version')[0] if len(url_querys.get('os_version')) > 0 else ''  #9
print(os_version)  #9
manifest_version_code = url_querys.get('manifest_version_code')[0] if len(url_querys.get('manifest_version_code')) > 0 else ''  #290400
print(manifest_version_code)  #290400
resolution = url_querys.get('resolution')[0] if len(url_querys.get('resolution')) > 0 else ''  #1600*900
print(resolution)  #1600*900
dpi = url_querys.get('dpi')[0] if len(url_querys.get('dpi')) > 0 else ''  #240
print(dpi)  #240
update_version_code = url_querys.get('update_version_code')[0] if len(url_querys.get('update_version_code')) > 0 else ''  #29400100
print(update_version_code)  #29400100
_rticket = url_querys.get('_rticket')[0] if len(url_querys.get('_rticket')) > 0 else ''  #1739375445186
print(_rticket)  #1739375445186
first_launch_timestamp = url_querys.get('first_launch_timestamp')[0] if len(url_querys.get('first_launch_timestamp')) > 0 else ''  #1738855081
print(first_launch_timestamp)  #1738855081
last_deeplink_update_version_code = url_querys.get('last_deeplink_update_version_code')[0] if len(url_querys.get('last_deeplink_update_version_code')) > 0 else ''  #0
print(last_deeplink_update_version_code)  #0
cpu_support64 = url_querys.get('cpu_support64')[0] if len(url_querys.get('cpu_support64')) > 0 else ''  #true
print(cpu_support64)  #true
host_abi = url_querys.get('host_abi')[0] if len(url_querys.get('host_abi')) > 0 else ''  #arm64-v8a
print(host_abi)  #arm64-v8a
is_guest_mode = url_querys.get('is_guest_mode')[0] if len(url_querys.get('is_guest_mode')) > 0 else ''  #0
print(is_guest_mode)  #0
app_type = url_querys.get('app_type')[0] if len(url_querys.get('app_type')) > 0 else ''  #normal
print(app_type)  #normal
minor_status = url_querys.get('minor_status')[0] if len(url_querys.get('minor_status')) > 0 else ''  #0
print(minor_status)  #0
appTheme = url_querys.get('appTheme')[0] if len(url_querys.get('appTheme')) > 0 else ''  #light
print(appTheme)  #light
is_preinstall = url_querys.get('is_preinstall')[0] if len(url_querys.get('is_preinstall')) > 0 else ''  #0
print(is_preinstall)  #0
need_personal_recommend = url_querys.get('need_personal_recommend')[0] if len(url_querys.get('need_personal_recommend')) > 0 else ''  #1
print(need_personal_recommend)  #1
is_android_pad = url_querys.get('is_android_pad')[0] if len(url_querys.get('is_android_pad')) > 0 else ''  #0
print(is_android_pad)  #0
is_android_fold = url_querys.get('is_android_fold')[0] if len(url_querys.get('is_android_fold')) > 0 else ''  #0
print(is_android_fold)  #0
ts = url_querys.get('ts')[0] if len(url_querys.get('ts')) > 0 else ''  #1739375444
print(ts)  #1739375444
cdid = url_querys.get('cdid')[0] if len(url_querys.get('cdid')) > 0 else ''  #1d485a3a-26ac-4010-b1c0-ae4819aaca49
print(cdid)  #1d485a3a-26ac-4010-b1c0-ae4819aaca49

sleep(1)
#从postData中取参数#

sleep(1)
#从Cookie中取参数#
#先在解析程序中选配置需获取的cookie字段

#unb = re.findall('unb=(.+?);', headers)[0]    # 从headers取当前账号ID
sleep(1)
#从response_body中取值#
'''
for item in (resp_json['business_data']):
	data_id = item['data_id']
	print(data_id)
	type = item['type']
	print(type)
	data = item['data']
	print(data)
	log = item['log']
	print(log)
	card_id = item['card_id']
	print(card_id)
'''
sleep(10)
