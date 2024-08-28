# app/routes/index.py
from fastapi import APIRouter, Request, Form
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



# 加載環境變量
from dotenv import load_dotenv
load_dotenv()

# 取得環境變數
MerchantID = os.getenv("MerchantID")    # 商店 ID
HASHKEY = os.getenv("HASHKEY")          # hashkey
HASHIV = os.getenv("HASHIV")            # hashIV
Version = os.getenv("Version")          # 藍新金流平台 API 版本號
PayGateWay = os.getenv("PayGateWay")    # 蘭新金流平台支付系統的網址
NotifyUrl = os.getenv("NotifyUrl")      # 支付完成後伺服器接收通知的 URL
ReturnUrl = os.getenv("ReturnUrl")      # 支付完成後用戶重定向的 URL






index_bp = APIRouter()
# Jinja2模板設置
templates = Jinja2Templates(directory="app/templates")






import psycopg2

DATABASE_URL = os.getenv('DATABASE_URL')

# 連接到資料庫
conn = psycopg2.connect(DATABASE_URL)

# 使用 conn 來執行資料庫操作
cursor = conn.cursor()
cursor.execute("SELECT * FROM member;")
results = cursor.fetchall()

# 關閉連接
cursor.close()
conn.close()









# ------------------------- [設定] -> [購買軟體產品] 首頁 -------------------------
@index_bp.get("/")
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "FastAPI"})






# 在 [設定] -> [購買軟體產品] 首頁，讓使用者輸入訂單資訊的 API
orders: Dict[int, dict] = {}
class OrderForm(BaseModel):
    Email: str
    Amt: int
    ItemDesc: str
@index_bp.post("/createOrder")
async def create_order(request: Request, Email: str = Form(...), Amt: int = Form(...), ItemDesc: str = Form(...)):
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

# 交易成功
@index_bp.post("/newebpay_return")
async def newebpay_return(request: Request):
    return templates.TemplateResponse("success.html", {"request": request, "title": "FastAPI"})











# 使用者在蘭新金流平台支付系統的網址 https://ccore.newebpay.com/MPG/mpg_gateway 購買完成後
# 蘭新金流平台支付系統會發以下 API 通知 index.py 這隻伺服器程式

# 通知確認交易
@index_bp.post("/newebpay_notify")
async def newebpay_notify(request: Request, TradeInfo: str = Form(...)):
    # 解密交易資訊
    data = create_aes_decrypt(TradeInfo)
    if not data:
        return "Invalid TradeInfo"
    # 解析解密后的数据
    data_dict = dict(item.split('=') for item in data.split('&'))
    order_no = data_dict.get("MerchantOrderNo")
    if not orders.get(int(order_no)):
        return "Order not found"
    this_sha_encrypt = create_sha_encrypt(TradeInfo)
    if this_sha_encrypt != request.form.get("TradeSha"):
        return "Invalid TradeSha"
    # 處理交易成功邏輯
    return "OK"
# 解密方法
def create_aes_decrypt(TradeInfo):
    cipher = AES.new(HASHKEY.encode('utf-8'), AES.MODE_CBC, HASHIV.encode('utf-8'))
    decrypt_text = cipher.decrypt(base64.b16decode(TradeInfo.upper()))
    # 去除填充
    unpad = lambda s: s[:-ord(s[-1:])]
    result = unpad(decrypt_text).decode('utf-8')
    return result

