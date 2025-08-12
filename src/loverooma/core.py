# 链接数据库

import importlib
import yaml
import qdrant_client
from qdrant_client import QdrantClient, models
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import VectorStoreIndex
from llama_index.core import Document
from loverooma.embedding_model import VolcanoEmbedding
from loverooma.log import Log

logger = Log.logger
def load_config():
    """ load config """
    with importlib.resources.open_text('loverooma', 'config.yaml') as f:
        return yaml.safe_load(f)

class EmbeddingPool():
    def __init__(self):
        self.reload()

    def create_collection(self,collection_name:str = "loveroom",vector_dimension:str = 1536):
        distance_metric = models.Distance.COSINE # 使用余弦相似度

        # 2. 定义 Collection 参数
        config = load_config()
        
        client = qdrant_client.QdrantClient(
            host=config.get("host","localhost"),
            port=config.get("port",6333),
        )

        # 3. 创建 Collection (推荐使用 recreate_collection)
        try:
            client.recreate_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(size=vector_dimension, distance=distance_metric),
            )
        except Exception as e:
            raise Exception("创建collection失败") from e
        finally:
            client.close()

    def reload(self):
        logger.info('reload')
        # 默认仓库要被创建的
        config = load_config()
        self.postprocess = SimilarityPostprocessor(similarity_cutoff=config.get("similarity_cutoff",0.5))
        client = qdrant_client.QdrantClient(
            host=config.get("host","localhost"),
            port=config.get("port",6333),
        )
        vector_store = QdrantVectorStore(client=client, collection_name=config.get("collection_name","loveroom"))
        self.embed_model = VolcanoEmbedding(model_name = config.get("model_name","doubao-embedding-text-240715"),
                                            api_key =config.get("api_key",''))
        self.index = VectorStoreIndex.from_vector_store(vector_store,embed_model=self.embed_model)
        self.retriver = self.index.as_retriever(similarity_top_k=config.get("similarity_top_k",2))

        logger.debug("== reload start ==")
        logger.debug(self.postprocess)


    def update(self,text:str,id:str)->str:
        logger.info('update')
        # splitter
        doc=Document(text = text,id_=id)
        self.index.update(document=doc)

    def delete(self,id:str):
        logger.info('delete')
        self.index.delete(doc_id = id)

    def search(self,query:str)->str:
        logger.info('search')
        result = self.retriver.retrieve(query)
        logger.debug(result)
        result_p = self.postprocess.postprocess_nodes(result)
        return '\n\n'.join([i.text for i in result_p])


import os
from openai import OpenAI


class Desensitization():
    def __init__(self):
        self.config = load_config()
        self.client = OpenAI(
            base_url='https://ark.cn-beijing.volces.com/api/v3',
            api_key=self.config.get("api_key",''),
        )
        self.model_name = self.config.get("chat_model_name",'')

    def _prompt_chat(self,prompt:str):
        response = self.client.chat.completions.create(
            model= self.model_name,
            messages=[
                        {
                            "role": "system",
                            "content": [
                                {"type": "text", "text": prompt },
                            ],
                        }
                    ],
        )
        result = response.choices[0].message.content
        return result
    
    def _postprocess(self,eva_result:str):
        if 'true' in eva_result:
            return True
        else:
            return False

    def desensitization(self,text):
        desensitization_prompt = self.config.get("Desensitization_prompt","")
        evaluation_prompt = self.config.get("Evaluation_prompt","")
        for i in range(self.config.get("roll_time",3)):
            logger.info(i)
            des_result = self._prompt_chat(desensitization_prompt.format(text = text))
            print(des_result,'des_result')

            eva_result = self._prompt_chat(evaluation_prompt.format(des_result = des_result))
            print(eva_result,'eva_result')
            if self._postprocess(eva_result):
                return des_result
        return "脱敏失败"

