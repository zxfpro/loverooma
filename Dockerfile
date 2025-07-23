# 使用官方 Python 3.10 镜像
FROM python:3.10-slim


COPY src/loverooma /etc/loverooma

# 安装项目依赖
 RUN pip install pyyaml qdrant_client llama_index  -i https://pypi.tuna.tsinghua.edu.cn/simple

# 暴露应用运行的端口
EXPOSE 80

# 设置默认命令启动 FastAPI 应用
CMD ["chainforge", "serve", "--host", "0.0.0.0", "--port", "80"]

