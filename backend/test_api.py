import os
import sys

# Ensure backend can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.preprocessing import clean_text, extract_xai_metrics
from backend.fake_review_model import predict_review, load_model
from backend.sentiment_analysis import analyze_sentiment
from backend.summarizer import summarize_reviews
from backend.database import engine, Base
from backend.models import User, Product, Review, AnalysisHistory

def run_diagnostics():
    print("==================================================")
    print("          ReviewGuard AI Diagnostic Tests         ")
    print("==================================================")
    
    # 1. Test Preprocessing
    print("\n[1/5] Testing Text Preprocessing...")
    test_text = "This product is AMAZING!!! Best display ever, buy now!"
    cleaned = clean_text(test_text)
    print(f"Original: '{test_text}'")
    print(f"Cleaned:  '{cleaned}'")
    assert "amazing" in cleaned or "amaz" in cleaned, "Cleaning failed"
    print("[OK] Text Preprocessing passed.")
    
    # 2. Test Explainable AI Features
    print("\n[2/5] Testing Explainable AI Metrics...")
    xai_metrics = extract_xai_metrics(test_text)
    print(f"Metrics extracted for review: {xai_metrics}")
    assert xai_metrics["exclamation_count"] >= 3, "Exclamations count mismatch"
    assert xai_metrics["caps_lock_detected"] is True or xai_metrics["capitals_ratio"] > 0.1, "Caps ratio mismatch"
    print("[OK] Explainable AI metrics passed.")
    
    # 3. Test Machine Learning Inference
    print("\n[3/5] Testing Machine Learning Model Prediction...")
    model, vectorizer = load_model()
    if model is None or vectorizer is None:
        print("Model file not found! Falling back to heuristic mode.")
    
    # Test Fake Review detection
    fake_review = "BUY NOW VOUCHER FREE DISCOUNT!!! 100% REFUND WWW.DEALS.COM"
    fake_res = predict_review(fake_review)
    print(f"Prediction for suspect text: {fake_res['prediction']} (Confidence: {fake_res['confidence']})")
    print(f"Reasons flagged: {fake_res['reasons']}")
    assert fake_res["prediction"] == "Fake", "Suspect review was not flagged"
    
    # Test Genuine Review detection
    gen_review = "Decent screen quality, but battery backup takes two hours to charge."
    gen_res = predict_review(gen_review)
    print(f"Prediction for organic text: {gen_res['prediction']} (Confidence: {gen_res['confidence']})")
    print(f"Reasons flagged: {gen_res['reasons']}")
    assert gen_res["prediction"] == "Genuine", "Genuine review was flagged"
    print("[OK] Model Prediction diagnostics passed.")
    
    # 4. Test Sentiment Analysis & Opinion Summarizer
    print("\n[4/5] Testing Sentiment & Summarization Modules...")
    sent_res1 = analyze_sentiment("Decent screen, battery drains fast.")
    sent_res2 = analyze_sentiment("This camera is absolutely spectacular! I love it.")
    print(f"Sentiment 1: {sent_res1} (Expected: Negative or Neutral)")
    print(f"Sentiment 2: {sent_res2} (Expected: Positive)")
    
    mock_reviews = [
        {"review_text": "Decent screen quality, screen looks beautiful.", "prediction": "Genuine", "sentiment": "Positive"},
        {"review_text": "Decent performance, battery drains fast.", "prediction": "Genuine", "sentiment": "Negative"},
        {"review_text": "Good screen resolution.", "prediction": "Genuine", "sentiment": "Positive"},
        {"review_text": "Buy now promo code click here!", "prediction": "Fake", "sentiment": "Positive"}
    ]
    summary = summarize_reviews(mock_reviews)
    print("Generated AI Summary:")
    print(f"  Summary: {summary['short_summary']}")
    print(f"  Pros:    {summary['pros']}")
    print(f"  Cons:    {summary['cons']}")
    print(f"  Rec:     {summary['recommendation']}")
    assert len(summary["pros"]) > 0, "No pros generated"
    print("[OK] Sentiment & Summarizer diagnostics passed.")
    
    # 5. Database Schema Checks
    print("\n[5/6] Checking Database Schemas & Connecting...")
    try:
        # Re-initialize schemas on engine
        Base.metadata.create_all(bind=engine)
        print("[OK] Database connection and SQLAlchemy mappings validated successfully.")
    except Exception as e:
        print(f"[FAIL] Database connection failed: {e}")
        sys.exit(1)
        
    # 6. Test AI Shopping Advisor & Scam Warnings
    print("\n[6/6] Testing AI Shopping Advisor & Scam Warnings...")
    try:
        from backend.advisor import generate_advisor_data
        mock_reviews_extended = [
            {"review_text": "Decent screen quality, screen looks beautiful.", "prediction": "Genuine", "sentiment": "Positive", "metrics": {}, "reasons": []},
            {"review_text": "Decent performance, battery drains fast.", "prediction": "Genuine", "sentiment": "Negative", "metrics": {}, "reasons": []},
            {"review_text": "Good screen resolution.", "prediction": "Genuine", "sentiment": "Positive", "metrics": {}, "reasons": []},
            {"review_text": "Buy now promo code click here!", "prediction": "Fake", "sentiment": "Positive", "metrics": {"caps_lock_detected": False, "excessive_punctuation": False, "ai_patterns_detected": False}, "reasons": []}
        ]
        advisor_res = generate_advisor_data("Test Gadget", mock_reviews_extended)
        print(f"Scam Warning Level: {advisor_res['scam_warning']['risk_level']}")
        print(f"Scam Message:       {advisor_res['scam_warning']['warning_message']}")
        print(f"Advisor Verdict:    {advisor_res['advisor']['verdict_title']}")
        print(f"Advisor Advice:     {advisor_res['advisor']['buying_advice']}")
        
        assert "scam_warning" in advisor_res, "scam_warning key missing in response"
        assert "advisor" in advisor_res, "advisor key missing in response"
        assert "risk_level" in advisor_res["scam_warning"], "risk_level missing"
        assert "verdict" in advisor_res["advisor"], "verdict missing"
        print("[OK] AI Shopping Advisor & Scam Warnings passed.")
    except Exception as e:
        print(f"[FAIL] AI Advisor validation failed: {e}")
        sys.exit(1)
        
    print("\n==================================================")
    print("    ALL SYSTEM DIAGNOSTICS COMPLETED SUCCESSFULLY   ")
    print("==================================================")

if __name__ == "__main__":
    run_diagnostics()
