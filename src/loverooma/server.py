# server
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import argparse
import uvicorn

from fastapi import FastAPI, HTTPException, Header, status
from pydantic import BaseModel, Field
from loverooma.core import EmbeddingPool,Desensitization
from loverooma import logger
default = 8009

app = FastAPI(
    title="LLM Service",
    description="Provides an OpenAI-compatible API for custom large language models.",
    version="1.0.1",
    # debug=True, 
    # docs_url="/api-docs",
)

# --- Configure CORS ---
origins = [
    "*", 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Specifies the allowed origins
    allow_credentials=True,  # Allows cookies/authorization headers
    allow_methods=["*"],  # Allows all methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Allows all headers (Content-Type, Authorization, etc.)
)
# --- End CORS Configuration ---


ep = EmbeddingPool()

de = Desensitization()

@app.get("/")
async def root():
    """server run"""
    return {"message": "LLM Service is running."}



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
        status_de,desensitized_text = de.desensitization(text=item.text)
        return {"status": status_de, "message": desensitized_text}

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
        status_de,desensitized_text = de.desensitization(text=item.text)
        #TODO 处理 desensitized_text 返回"脱敏失败" 关键字时, 对应的处理, 
        

        if status_de == "failed":
            return {"status": status_de, "message": desensitized_text}
        ep.update(text=desensitized_text, id=item.id)
        logger.info(f"ID '{item.id}' updated successfully with desensitized text.")
        return {"status": "success", "message": f"ID '{item.id}' updated successfully with {desensitized_text}."}
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
    # 27
    
    parser = argparse.ArgumentParser(
        description="Start a simple HTTP server similar to http.server."
    )
    parser.add_argument(
        "port",
        metavar="PORT",
        type=int,
        nargs="?",  # 端口是可选的
        default=default,
        help=f"Specify alternate port [default: {default}]",
    )
    # 创建一个互斥组用于环境选择
    group = parser.add_mutually_exclusive_group()

    # 添加 --dev 选项
    group.add_argument(
        "--dev",
        action="store_true",  # 当存在 --dev 时，该值为 True
        help="Run in development mode (default).",
    )

    # 添加 --prod 选项
    group.add_argument(
        "--prod",
        action="store_true",  # 当存在 --prod 时，该值为 True
        help="Run in production mode.",
    )
    args = parser.parse_args()

    if args.prod:
        env = "prod"
    else:
        # 如果 --prod 不存在，默认就是 dev
        env = "dev"

    port = args.port

    if env == "dev":
        port += 100
        reload = True
        app_import_string = (
            f"{__package__}.server:app"  # <--- 关键修改：传递导入字符串
        )
    elif env == "prod":
        reload = False
        app_import_string = app
    else:
        reload = False
        app_import_string = app

    # 使用 uvicorn.run() 来启动服务器
    # 参数对应于命令行选项
    uvicorn.run(
        app_import_string, host="0.0.0.0", port=port, reload=reload  # 启用热重载
    )
