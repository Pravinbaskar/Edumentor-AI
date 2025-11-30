"""
Quick test script to verify vector store functionality.
"""
from edumentor.services.vector_store import VectorStore
from edumentor.services.pdf_processor import PDFProcessor

def test_vector_store():
    print("Testing VectorStore...")
    
    # Initialize vector store
    vs = VectorStore(data_dir="data/vector_store_test")
    
    # Test adding documents
    test_docs = [
        "Photosynthesis is the process by which plants make their own food using sunlight.",
        "Plants contain chlorophyll which gives them their green color.",
        "Water and carbon dioxide are needed for photosynthesis to occur."
    ]
    
    num_added = vs.add_documents(
        subject="science",
        texts=test_docs,
        source="test_biology.pdf"
    )
    print(f"✅ Added {num_added} documents to science vector store")
    
    # Test search
    query = "How do plants make food?"
    results = vs.search("science", query, top_k=2)
    
    print(f"\n🔍 Search results for: '{query}'")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. Score: {result['score']:.4f}")
        print(f"   Text: {result['text'][:100]}...")
        print(f"   Source: {result['source']}")
    
    # Test stats
    stats = vs.get_subject_stats("science")
    print(f"\n📊 Stats: {stats}")
    
    # Clean up
    vs.delete_subject_data("science")
    print("\n🧹 Cleaned up test data")
    
    print("\n✅ All tests passed!")

def test_pdf_processor():
    print("\nTesting PDFProcessor...")
    
    # Test text chunking
    sample_text = """
    This is a sample text for testing the chunking functionality.
    It should be split into multiple chunks based on the chunk size parameter.
    
    Each chunk should maintain context and have some overlap with adjacent chunks.
    This helps in maintaining semantic coherence when retrieving similar content.
    
    The PDF processor will first extract text from PDF files and then chunk them.
    """
    
    chunks = PDFProcessor.chunk_text(sample_text, chunk_size=100, overlap=20)
    print(f"✅ Created {len(chunks)} chunks from sample text")
    for i, chunk in enumerate(chunks, 1):
        print(f"\nChunk {i}: {chunk[:80]}...")
    
    print("\n✅ PDF processor tests passed!")

if __name__ == "__main__":
    try:
        test_vector_store()
        test_pdf_processor()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
