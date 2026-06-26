"""
Tiện ích để tải và xử lý dữ liệu cho RAG pipeline.

Cách dùng:
    from utils.data_loader import load_knowledge_base, split_text, build_vectorstore

    text        = load_knowledge_base()
    chunks      = split_text(text, chunk_size=500, chunk_overlap=50)
    vectorstore = build_vectorstore(chunks, embeddings)
"""
from pathlib import Path


def load_knowledge_base(path: str = None) -> str:
    """
    Đọc file knowledge base và trả về nội dung dạng chuỗi.

    Args:
        path: đường dẫn tới file text.
              Mặc định: data/knowledge_base.txt (thư mục gốc của project)

    Returns:
        Nội dung file dưới dạng str
    """
    if path is None:
        path = Path(__file__).parent.parent.parent / "data" / "knowledge_base.txt"
    return Path(path).read_text(encoding="utf-8")


def split_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list:
    """
    Chia văn bản thành các đoạn nhỏ (chunks) để index.

    Dùng RecursiveCharacterTextSplitter — tách ưu tiên theo đoạn văn, câu, rồi ký tự.

    Args:
        text         : văn bản cần chia
        chunk_size   : số ký tự tối đa mỗi chunk (mặc định: 500)
        chunk_overlap: số ký tự chồng lên nhau giữa 2 chunks liên tiếp (mặc định: 50)

    Returns:
        list[str] — danh sách các chuỗi chunk
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return splitter.split_text(text)


def build_vectorstore(chunks: list, embeddings, batch_size: int = 50):
    """
    Tao FAISS vectorstore tu danh sach chunks va embeddings.
    Embeds in batches to respect rate limits (e.g. Gemini free tier: 100 req/min).

    Args:
        chunks     : list[str] -- danh sach text chunks da chia
        embeddings : Embeddings instance (tu get_embeddings())
        batch_size : so chunks moi batch (default 50 de tranh rate limit)

    Returns:
        FAISS vectorstore da duoc index va san sang dung de retrieve
    """
    import time
    from langchain_community.vectorstores import FAISS

    print(f"Building FAISS index from {len(chunks)} chunks (batch_size={batch_size}) ...")

    vectorstore = None
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        print(f"  Embedding batch {i // batch_size + 1}/{(len(chunks) + batch_size - 1) // batch_size} ({len(batch)} chunks)...")

        # Retry with exponential backoff for rate limit errors
        for attempt in range(5):
            try:
                if vectorstore is None:
                    vectorstore = FAISS.from_texts(batch, embeddings)
                else:
                    batch_vs = FAISS.from_texts(batch, embeddings)
                    vectorstore.merge_from(batch_vs)
                break
            except Exception as e:
                if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                    wait = 2 ** attempt * 15  # 15s, 30s, 60s, 120s, 240s
                    print(f"  Rate limit hit, waiting {wait}s before retry (attempt {attempt+1}/5)...")
                    time.sleep(wait)
                else:
                    raise

        # Sleep between batches to stay within rate limits
        if i + batch_size < len(chunks):
            time.sleep(2)

    print("FAISS vectorstore ready.")
    return vectorstore

