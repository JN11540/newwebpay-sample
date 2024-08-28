import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os

# 路由配置
from app.routes import index
from app.routes.error import register_exception_handlers

# 初始化 FastAPI 應用
app = FastAPI()

# 靜態文件配置
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 模板配置
templates = Jinja2Templates(directory="app/templates")

# 後端程式
app.include_router(index.index_bp)
register_exception_handlers(app)

# 啟動應用
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)