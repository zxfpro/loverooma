

# 推荐算法用途
直接用id 代替用户 text 作为用户的概述和标签
基于这个用户的标签描述拖投影和搜索

# 爱心小屋用途
pass

# 修改llama_index

core/vector_stores/utils.py: 66
metadata["_node_content"] = json.dumps(node_dict,ensure_ascii = False)#TODO
切记