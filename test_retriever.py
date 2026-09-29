#!/usr/bin/env python3
"""
Test script for the RAG retriever.
Tests the end-to-end flow: load document from URL, index it, and search.
"""

from core.document import Document
from core.retriever import RAGRetriever


def main():
    print("Testing RAG Retriever...")

    # URL of the Techbox specifications document
    url = "https://raw.githubusercontent.com/EstefGlez/techbox-mx/refs/heads/main/especificaciones-techbox.md"

    try:
        # 1. Create a Document from the URL
        print(f"Loading document from URL: {url}")
        doc = Document(url)
        # Load content (this will download the content)
        content = doc.load_content()
        print(f"Document loaded. Content length: {len(content)} characters")

        # 2. Create a RAGRetriever and index the document
        print("Initializing RAG Retriever...")
        retriever = RAGRetriever()

        print("Indexing document...")
        retriever.add_document(doc)
        print("Document indexed successfully.")

        # 3. Perform a test search
        query = "¿cuánto tarda el envío?"
        print(f"\nSearching for: '{query}'")
        results = retriever.search(query, top_k=3)

        # 4. Print the results
        print(f"\nFound {len(results)} relevant chunks:")
        print("-" * 50)
        for i, chunk in enumerate(results, 1):
            print(f"Chunk {i}:")
            print(chunk)
            print("-" * 50)

        # Check if the results contain expected information about shipping time
        # The expected answer is about 24 to 72 hours for shipping
        shipping_info_found = False
        for chunk in results:
            if "24" in chunk and "72" in chunk and ("hora" in chunk or "horas" in chunk):
                shipping_info_found = True
                break

        if shipping_info_found:
            print("[OK] SUCCESS: Found shipping information (24-72 hours) in the results.")
        else:
            print("[WARN] WARNING: Could not confirm shipping information (24-72 hours) in results.")
            print("   The retrieved chunks might not contain the expected answer.")

    except Exception as e:
        print(f"[ERR] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())