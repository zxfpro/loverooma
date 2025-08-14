from fastapi import FastAPI, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from loverooma.core import EmbeddingPool,Desensitization
from loverooma.log import Log
import importlib.resources
import yaml


logger = Log.logger

app = FastAPI(
    title="Embedding Service API",
    description="一个用于管理和查询文本嵌入的简单API服务。",
    version="1.0.0",
    docs_url="/docs",  # OpenAPI (Swagger UI) 文档
    redoc_url="/redoc" # ReDoc 文档
)

origins = [
    # "http://localhost:3000",  # 允许前端域名
    # "http://127.0.0.1:3000",
    "*" # 暂时允许所有来源，生产环境应限制
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有请求头
)

ep = EmbeddingPool()

de = Desensitization()
# @app.get("/reload")
# async def reload():
#     ep.reload()
#     return 'success'

def load_config():
    """ load config """
    with importlib.resources.open_text('loverooma', 'config.yaml') as f:
        return yaml.safe_load(f)

@app.get(
    "/reload",
    summary="重新加载Embedding池数据",
    description="清空并重新初始化Embedding池。注意：这可能会导致短暂的服务中断或数据丢失。",
    response_description="表示操作是否成功。"
)
async def reload_endpoint(Desensitization_prompt: str = Header(None), Evaluation_prompt: str = Header(None)):
    """
    重新加载Embedding池，通常用于清除缓存或重新从源加载数据。
    """
    logger.info(Desensitization_prompt)
    logger.info(Evaluation_prompt)
    try:
        if Desensitization_prompt or Evaluation_prompt:
            config = load_config()
            if Desensitization_prompt:
                config['Desensitization_prompt'] = Desensitization_prompt
            if Evaluation_prompt:
                config['Evaluation_prompt'] = Evaluation_prompt
            with importlib.resources.path('loverooma', 'config.yaml') as config_path:
                with open(config_path, 'w') as f:
                    yaml.safe_dump(config, f)
        ep.reload()
        return {"status": "success", "message": "Embedding pool reloaded successfully."}
    except Exception as e:
        logger.error(f"Error reloading EmbeddingPool: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload embedding pool: {e}"
        )


class UpdateItem(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="要更新的文本内容。")
    id: str = Field(..., min_length=1, max_length=100, description="与文本关联的唯一ID。")


@app.post(
    "/update", # 推荐使用POST请求进行数据更新
    summary="更新或添加文本嵌入",
    description="将给定的文本内容与一个ID关联并更新到Embedding池中。",
    response_description="表示操作是否成功。"
)
def update_endpoint(item: UpdateItem):
    """
    接收文本和ID，并将其添加到Embedding池中。
    - **text**: 要嵌入的文本。
    - **id**: 关联的唯一标识符。
    """
    try:
        ep.update(text=item.text, id=item.id)
        return {"status": "success", "message": f"ID '{item.id}' updated successfully."}
    except ValueError as e: # 假设EmbeddingPool.update可能抛出ValueError
        logger.warning(f"Validation error during update: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating EmbeddingPool for ID '{item.id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update embedding for ID '{item.id}': {e}"
        )


class QueryItem(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="用于搜索的查询文本。")


@app.post(
    "/search",
    summary="搜索文本嵌入",
    description="根据查询文本在Embedding池中搜索相关内容。",
    response_description="搜索结果列表。"
)
def search_endpoint(query_item: QueryItem): # 使用Pydantic模型进行查询参数验证
    """
    根据查询字符串搜索Embedding池中的文本。
    - **query**: 搜索的关键词。
    """
    try:
        result = ep.search(query=query_item.query)
        return {"status": "success", "results": result, "query": query_item.query}
    except Exception as e:
        logger.error(f"Error searching EmbeddingPool for query '{query_item.query}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform search: {e}"
        )


# @app.get('/desensitization')
# def desensitization(text:str):

#     result = de.desensitization(text = text)
#     if result == 'error':
#         return "error"
#     else:
#         return result

class DesensitizationItem(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="需要进行脱敏处理的文本。") # 文本可能较长，增加 max_length


