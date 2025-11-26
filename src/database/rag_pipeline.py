import os
from typing import List, Dict, Any, Optional, Union
import hashlib
from datetime import datetime
import json

# Pinecone
from pinecone import Pinecone, ServerlessSpec

# Embeddings
from sentence_transformers import SentenceTransformer

# Text processing
import re
from dataclasses import dataclass

@dataclass
class Document:
    """Document data structure"""
    id: str
    text: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None

@dataclass
class RetrievalResult:
    """Retrieval result structure"""
    id: str
    text: str
    score: float
    metadata: Dict[str, Any]

class RAGPipeline:
    """
    Complete RAG Pipeline with Pinecone Cloud
    
    Features:
    - Document ingestion and chunking
    - Embedding generation
    - Vector storage in Pinecone
    - Semantic search and retrieval
    - Context management
    """
    
    def __init__(
        self,
        pinecone_api_key: str,
        index_name: str = "rag-documents",
        embedding_model: str = "all-MiniLM-L6-v2",
        dimension: int = 384,
        cloud: str = "aws",
        region: str = "us-east-1"
    ):
        """
        Initialize RAG Pipeline
        
        Args:
            pinecone_api_key: Pinecone API key
            index_name: Name of Pinecone index
            embedding_model: Sentence transformer model name
            dimension: Embedding dimension
            cloud: Cloud provider (aws, gcp, azure)
            region: Cloud region
        """
        self.pinecone_api_key = pinecone_api_key
        self.index_name = index_name
        self.dimension = dimension
        self.cloud = cloud
        self.region = region
        
        # Initialize Pinecone
        self.pc = Pinecone(api_key=pinecone_api_key)
        
        # Initialize embedding model
        print(f"Loading embedding model: {embedding_model}...")
        self.embedding_model = SentenceTransformer(embedding_model)
        
        # Create or connect to index
        self._initialize_index()
        
        print(f"✅ RAG Pipeline initialized with index: {index_name}")
    
    def _initialize_index(self):
        """Create or connect to Pinecone index"""
        existing_indexes = [index.name for index in self.pc.list_indexes()]
        
        if self.index_name not in existing_indexes:
            print(f"Creating new index: {self.index_name}...")
            self.pc.create_index(
                name=self.index_name,
                dimension=self.dimension,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud=self.cloud,
                    region=self.region
                )
            )
            print(f"✅ Index {self.index_name} created")
        else:
            print(f"✅ Connected to existing index: {self.index_name}")
        
        # Connect to index
        self.index = self.pc.Index(self.index_name)
    
    def _generate_id(self, text: str) -> str:
        """Generate unique ID for document"""
        return hashlib.md5(text.encode()).hexdigest()
    
    def _chunk_text(
        self,
        text: str,
        chunk_size: int = 500,
        overlap: int = 50
    ) -> List[str]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Input text
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        # Clean text
        text = re.sub(r'\s+', ' ', text).strip()
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings
                for delimiter in ['. ', '! ', '? ', '\n']:
                    last_delim = text[start:end].rfind(delimiter)
                    if last_delim != -1:
                        end = start + last_delim + len(delimiter)
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
        
        return chunks
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector
        """
        embedding = self.embedding_model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def add_document(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: int = 500,
        overlap: int = 50
    ) -> List[str]:
        """
        Add a document to the pipeline
        
        Args:
            text: Document text
            metadata: Additional metadata
            chunk_size: Size of text chunks
            overlap: Overlap between chunks
            
        Returns:
            List of document IDs added
        """
        if metadata is None:
            metadata = {}
        
        # Add timestamp
        metadata['timestamp'] = datetime.now().isoformat()
        
        # Chunk the text
        chunks = self._chunk_text(text, chunk_size, overlap)
        
        print(f"Adding document: {len(chunks)} chunks")
        
        documents = []
        doc_ids = []
        
        for i, chunk in enumerate(chunks):
            # Generate unique ID
            doc_id = self._generate_id(f"{text[:50]}_{i}")
            doc_ids.append(doc_id)
            
            # Generate embedding
            embedding = self.generate_embedding(chunk)
            
            # Prepare metadata
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                'text': chunk,
                'chunk_index': i,
                'total_chunks': len(chunks)
            })
            
            documents.append({
                'id': doc_id,
                'values': embedding,
                'metadata': chunk_metadata
            })
        
        # Upsert to Pinecone
        self.index.upsert(vectors=documents)
        
        print(f"✅ Added {len(documents)} chunks to index")
        return doc_ids
    
    def add_documents_batch(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        chunk_size: int = 500,
        overlap: int = 50,
        batch_size: int = 100
    ) -> List[List[str]]:
        """
        Add multiple documents in batch
        
        Args:
            texts: List of document texts
            metadatas: List of metadata dicts
            chunk_size: Size of text chunks
            overlap: Overlap between chunks
            batch_size: Batch size for upserting
            
        Returns:
            List of document ID lists
        """
        if metadatas is None:
            metadatas = [{}] * len(texts)
        
        all_doc_ids = []
        all_documents = []
        
        for text, metadata in zip(texts, metadatas):
            chunks = self._chunk_text(text, chunk_size, overlap)
            
            for i, chunk in enumerate(chunks):
                doc_id = self._generate_id(f"{text[:50]}_{i}")
                embedding = self.generate_embedding(chunk)
                
                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    'text': chunk,
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'timestamp': datetime.now().isoformat()
                })
                
                all_documents.append({
                    'id': doc_id,
                    'values': embedding,
                    'metadata': chunk_metadata
                })
        
        # Batch upsert
        print(f"Upserting {len(all_documents)} documents in batches...")
        
        for i in range(0, len(all_documents), batch_size):
            batch = all_documents[i:i + batch_size]
            self.index.upsert(vectors=batch)
            print(f"  Uploaded batch {i//batch_size + 1}/{(len(all_documents)-1)//batch_size + 1}")
        
        print(f"✅ Added {len(all_documents)} total chunks from {len(texts)} documents")
        
        return all_doc_ids
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant documents for a query
        
        Args:
            query: Search query
            top_k: Number of results to return
            filter_dict: Metadata filters
            include_metadata: Include metadata in results
            
        Returns:
            List of RetrievalResult objects
        """
        # Generate query embedding
        query_embedding = self.generate_embedding(query)
        
        # Search Pinecone
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=include_metadata,
            filter=filter_dict
        )
        
        # Parse results
        retrieval_results = []
        for match in results['matches']:
            result = RetrievalResult(
                id=match['id'],
                text=match['metadata'].get('text', ''),
                score=match['score'],
                metadata=match['metadata']
            )
            retrieval_results.append(result)
        
        return retrieval_results
    
    def retrieve_with_context(
        self,
        query: str,
        top_k: int = 5,
        context_window: int = 1
    ) -> List[RetrievalResult]:
        """
        Retrieve documents with surrounding context chunks
        
        Args:
            query: Search query
            top_k: Number of results
            context_window: Number of surrounding chunks to include
            
        Returns:
            List of RetrievalResult with expanded context
        """
        results = self.retrieve(query, top_k)
        
        expanded_results = []
        for result in results:
            chunk_index = result.metadata.get('chunk_index', 0)
            total_chunks = result.metadata.get('total_chunks', 1)
            
            # Get surrounding chunks if available
            context_text = result.text
            
            # This is a simplified version - in production you'd fetch adjacent chunks
            expanded_results.append(result)
        
        return expanded_results
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        return_text_only: bool = False
    ) -> Union[List[str], List[RetrievalResult]]:
        """
        Simple search interface
        
        Args:
            query: Search query
            top_k: Number of results
            return_text_only: Return only text strings
            
        Returns:
            List of texts or RetrievalResult objects
        """
        results = self.retrieve(query, top_k)
        
        if return_text_only:
            return [r.text for r in results]
        
        return results
    
    def delete_document(self, doc_id: str):
        """Delete a document by ID"""
        self.index.delete(ids=[doc_id])
        print(f"✅ Deleted document: {doc_id}")
    
    def delete_documents(self, doc_ids: List[str]):
        """Delete multiple documents"""
        self.index.delete(ids=doc_ids)
        print(f"✅ Deleted {len(doc_ids)} documents")
    
    def delete_all(self):
        """Delete all documents from index"""
        self.index.delete(delete_all=True)
        print(f"✅ Deleted all documents from index: {self.index_name}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        stats = self.index.describe_index_stats()
        return {
            'total_vectors': stats.total_vector_count,
            'dimension': stats.dimension,
            'index_fullness': stats.index_fullness,
            'namespaces': stats.namespaces
        }
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a specific document by ID
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document data or None
        """
        result = self.index.fetch(ids=[doc_id])
        
        if doc_id in result['vectors']:
            return result['vectors'][doc_id]
        
        return None
    
    def update_metadata(
        self,
        doc_id: str,
        metadata: Dict[str, Any]
    ):
        """
        Update metadata for a document
        
        Args:
            doc_id: Document ID
            metadata: New metadata
        """
        # Fetch existing document
        doc = self.get_document(doc_id)
        
        if doc:
            # Merge metadata
            existing_metadata = doc.get('metadata', {})
            existing_metadata.update(metadata)
            
            # Update
            self.index.upsert(
                vectors=[{
                    'id': doc_id,
                    'values': doc['values'],
                    'metadata': existing_metadata
                }]
            )
            print(f"✅ Updated metadata for: {doc_id}")
        else:
            print(f"❌ Document not found: {doc_id}")
    
    def generate_rag_context(
        self,
        query: str,
        top_k: int = 3,
        max_context_length: int = 2000
    ) -> str:
        """
        Generate context for RAG (Retrieval Augmented Generation)
        
        Args:
            query: User query
            top_k: Number of documents to retrieve
            max_context_length: Maximum context length
            
        Returns:
            Formatted context string
        """
        results = self.retrieve(query, top_k)
        
        context_parts = []
        current_length = 0
        
        for i, result in enumerate(results):
            text = result.text
            
            if current_length + len(text) > max_context_length:
                # Truncate if needed
                remaining = max_context_length - current_length
                text = text[:remaining] + "..."
            
            context_parts.append(f"[Document {i+1}] (Score: {result.score:.3f})\n{text}\n")
            current_length += len(text)
            
            if current_length >= max_context_length:
                break
        
        return "\n".join(context_parts)
    
    def create_rag_prompt(
        self,
        query: str,
        system_prompt: str = "You are a helpful assistant. Use the following context to answer the question.",
        top_k: int = 3
    ) -> str:
        """
        Create a complete RAG prompt with context
        
        Args:
            query: User query
            system_prompt: System instruction
            top_k: Number of documents to retrieve
            
        Returns:
            Complete prompt with context
        """
        context = self.generate_rag_context(query, top_k)
        
        prompt = f"""{system_prompt}

Context:
{context}

Question: {query}

Answer:"""
        
        return prompt


# ============= EXAMPLE USAGE =============

def example_usage():
    """Example usage of RAG Pipeline"""
    
    # Load Pinecone API key from environment
    import os
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))
    pinecone_api_key = os.getenv('PINECONE_API_KEY')

    # Initialize
    rag = RAGPipeline(
        pinecone_api_key=pinecone_api_key,
        index_name="my-rag-index",
        embedding_model="all-MiniLM-L6-v2"
    )
    
    # Add documents
    doc1 = """
    Python is a high-level programming language. It was created by Guido van Rossum
    and first released in 1991. Python emphasizes code readability and allows
    programmers to express concepts in fewer lines of code.
    """
    
    doc2 = """
    Machine learning is a subset of artificial intelligence. It focuses on
    building systems that can learn from data. Common algorithms include
    neural networks, decision trees, and support vector machines.
    """
    
    # Add single document
    rag.add_document(
        text=doc1,
        metadata={'source': 'python_docs', 'category': 'programming'}
    )
    
    # Add multiple documents
    rag.add_documents_batch(
        texts=[doc2],
        metadatas=[{'source': 'ml_docs', 'category': 'ai'}]
    )
    
    # Retrieve relevant documents
    query = "What is Python?"
    results = rag.retrieve(query, top_k=3)
    
    for result in results:
        print(f"\nScore: {result.score:.3f}")
        print(f"Text: {result.text}")
        print(f"Metadata: {result.metadata}")
    
    # Generate RAG context
    context = rag.generate_rag_context(query, top_k=2)
    print(f"\nRAG Context:\n{context}")
    
    # Get index stats
    stats = rag.get_stats()
    print(f"\nIndex Stats: {stats}")


if __name__ == "__main__":
    example_usage()
