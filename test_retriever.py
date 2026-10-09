#!/usr/bin/env python3
"""
Test script for the RAG retriever with multi-source support.
Tests the end-to-end flow: load documents from different sources, index them, and search with source filtering.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from core.document import Document
from core.retriever import RAGRetriever
from pathlib import Path


def main():
    print("Testing RAG Retriever with multi-source support...")

    # Create a RAGRetriever
    print("Initializing RAG Retriever...")
    retriever = RAGRetriever()

    # 1. Test with Techbox document (source="techbox")
    print("\n" + "="*60)
    print("TEST 1: Techbox document (source='techbox')")
    print("="*60)

    techbox_url = "https://raw.githubusercontent.com/EstefGlez/techbox-mx/refs/heads/main/especificaciones-techbox.md"
    print(f"Loading Techbox document from: {techbox_url}")

    # Create Document with source_type="techbox"
    techbox_doc = Document(location=techbox_url, source_type="techbox")
    retriever.add_document(techbox_doc)
    print("Techbox document indexed successfully.")

    # Search for shipping information with source="techbox"
    query_envio = "¿cuánto tarda el envío?"
    print(f"\nSearching for: '{query_envio}' (source='techbox')")
    results_envio = retriever.search(query_envio, top_k=3, source="techbox")

    print(f"\nFound {len(results_envio)} relevant chunks:")
    print("-" * 50)
    for i, chunk in enumerate(results_envio, 1):
        print(f"Chunk {i}:")
        print(chunk)
        print("-" * 50)

    # Check if the results contain expected information about shipping time
    shipping_info_found = False
    for chunk in results_envio:
        if "24" in chunk and "72" in chunk and ("hora" in chunk or "horas" in chunk):
            shipping_info_found = True
            break

    if shipping_info_found:
        print("[OK] SUCCESS: Found shipping information (24-72 hours) in the results.")
    else:
        print("[WARN] WARNING: Could not confirm shipping information (24-72 hours) in results.")
        print("   The retrieved chunks might not contain the expected answer.")

    # 2. Test with Obsidian folder from GitHub (source="obsidian")
    print("\n" + "="*60)
    print("TEST 2: Obsidian folder from GitHub (source='obsidian')")
    print("="*60)

    try:
        # Load Obsidian documents from GitHub with source_type="obsidian"
        print(f"Loading Obsidian documents from GitHub...")
        retriever.load_from_github_folder(
            owner="EstefGlez",
            repo="Estefano-Gonzalez-Data-Analytics-Portfolio",
            folder_path="Notebook-TripleTen/Arsenal_Tecnico",
            source_type="obsidian",
            branch="main"
        )
        print("Obsidian documents from GitHub indexed successfully.")
    except Exception as e:
        print(f"Error loading Obsidian folder from GitHub: {e}")
        print("Continuing with test anyway...")

    # Search for pandas information with source="obsidian"
    query_pandas = "¿Cómo se hace un groupby en pandas?"
    print(f"\nSearching for: '{query_pandas}' (source='obsidian')")
    results_pandas = retriever.search(query_pandas, top_k=3, source="obsidian")

    print(f"\nFound {len(results_pandas)} relevant chunks:")
    print("-" * 50)
    for i, chunk in enumerate(results_pandas, 1):
        print(f"Chunk {i}:")
        print(chunk)
        print("-" * 50)

    # Check if the results contain expected information about groupby
    groupby_info_found = False
    for chunk in results_pandas:
        if ("groupby" in chunk.lower() or "group by" in chunk.lower()) and \
           ("pandas" in chunk.lower() or "dataframe" in chunk.lower()):
            groupby_info_found = True
            break

    if groupby_info_found:
        print("[OK] SUCCESS: Found groupby information in the results.")
    else:
        print("[WARN] WARNING: Could not confirm groupby information in results.")
        print("   The retrieved chunks might not contain the expected answer.")

    # 3. Test cross-source filtering (should not find techbox info in obsidian search)
    print("\n" + "="*60)
    print("TEST 3: Cross-source verification")
    print("="*60)

    print(f"Searching for shipping info in Obsidian source (should not find): '{query_envio}' (source='obsidian')")
    results_cross = retriever.search(query_envio, top_k=3, source="obsidian")

    if len(results_cross) == 0:
        print("[OK] SUCCESS: No shipping information found in Obsidian source (correct filtering).")
    else:
        print("[INFO] Found some results in Obsidian source when searching for shipping info:")
        for i, chunk in enumerate(results_cross, 1):
            try:
                print(f"  Chunk {i}: {chunk[:100]}...")
            except UnicodeEncodeError:
                print(f"  Chunk {i}: [Content contains special characters that cannot be displayed]")

    print("\n" + "="*60)
    print("TEST COMPLETED")
    print("="*60)

    return 0


if __name__ == "__main__":
    exit(main())