@app.post( # 推荐使用POST进行数据发送，特别是文本内容可能较长
    "/desensitization",
    summary="对文本进行脱敏处理",
    description="接收一段文本，对其进行敏感信息（如手机号、身份证号等）的脱敏处理。",
    response_description="脱敏后的文本或错误信息。"
)
def desensitization_endpoint(item: DesensitizationItem): # 使用Pydantic模型进行输入验证
    """
    对输入的文本进行脱敏操作。
    - **text**: 需要脱敏的原始文本。
    """
    try:
        logger.info(f"Received text for desensitization: '{item.text[:100]}...'")
        result = de.desensitization(text=item.text)

        if result == 'error': # 假设 'error' 是业务逻辑上的失败标识
            logger.warning(f"Desensitization failed for text: '{item.text[:100]}...'. Returned 'error'.")
            # 业务逻辑错误，返回 422 Unprocessable Entity 或 400 Bad Request
            # 如果是文本内容本身导致无法脱敏，可以是 400
            # 如果是内部处理问题，但不是 HTTP 5xx 级别，可以是 422
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, # 或者 400 Bad Request
                detail="Desensitization process failed."
            )
        else:
            logger.info(f"Text successfully desensitized. Original length: {len(item.text)}, Desensitized length: {len(result)}")
            return {"status": "success", "desensitized_text": result}
    except ValueError as e: # 假设 de.desensitization 可能抛出 ValueError
        logger.warning(f"Validation error during desensitization: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e: # 捕获其他未预料的异常
        logger.error(f"An unexpected error occurred during desensitization: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal server error occurred during desensitization: {e}"
        )


@app.post( # 推荐使用POST进行数据发送，特别是文本内容可能较长
    "/update_with_desensitization",
    summary="对文本进行脱敏处理并上传",
    description="接收一段文本，对其进行敏感信息（如手机号、身份证号等）的脱敏处理后，将脱敏后的文本与ID关联并更新到Embedding池中。",
    response_description="表示操作是否成功。"
)
def update_with_desensitization(item: UpdateItem): # 使用Pydantic模型进行输入验证
    """
    对输入的文本进行脱敏操作。
    - **text**: 需要脱敏的原始文本。
    """
    
    try:
        logger.info(f"Received text for desensitization and update: '{item.text[:100]}...' with ID: '{item.id}'")
        desensitized_text = de.desensitization(text=item.text)
        #TODO 处理 desensitized_text 返回"脱敏失败" 关键字时, 对应的处理, 

        if desensitized_text == 'error' or desensitized_text == "脱敏失败":
            logger.warning(f"Desensitization failed for text: '{item.text[:100]}...'. Returned 'error' or '脱敏失败'. Skipping update.")
            return {"status": "skipped", "message": f"Desensitization failed for ID '{item.id}', skipping update."}
        
        ep.update(text=desensitized_text, id=item.id)
        logger.info(f"ID '{item.id}' updated successfully with desensitized text.")
        return {"status": "success", "message": f"ID '{item.id}' updated successfully with desensitized text."}
    except ValueError as e:
        logger.warning(f"Validation error during update with desensitization for ID '{item.id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred during update with desensitization for ID '{item.id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update embedding for ID '{item.id}' after desensitization: {e}"
        )

if __name__ == "__main__":
    # 这是一个标准的 Python 入口点惯用法
    # 当脚本直接运行时 (__name__ == "__main__")，这里的代码会被执行
    # 当通过 python -m YourPackageName 执行 __main__.py 时，__name__ 也是 "__main__"
    import argparse
    import uvicorn
    from .log import Log
    parser = argparse.ArgumentParser(
        description="Start a simple HTTP server similar to http.server."
    )
    parser.add_argument(
        'port',
        metavar='PORT',
        type=int,
        nargs='?', # 端口是可选的
        default=8009,
        help='Specify alternate port [default: 8000]'
    )

    parser.add_argument(
        '--env',
        type=str,
        default='dev', # 默认是开发环境
        choices=['dev', 'prod'],
        help='Set the environment (dev or prod) [default: dev]'
    )

    args = parser.parse_args()

    port = args.port
    print(args.env)
    if args.env == "dev":
        port += 100
        Log.reset_level('debug',env = args.env)
        reload = False
    elif args.env == "prod":
        Log.reset_level('info',env = args.env)# ['debug', 'info', 'warning', 'error', 'critical']
        reload = False
    else:
        reload = False

    # 使用 uvicorn.run() 来启动服务器
    # 参数对应于命令行选项
    uvicorn.run(
        app, # 要加载的应用，格式是 "module_name:variable_name"
        host="0.0.0.0",
        port=port,
        reload=reload  # 启用热重载
    )