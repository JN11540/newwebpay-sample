# app/routes/error.py
from fastapi import Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from fastapi import FastAPI

templates = Jinja2Templates(directory="app/templates")

async def not_found_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse("error.html", {"request": request, "message": "Not Found", "status": 404})

async def error_handler(request: Request, exc: Exception):
    return templates.TemplateResponse("error.html", {"request": request, "message": str(exc), "status": 500})

def register_exception_handlers(app: FastAPI):
    app.add_exception_handler(404, not_found_handler)
    app.add_exception_handler(Exception, error_handler)