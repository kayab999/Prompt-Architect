import pytest
import math
from app.services import text_processing

def test_tokenize():
    text = "Hello World"
    assert text_processing.tokenize(text) == ["hello", "world"]

def test_calculate_tfidf_simple():
    corpus = [
        "this is a sample",
        "this is another example another example example"
    ]
    results = text_processing.calculate_tfidf(corpus)
    
    assert len(results) == 2
    
    # Check Doc 1
    # "sample" appears once.
    # Total docs = 2. Docs with "sample" = 1.
    # IDF = log((2+1)/(1+1)) + 1 = log(1.5) + 1 ≈ 1.405
    # TF = 1/4 = 0.25
    # TF-IDF ≈ 0.35
    
    sample_score = results[0].get("sample")
    assert sample_score > 0
    
    # Check Doc 2
    # "example" appears 3 times. Total tokens = 7.
    # TF = 3/7 ≈ 0.428
    # IDF = log(1.5) + 1 ≈ 1.405
    # TF-IDF ≈ 0.6
    
    example_score = results[1]["example"]
    assert example_score > 0.5 

def test_get_top_keywords():
    corpus = [
        "machine learning is great",
        "machine learning models are cool",
        "machines are learning"
    ]
    doc = "machine learning models"
    
    keywords = text_processing.get_top_keywords(doc, corpus, top_n=2)
    assert len(keywords) == 2
    # "models" is rarer than "machine" or "learning", so it should score high
    top_word = keywords[0][0]
    assert top_word == "models"

def test_scikit_learn_fallback_scenario():
    """Ensure our code works without sklearn import."""
    try:
        import sklearn
        pytest.skip("sklearn is installed, but we want to test that our code does dependency-free calc")
    except ImportError:
        pass
    
    corpus = ["data science", "data engineering"]
    results = text_processing.calculate_tfidf(corpus)
    assert len(results) == 2
