# 使用 Python 3.10 的基础镜像
FROM tiangolo/uvicorn-gunicorn-fastapi:python3.10

# 设置工作目录
WORKDIR /app

# 复制项目依赖文件
COPY requirements.txt .

# 安装项目依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 暴露默认端口 8000
EXPOSE 8000

# 设置环境变量 PORT，默认为 8000
ENV PORT 8000

# 启动命令，指定端口为环境变量中的 PORT 值
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port $PORT"]