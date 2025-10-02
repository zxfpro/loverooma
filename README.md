

# 推荐算法用途
直接用id 代替用户 text 作为用户的概述和标签
基于这个用户的标签描述拖投影和搜索

# 爱心小屋用途
pass

docker pull qdrant/qdrant
docker run -p 6333:6333 -p 6334:6334 \
    -v $(pwd)/qdrant_storage:/qdrant/storage \
    qdrant/qdrant

验证
curl 访问 http://localhost:6334/collections。如