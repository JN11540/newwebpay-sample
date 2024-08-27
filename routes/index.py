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

router = APIRouter()

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 取得環境變數
MerchantID = os.getenv("MerchantID")
HASHKEY = os.getenv("HASHKEY")
HASHIV = os.getenv("HASHIV")
Version = os.getenv("Version")
PayGateWay = os.getenv("PayGateWay")
NotifyUrl = os.getenv("NotifyUrl")
ReturnUrl = os.getenv("ReturnUrl")

# Jinja2模板設置
templates = Jinja2Templates(directory="views")

orders: Dict[int, dict] = {}

class OrderForm(BaseModel):
    Email: str
    Amt: int
    ItemDesc: str

# 建立訂單頁面
@router.get("/")
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "FastAPI"})

# 建立訂單 API
@router.post("/createOrder")
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

    return RedirectResponse(url=f"/check/{TimeStamp}")

# 顯示訂單確認頁面
@router.get("/check/{id}")
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

# 交易成功
@router.post("/newebpay_return")
async def newebpay_return(request: Request):
    return templates.TemplateResponse("success.html", {"request": request, "title": "FastAPI"})

# 通知確認交易
@router.post("/newebpay_notify")
async def newebpay_notify(request: Request, TradeInfo: str = Form(...)):
    # 解密交易資訊
    data = create_aes_decrypt(TradeInfo)

    if not data:
        return "Invalid TradeInfo"

    order_no = data.get("Result", {}).get("MerchantOrderNo")
    if not orders.get(order_no):
        return "Order not found"

    this_sha_encrypt = create_sha_encrypt(TradeInfo)
    if this_sha_encrypt != request.form.get("TradeSha"):
        return "Invalid TradeSha"

    # 處理交易成功邏輯
    return "OK"

# 加密方法
def create_aes_encrypt(order):
    data = gen_data_chain(order)
    cipher = AES.new(HASHKEY.encode('utf-8'), AES.MODE_CBC, HASHIV.encode('utf-8'))
    pad = lambda s: s + (32 - len(s) % 32) * chr(32 - len(s) % 32)
    data = pad(data)
    encrypted = cipher.encrypt(data.encode('utf-8'))
    return base64.b16encode(encrypted).decode('utf-8').lower()

def create_sha_encrypt(aes_encrypt):
    plain_text = f"HashKey={HASHKEY}&{aes_encrypt}&HashIV={HASHIV}"
    return hmac.new(HASHKEY.encode('utf-8'), plain_text.encode('utf-8'), hashlib.sha256).hexdigest().upper()

# 解密方法
def create_aes_decrypt(TradeInfo):
    cipher = AES.new(HASHKEY.encode('utf-8'), AES.MODE_CBC, HASHIV.encode('utf-8'))
    decrypt_text = cipher.decrypt(base64.b16decode(TradeInfo.upper()))
    unpad = lambda s: s[:-ord(s[len(s) - 1:])]
    result = unpad(decrypt_text).decode('utf-8')
    return result

def gen_data_chain(order):
    return f"MerchantID={MerchantID}&TimeStamp={order['TimeStamp']}&Version={Version}&RespondType=JSON&MerchantOrderNo={order['MerchantOrderNo']}&Amt={order['Amt']}&NotifyURL={NotifyUrl}&ReturnURL={ReturnUrl}&ItemDesc={order['ItemDesc']}&Email={order['Email']}"

