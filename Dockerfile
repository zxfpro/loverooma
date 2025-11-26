# 使用官方 Python 3.10 镜像
FROM python:3.12-slim

# 安装项目依赖
RUN pip install --no-cache-dir pyyaml qdrant_client llama_index==0.14.7 -i https://pypi.tuna.tsinghua.edu.cn/simple
# RUN pip install --no-cache-dir loverooma==0.1.11 -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装 .whl 文件 安装是屏蔽
COPY ./dist/loverooma-0.1.11-py3-none-any.whl . 
COPY utils.py /usr/local/lib/python3.12/site-packages/llama_index/core/vector_stores/utils.py

RUN pip install --no-cache-dir loverooma-0.1.11-py3-none-any.whl


# RUN sed -i 's/DEBUG = True/DEBUG = False/g' /app/config.py
# metadata["_node_content"] = json.dumps(node_dict)
# metadata["_node_content"] = json.dumps(node_dict,ensure_ascii = False)#TODO
# RUN sed -i 's/metadata["_node_content"] = json.dumps(node_dict)/metadata["_node_content"] = json.dumps(node_dict,ensure_ascii = False)#TODO/g' /usr/local/lib/python3.12/site-packages/llama_index/core/vector_stores/utils.py
# 暴露应用运行的端口
EXPOSE 80

# 设置默认命令启动 FastAPI 应用
CMD ["python", "-m", "loverooma.server","80","--env","prod"]

