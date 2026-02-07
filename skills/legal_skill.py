"""
法律检索技能：加载向量索引，提供法律条文搜索工具。
"""
from pathlib import Path

from llama_index.core import (
    StorageContext,
    load_index_from_storage,
)
from llama_index.core.tools import QueryEngineTool
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# 使用与 build_knowledge.py 相同的嵌入模型，加载索引时必须一致
_EMBED_MODEL = HuggingFaceEmbedding(model_name="BAAI/bge-small-zh-v1.5")

# 加载 ./storage 下的向量索引
_STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage"

_storage_context = StorageContext.from_defaults(persist_dir=str(_STORAGE_DIR))
_index = load_index_from_storage(
    _storage_context,
    index_id="vector_index",
    embed_model=_EMBED_MODEL,
)
_query_engine = _index.as_query_engine()

# 定义 QueryEngineTool：search_laws，用于搜索法律条文
search_laws = QueryEngineTool.from_defaults(
    query_engine=_query_engine,
    name="search_laws",
    description="在民法典等法律知识库中检索与用户问题相关的法律条文。输入应为自然语言问题或关键词。",
)
