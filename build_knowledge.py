"""
知识库构建脚本：读取 data/ 下 PDF，用 LlamaIndex 加载切片，
使用 HuggingFace 中文嵌入模型构建向量索引并持久化到 ./storage。
"""
from pathlib import Path

from dotenv import load_dotenv
from llama_index.core import (
    SimpleDirectoryReader,
    VectorStoreIndex,
    Settings,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# 1. 加载 .env（可选，供其他配置使用）
load_dotenv()

# 2. 使用 HuggingFace 中文嵌入模型
embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-zh-v1.5")
Settings.embed_model = embed_model

# 3. 配置文本切片（chunk）
Settings.chunk_size = 512
Settings.chunk_overlap = 50
node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)

# 4. 读取 data/ 目录下的 PDF 文件
data_dir = Path(__file__).parent / "data"
if not data_dir.exists():
    raise FileNotFoundError(f"数据目录不存在: {data_dir}")

reader = SimpleDirectoryReader(input_dir=str(data_dir), required_exts=[".pdf"])
documents = reader.load_data()

if not documents:
    raise ValueError(f"在 {data_dir} 下未找到 PDF 文件")

# 5. 将文档切成节点
nodes = node_parser.get_nodes_from_documents(documents)

# 6. 构建向量索引 (VectorStoreIndex)
index = VectorStoreIndex(nodes, embed_model=embed_model)

# 7. 将索引持久化保存到 ./storage
storage_dir = Path(__file__).parent / "storage"
storage_dir.mkdir(parents=True, exist_ok=True)

index.set_index_id("vector_index")
index.storage_context.persist(persist_dir=str(storage_dir))

print("知识库构建完成")
