#!/usr/bin/env python3
"""
FAISS Status Checker - Check FAISS vector store status
"""

import os
import json
import numpy as np
from pathlib import Path

def check_faiss_status():
    """Check FAISS vector store status"""
    print("🔍 FAISS Vector Store Status Check")
    print("=" * 50)
    
    index_path = Path("data/index")
    
    # Check if index directory exists
    if not index_path.exists():
        print("❌ FAISS index directory not found!")
        return False
    
    # Check required files
    required_files = ["faiss.index", "embeddings.npy", "docstore.jsonl", "ids.txt"]
    missing_files = []
    
    for file_name in required_files:
        file_path = index_path / file_name
        if file_path.exists():
            size = file_path.stat().st_size
            print(f"✅ {file_name}: {size:,} bytes")
        else:
            missing_files.append(file_name)
            print(f"❌ {file_name}: MISSING")
    
    if missing_files:
        print(f"\n❌ Missing files: {missing_files}")
        return False
    
    # Check embeddings
    try:
        embeddings_path = index_path / "embeddings.npy"
        embeddings = np.load(embeddings_path)
        print(f"\n📊 Embeddings Information:")
        print(f"   Shape: {embeddings.shape}")
        print(f"   Documents: {embeddings.shape[0]}")
        print(f"   Dimensions: {embeddings.shape[1]}")
        print(f"   Size: {embeddings.nbytes:,} bytes")
        
        if embeddings.shape[0] > 0:
            print("✅ FAISS contains documents!")
        else:
            print("❌ FAISS has no documents!")
            return False
            
    except Exception as e:
        print(f"❌ Error loading embeddings: {e}")
        return False
    
    # Check docstore
    try:
        docstore_path = index_path / "docstore.jsonl"
        with open(docstore_path, 'r') as f:
            lines = f.readlines()
            print(f"\n📄 Document Store:")
            print(f"   Lines: {len(lines)}")
            print(f"   Size: {docstore_path.stat().st_size:,} bytes")
            
            if len(lines) > 0:
                print("✅ Document store has content!")
            else:
                print("❌ Document store is empty!")
                return False
                
    except Exception as e:
        print(f"❌ Error reading docstore: {e}")
        return False
    
    # Check FAISS index
    try:
        import faiss
        faiss_path = index_path / "faiss.index"
        index = faiss.read_index(str(faiss_path))
        print(f"\n🔍 FAISS Index:")
        print(f"   Index size: {index.ntotal}")
        print(f"   Dimension: {index.d}")
        print(f"   Is trained: {index.is_trained}")
        
        if index.ntotal > 0:
            print("✅ FAISS index is working!")
        else:
            print("❌ FAISS index is empty!")
            return False
            
    except Exception as e:
        print(f"❌ Error loading FAISS index: {e}")
        return False
    
    print("\n🎉 FAISS Status: HEALTHY!")
    print("✅ All components working properly")
    return True

if __name__ == "__main__":
    check_faiss_status()
