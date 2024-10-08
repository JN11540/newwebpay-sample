# app/routes/index.py
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Dict
import os
import time
import hashlib
import hmac
from Crypto.Cipher import AES
import base64
from Crypto.Util.Padding import pad
import psycopg2
from urllib.parse import parse_qs
import json

# 加載環境變量
from dotenv import load_dotenv
load_dotenv()

# 取得環境變數
MerchantID = os.getenv("MerchantID")        # 商店 ID
HASHKEY = os.getenv("HASHKEY")              # hashkey
HASHIV = os.getenv("HASHIV")                # hashIV
Version = os.getenv("Version")              # 藍新金流平台 API 版本號
PayGateWay = os.getenv("PayGateWay")        # 蘭新金流平台支付系統的網址
NotifyUrl = os.getenv("NotifyUrl")          # 支付完成後伺服器接收通知的 URL
ReturnUrl = os.getenv("ReturnUrl")          # 支付完成後用戶重定向的 URL
DATABASE_URL = os.getenv('DATABASE_URL')    # 連接 Railway PostgreSQL 資料庫的網址





index_bp = APIRouter()
# Jinja2模板設置
templates = Jinja2Templates(directory="app/templates")







# ------------------------- [設定] -> [購買軟體產品] 首頁 -------------------------
@index_bp.get("/")
async def get_index(request: Request):
    softwareproductnamelist = []
    descriptionlist = []
    pricelist = []
    try:
        # Connect to the database
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        # Execute query to retrieve data
        cursor.execute("SELECT softwareproductname, description, price FROM softwareproduct;")
        results = cursor.fetchall()
        # Extract data into separate lists
        for row in results:
            softwareproductnamelist.append(row[0])
            descriptionlist.append(row[1])
            pricelist.append(row[2])
    except Exception as e:
        print("An error occurred:", e)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    # Pass the data to the template
    return templates.TemplateResponse("index.html", {
        "request": request,
        "softwareproductnamelist": softwareproductnamelist,
        "descriptionlist": descriptionlist,
        "pricelist": pricelist
    })










# 在 [設定] -> [購買軟體產品] 首頁，讓使用者點選軟體產品訂單的 API
orders: Dict[int, dict] = {}
class OrderForm(BaseModel):
    Email: str
    Amt: int
    ItemDesc: str
@index_bp.post("/createOrder")
async def create_order(request: Request):
    req = await request.json()
    ItemDesc = req.get("softwareproductname")
    Amt = req.get("price")
    try:
        # Connect to the database
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        # Find the email of the active member
        cursor.execute("SELECT email FROM member WHERE isactive = true;")
        member_email = cursor.fetchone()
        if not member_email:
            raise HTTPException(status_code=404, detail="No active member found")
        # Extract the email
        Email = member_email[0]
    except Exception as e:
        print("An error occurred:", e)
        raise HTTPException(status_code=500, detail="Failed to create order")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        
    TimeStamp = int(time.time())
    order = {
        "Email": Email,
        "Amt": Amt,
        "ItemDesc": ItemDesc,
        "TimeStamp": TimeStamp,
        "MerchantOrderNo": TimeStamp
    }
    # 加密訂單資料
    aes_encrypt = create_aes_encrypt(order)
    sha_encrypt = create_sha_encrypt(aes_encrypt)
    order["aesEncrypt"] = aes_encrypt
    order["shaEncrypt"] = sha_encrypt
    orders[TimeStamp] = order
    # 使用GET方法进行重定向
    return RedirectResponse(url=f"/check/{TimeStamp}", status_code=303)
# AES加密方法
def create_aes_encrypt(TradeInfo):
    # 将 TradeInfo 转换成字符串 (如：MerchantID=123456&Amt=100&MerchantOrderNo=123456...)
    data_chain = gen_data_chain(TradeInfo)
    # 填充数据到 16 字节的倍数
    block_size = AES.block_size
    padded_data = pad(data_chain.encode('utf-8'), block_size)
    # AES 加密 - 手动将 HASHKEY 和 HASHIV 转换为字节类型
    cipher = AES.new(HASHKEY.encode('utf-8'), AES.MODE_CBC, HASHIV.encode('utf-8'))
    enc = cipher.encrypt(padded_data)
    return base64.b16encode(enc).decode('utf-8')
# SHA256加密方法
def create_sha_encrypt(aes_encrypt):
    sha = hashlib.sha256()
    plain_text = f"HashKey={HASHKEY}&{aes_encrypt}&HashIV={HASHIV}"
    sha.update(plain_text.encode('utf-8'))
    return sha.hexdigest().upper()
