import os
import pickle
import numpy as np
from .preprocessing import clean_text, extract_xai_metrics

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "trained_model")
MODEL_PATH = os.path.join(MODEL_DIR, "model.pkl")
VECTORIZER_PATH = os.path.join(MODEL_DIR, "vectorizer.pkl")

# Global variables for model and vectorizer
_model = None
_vectorizer = None

def load_model():
    """
    Loads the trained Logistic Regression model and TF-IDF Vectorizer.
    """
    global _model, _vectorizer
    if _model is not None and _vectorizer is not None:
        return _model, _vectorizer
    
    if os.path.exists(MODEL_PATH) and os.path.exists(VECTORIZER_PATH):
        try:
            with open(MODEL_PATH, "rb") as f:
                _model = pickle.load(f)
            with open(VECTORIZER_PATH, "rb") as f:
                _vectorizer = pickle.load(f)
            print("Loaded trained fake review model successfully.")
            return _model, _vectorizer
        except Exception as e:
            print(f"Error loading model files: {e}. Resetting to fallback.")
            
    _model = None
    _vectorizer = None
    return None, None

def save_model(model, vectorizer):
    """
    Saves the trained model and vectorizer to disk.
    """
    global _model, _vectorizer
    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    with open(VECTORIZER_PATH, "wb") as f:
        pickle.dump(vectorizer, f)
    _model = model
    _vectorizer = vectorizer
    print("Saved fake review model successfully.")

def predict_review(text: str) -> dict:
    """
    Predicts if a review is 'Genuine' or 'Fake' and returns confidence and explanation reasons.
    """
    model, vectorizer = load_model()
    xai_metrics = extract_xai_metrics(text)
    
    # Heuristic rules to blend with the model (ensuring excellent explainability and robustness)
    # If model is not trained yet, use pure heuristic fallback
    if model is None or vectorizer is None:
        # Pure heuristic prediction
        score = 0
        reasons = []
        if xai_metrics["caps_lock_detected"]:
            score += 2
            reasons.append("Excessive promotional capital letters (SHOUTING)")
        if xai_metrics["excessive_punctuation"]:
            score += 2
            reasons.append("Too many exclamation marks (promotional style)")
        if xai_metrics["repeated_phrases_found"]:
            score += 1.5
            reasons.append("Unnatural repeated phrasing or low vocabulary diversity")
        if xai_metrics["promotional_score"] > 0:
            score += 2.0 * xai_metrics["promotional_score"]
            reasons.append(f"Contains promotional/spam trigger words ({xai_metrics['promotional_score']} instances)")
        if xai_metrics.get("ai_patterns_detected"):
            score += 2.5
            reasons.append("ChatGPT / LLM stylistic patterns detected (perfect grammar, formal transitions, AI-typical phrasing)")
        
        # Determine classification
        # Score threshold: 2.0
        if score >= 2.0:
            prediction = "Fake"
            confidence = min(0.5 + (score * 0.1), 0.99)
        else:
            prediction = "Genuine"
            confidence = max(0.99 - (score * 0.15), 0.50)
            if not reasons:
                reasons.append("Natural wording and grammar structure")
                
        return {
            "prediction": prediction,
            "confidence": round(float(confidence), 2),
            "reasons": reasons,
            "metrics": xai_metrics
        }

    # Model inference
    cleaned = clean_text(text)
    if not cleaned.strip():
        # Empty text fallback
        return {
            "prediction": "Genuine",
            "confidence": 0.50,
            "reasons": ["Insufficient text for evaluation"],
            "metrics": xai_metrics
        }
        
    vec = vectorizer.transform([cleaned])
    prob = model.predict_proba(vec)[0]  # [prob_genuine, prob_fake] (assuming 0 is Genuine, 1 is Fake)
    pred_idx = np.argmax(prob)
    
    confidence = float(prob[pred_idx])
    prediction = "Fake" if pred_idx == 1 else "Genuine"
    
    # Blending AI heuristic detection with the ML model
    # If the model thought it was Genuine, but the AI-generation indicators are strongly present
    # (and the model's genuine probability is not extremely high, say, less than 0.85)
    if prediction == "Genuine" and xai_metrics.get("ai_patterns_detected") and prob[0] < 0.85:
        prediction = "Fake"
        # Overwrite confidence by blending the probabilities
        fake_prob = max(prob[1], 0.55 + (xai_metrics["ai_score"] * 0.05))
        confidence = min(fake_prob, 0.99)
        
    # Gather words that influenced the decision
    feature_names = vectorizer.get_feature_names_out()
    coef = model.coef_[0]
    
    words_in_text = cleaned.split()
    influenced_reasons = []
    
    # Find active features in this review
    active_features = []
    for word in set(words_in_text):
        if word in vectorizer.vocabulary_:
            idx = vectorizer.vocabulary_[word]
            weight = coef[idx]
            active_features.append((word, weight))
            
    # Sort active features by magnitude
    active_features.sort(key=lambda x: x[1], reverse=True) # positive weights favor 'Fake'
    
    # Explainable AI logs based on metrics & coefficients
    reasons = []
    if prediction == "Fake":
        # Check heuristics first
        if xai_metrics["caps_lock_detected"]:
            reasons.append("Excessive promotional capital letters (SHOUTING)")
        if xai_metrics["excessive_punctuation"]:
            reasons.append("Too many exclamation marks (promotional style)")
        if xai_metrics["repeated_phrases_found"]:
            reasons.append("Unnatural repeated phrasing or low vocabulary diversity")
        if xai_metrics["promotional_score"] > 0:
            reasons.append("Contains promotional or spam keywords")
        if xai_metrics.get("ai_patterns_detected"):
            reasons.append("ChatGPT / LLM stylistic patterns detected (perfect grammar, formal transitions, AI-typical phrasing)")
            
        # Add key features from the model coefficients
        fake_words = [w for w, weight in active_features if weight > 0.2][:3]
        if fake_words:
            reasons.append(f"Model flagged suspicious words: {', '.join(fake_words)}")
            
        if not reasons:
            reasons.append("Sentential structure matches known spam pattern templates")
    else:
        # Genuine
        if xai_metrics["lexical_diversity"] > 0.75:
            reasons.append("High vocabulary variety (indicates organic review)")
        
        genuine_words = [w for w, weight in active_features if weight < -0.2][:3]
        if genuine_words:
            reasons.append(f"Contains organic customer vocabulary: {', '.join(genuine_words)}")
            
        if not reasons:
            reasons.append("No suspicious spam signals or promotional patterns detected")
            
    return {
        "prediction": prediction,
        "confidence": round(confidence, 2),
        "reasons": reasons,
        "metrics": xai_metrics
    }
