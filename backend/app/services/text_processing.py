import math
from collections import Counter
from typing import List, Dict, Tuple

def tokenize(text: str) -> List[str]:
    """Simple whitespace tokenizer."""
    return text.lower().split()

def calculate_tfidf(corpus: List[str]) -> List[Dict[str, float]]:
    """
    Calculates TF-IDF scores for a corpus of documents.
    Returns a list of dictionaries (one per doc) mapping terms to their TF-IDF score.
    
    This is a "Poor Man's" implementation to avoid heavy dependencies like scikit-learn.
    """
    if not corpus:
        return []

    # 1. Calculate Term Frequencies (TF) per document
    # TF = (count of term in doc) / (total terms in doc)
    tfs = []
    doc_contains_term = Counter()
    
    for doc in corpus:
        tokens = tokenize(doc)
        total_tokens = len(tokens)
        counts = Counter(tokens)
        
        tf_dict = {}
        if total_tokens > 0:
            for term, count in counts.items():
                tf_dict[term] = count / total_tokens
                doc_contains_term[term] += 1
        tfs.append(tf_dict)

    # 2. Calculate Inverse Document Frequency (IDF)
    # IDF = log(Total Docs / (Docs with term))
    # We use (Docs with term + 1) smoothing if desired, but here we stick to basic log
    total_docs = len(corpus)
    idfs = {}
    
    for term, count in doc_contains_term.items():
        # Add 1 to denominator to avoid division by zero (smoothing)
        # Add 1 to numerator to behave like sklearn's default settings usually do
        idfs[term] = math.log((total_docs + 1) / (count + 1)) + 1 

    # 3. Calculate TF-IDF
    results = []
    for tf_dict in tfs:
        tfidf_doc = {}
        for term, tf_val in tf_dict.items():
            tfidf_doc[term] = tf_val * idfs[term]
        results.append(tfidf_doc)
        
    return results

def get_top_keywords(doc_text: str, corpus: List[str], top_n: int = 5) -> List[Tuple[str, float]]:
    """Helper to extract top keywords for a single document given a corpus context."""
    # We need to re-process the whole corpus to get IDF context
    # In a real app, IDFs would be pre-computed.
    # Check if doc exists in corpus, if not add it temp
    if doc_text not in corpus:
        context_corpus = corpus + [doc_text]
        target_idx = len(corpus)
    else:
        context_corpus = corpus
        target_idx = corpus.index(doc_text)
        
    tfidf_results = calculate_tfidf(context_corpus)
    target_scores = tfidf_results[target_idx]
    
    # Sort by score desc
    sorted_items = sorted(target_scores.items(), key=lambda item: item[1], reverse=True)
    return sorted_items[:top_n]