def gen_data_chain(order):
    return f"MerchantID={MerchantID}&TimeStamp={order['TimeStamp']}&Version={Version}&RespondType=JSON&MerchantOrderNo={order['MerchantOrderNo']}&Amt={order['Amt']}&NotifyURL={NotifyUrl}&ReturnURL={ReturnUrl}&ItemDesc={order['ItemDesc']}&Email={order['Email']}"






# ------------------------- [設定] -> [購買軟體產品] 次頁 (顯示使用者訂單確認頁面) -------------------------

# 顯示使用者訂單資訊的 API
@index_bp.get("/check/{id}")
async def check_order(request: Request, id: int):
    order = orders.get(id)
    if not order:
        return templates.TemplateResponse("error.html", {"request": request, "message": "Order not found", "status": 404})
    return templates.TemplateResponse("check.html", {
        "request": request,
        "title": "FastAPI",
        "PayGateWay": PayGateWay,
        "Version": Version,
        "order": order,
        "MerchantID": MerchantID,
        "NotifyUrl": NotifyUrl,
        "ReturnUrl": ReturnUrl
    })






# ------------------------- [設定] -> [購買軟體產品] 第三頁 -------------------------
# check.html 會跳轉至蘭新金流平台支付系統的網址 https://ccore.newebpay.com/MPG/mpg_gateway










# ------------------------- [設定] -> [購買軟體產品] 第四頁 (顯示結帳完成的頁面) -------------------------

# 使用者在蘭新金流平台支付系統的網址 https://ccore.newebpay.com/MPG/mpg_gateway 購買完成後
# 蘭新金流平台支付系統會發布以下 API
# 通知使用者
@index_bp.post("/newebpay_return")
async def newebpay_return(request: Request):
    body = await request.body()  # 獲取原始的字節數據
    body_str = body.decode('utf-8')  # 將字節數據解碼為字符串
    # 解析URL編碼的字符串為字典
    parsed_data = parse_qs(body_str)
    print('return data: ', parsed_data)
    status_info = parsed_data.get('Status', [''])[0]
    # 傳遞 status_info 給前端模板
    return templates.TemplateResponse("success.html", {"request": request, "status_info": status_info})
    








# 使用者在蘭新金流平台支付系統的網址 https://ccore.newebpay.com/MPG/mpg_gateway 購買完成後
# 蘭新金流平台支付系統會發布以下 API
# 通知這支伺服器程式
@index_bp.post("/newebpay_notify")
async def newebpay_notify(request: Request):
    global orders
    body = await request.body()  # 獲取原始的字節數據
    body_str = body.decode('utf-8')  # 將字節數據解碼為字符串
    # 解析URL編碼的字符串為字典
    parsed_data = parse_qs(body_str)
    print('notify data: ', parsed_data)
    # 提取TradeInfo的值
    trade_info = parsed_data.get('TradeInfo', [''])[0]
    trade_sha = parsed_data.get('TradeSha', [''])[0]
    # 解密交易內容
    data = create_aes_decrypt(trade_info)
    # 将data从JSON字符串解析为Python字典
    data_dict = json.loads(data)
    print('data: ', data_dict)
    # 提取MerchantOrderNo的值
    merchant_order_no = data_dict.get("Result", {}).get("MerchantOrderNo", "")
    # 提取 orders 中的 MerchantOrderNo
    for order_no, order_data in orders.items():
        extracted_merchant_order_no = order_data.get('MerchantOrderNo', '')
    # 取得交易內容，並查詢本地端資料庫是否有相符的訂單
    if str(merchant_order_no) != str(extracted_merchant_order_no):
        print('找不到訂單')
        return {}
    # 使用 HASH 再次 SHA 加密字串，確保比對一致（確保不正確的請求觸發交易成功）
    this_sha_encrypt = create_sha_encrypt(trade_info)
    if this_sha_encrypt != trade_sha:
        print('付款失敗：TradeSha 不一致')
        return {}
    print('訂單：', orders)
    orders = {}
    return {}
# 解密方法
def create_aes_decrypt(TradeInfo):
    cipher = AES.new(HASHKEY.encode('utf-8'), AES.MODE_CBC, HASHIV.encode('utf-8'))
    decrypt_text = cipher.decrypt(base64.b16decode(TradeInfo.upper()))
    # 去除填充
    unpad = lambda s: s[:-ord(s[-1:])]
    result = unpad(decrypt_text).decode('utf-8')
    return result

