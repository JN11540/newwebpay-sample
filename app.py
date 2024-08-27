from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os

app = FastAPI()

# 靜態文件配置
app.mount("/static", StaticFiles(directory="public"), name="static")

# 模板配置
templates = Jinja2Templates(directory="views")

# 路由配置
from routes import index, users

app.include_router(index.router)
app.include_router(users.router)

# 404 錯誤處理
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse("error.html", {"request": request, "message": "Not Found", "status": 404})

# 其他錯誤處理
@app.exception_handler(Exception)
async def error_handler(request: Request, exc: Exception):
    return templates.TemplateResponse("error.html", {"request": request, "message": str(exc), "status": 500})