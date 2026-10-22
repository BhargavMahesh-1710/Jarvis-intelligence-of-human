import math
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from config import KNOWLEDGE_DIR

class DocumentChunk:
    def __init__(self, text: str, source: str, chunk_id: int):
        self.text = text
        self.source = source
        self.chunk_id = chunk_id

    def to_dict(self):
        return {
            "chunk_id": self.chunk_id,
            "source": self.source,
            "text": self.text
        }

class LightweightVectorDB:
    """
    A lightweight, robust Vector DB implementing TF-IDF vectorization
    and Cosine Similarity search, running seamlessly without external dependencies.
    """
    def __init__(self):
        self.chunks: List[DocumentChunk] = []
        self.vocabulary: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.vectors: List[Dict[int, float]] = []

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"\b[a-zA-Z0-9_]{2,}\b", text.lower())

    def fit_and_index(self, chunks: List[DocumentChunk]):
        self.chunks = chunks
        self.vocabulary.clear()
        self.idf.clear()
        self.vectors.clear()

        if not chunks:
            return

        # 1. Build vocabulary & document frequency
        doc_count = len(chunks)
        doc_freq: Dict[str, int] = {}
        tokenized_docs = []

        for chunk in chunks:
            tokens = set(self._tokenize(chunk.text))
            tokenized_docs.append(tokens)
            for token in tokens:
                doc_freq[token] = doc_freq.get(token, 0) + 1

        # Assign indices to tokens
        for idx, token in enumerate(sorted(doc_freq.keys())):
            self.vocabulary[token] = idx
            # Standard IDF with smoothing
            self.idf[token] = math.log((1 + doc_count) / (1 + doc_freq[token])) + 1.0

        # 2. Compute vectors for each chunk
        for chunk in chunks:
            tokens = self._tokenize(chunk.text)
            tf: Dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1

            vec: Dict[int, float] = {}
            norm_sq = 0.0
            for t, count in tf.items():
                if t in self.vocabulary:
                    dim = self.vocabulary[t]
                    val = (count / len(tokens)) * self.idf[t]
                    vec[dim] = val
                    norm_sq += val * val

            norm = math.sqrt(norm_sq) or 1.0
            for dim in vec:
                vec[dim] /= norm
            self.vectors.append(vec)

    def similarity_search(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        if not self.chunks or not self.vocabulary:
            return []

        tokens = self._tokenize(query)
        if not tokens:
            return []

        # Vectorize query
        q_tf: Dict[str, int] = {}
        for t in tokens:
            q_tf[t] = q_tf.get(t, 0) + 1

        q_vec: Dict[int, float] = {}
        norm_sq = 0.0
        for t, count in q_tf.items():
            if t in self.vocabulary:
                dim = self.vocabulary[t]
                val = (count / len(tokens)) * self.idf[t]
                q_vec[dim] = val
                norm_sq += val * val

        if not q_vec:
            return []

        norm = math.sqrt(norm_sq) or 1.0
        for dim in q_vec:
            q_vec[dim] /= norm

        # Compute cosine similarities
        scores = []
        for idx, doc_vec in enumerate(self.vectors):
            dot_product = 0.0
            # iterate through smaller vector
            for dim, q_val in q_vec.items():
                if dim in doc_vec:
                    dot_product += q_val * doc_vec[dim]
            if dot_product > 0.01:
                scores.append((dot_product, self.chunks[idx]))

        scores.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, chunk in scores[:top_k]:
            item = chunk.to_dict()
            item["score"] = round(score, 4)
            results.append(item)
        return results

class RAGPipeline:
    def __init__(self, knowledge_dir: Path = KNOWLEDGE_DIR):
        self.knowledge_dir = Path(knowledge_dir)
        self.vector_db = LightweightVectorDB()
        self.reload_documents()

    def load_documents(self) -> List[Dict[str, str]]:
        docs = []
        if not self.knowledge_dir.exists():
            return docs

        supported_extensions = [".txt", ".md", ".json", ".csv"]
        for ext in supported_extensions:
            for file_path in self.knowledge_dir.glob(f"*{ext}"):
                try:
                    content = file_path.read_text(encoding="utf-8")
                    if content.strip():
                        docs.append({"source": file_path.name, "text": content})
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
        return docs

    def split_into_chunks(self, documents: List[Dict[str, str]], chunk_size: int = 400, overlap: int = 50) -> List[DocumentChunk]:
        chunks = []
        chunk_id = 1
        for doc in documents:
            text = doc["text"]
            source = doc["source"]
            # Split by double newline / paragraphs
            paragraphs = re.split(r"\n\s*\n", text)
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                if len(para) <= chunk_size:
                    chunks.append(DocumentChunk(para, source, chunk_id))
                    chunk_id += 1
                else:
                    words = para.split()
                    idx = 0
                    while idx < len(words):
                        chunk_words = words[idx : idx + 60]
                        chunks.append(DocumentChunk(" ".join(chunk_words), source, chunk_id))
                        chunk_id += 1
                        idx += 50
        return chunks

    def reload_documents(self):
        docs = self.load_documents()
        chunks = self.split_into_chunks(docs)
        self.vector_db.fit_and_index(chunks)
        return len(docs), len(chunks)

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        return self.vector_db.similarity_search(query, top_k=top_k)

    def build_prompt(self, question: str, context_chunks: List[Dict[str, Any]]) -> str:
        context_str = "\n\n".join([f"[{c['source']}]: {c['text']}" for c in context_chunks])
        return (
            f"You are JARVIS. Answer the user's question using the retrieved knowledge base context below.\n\n"
            f"--- KNOWLEDGE CONTEXT ---\n{context_str}\n-----------------------\n\n"
            f"Question: {question}\n\n"
            f"Answer accurately and concisely, citing the source document when appropriate."
        )

# Global singleton RAG instance
rag_pipeline = RAGPipeline()
