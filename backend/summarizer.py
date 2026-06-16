import re
from collections import Counter
from typing import List, Dict

# Standard e-commerce product aspects
ASPECTS = [
    "battery", "camera", "screen", "display", "performance", "speed", "heating", "charge", 
    "speaker", "sound", "price", "cost", "design", "look", "quality", "service", "software"
]

def split_into_sentences(text: str) -> List[str]:
    """
    Splits text into individual sentences.
    """
    if not text:
        return []
    # Simple regex split by punctuation
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if len(s.strip()) > 8]

def extract_aspect_keywords(sentences: List[str]) -> List[str]:
    """
    Identifies which aspects are most talked about.
    """
    found_aspects = []
    for s in sentences:
        s_lower = s.lower()
        for aspect in ASPECTS:
            if aspect in s_lower:
                found_aspects.append(aspect)
    counts = Counter(found_aspects)
    return [item[0] for item in counts.most_common(3)]

def summarize_reviews(reviews: List[Dict]) -> Dict:
    """
    Generates a structured summary from a list of reviews.
    Each review dict should contain: {'review_text': str, 'sentiment': str, 'prediction': str}
    """
    # Filter only Genuine reviews for summarization
    genuine_reviews = [r for r in reviews if r.get("prediction", "Genuine") == "Genuine"]
    
    if not genuine_reviews:
        return {
            "short_summary": "No genuine reviews available to summarize.",
            "pros": ["No clear pros identified."],
            "cons": ["No clear cons identified."],
            "recommendation": "Neutral / Insufficient Data"
        }
        
    total_genuine = len(genuine_reviews)
    positive_reviews = [r for r in genuine_reviews if r.get("sentiment") == "Positive"]
    negative_reviews = [r for r in genuine_reviews if r.get("sentiment") == "Negative"]
    neutral_reviews = [r for r in genuine_reviews if r.get("sentiment") == "Neutral"]
    
    # Calculate ratios
    pos_ratio = len(positive_reviews) / total_genuine if total_genuine > 0 else 0.0
    neg_ratio = len(negative_reviews) / total_genuine if total_genuine > 0 else 0.0
    
    # Extract sentences
    all_pos_sentences = []
    for r in positive_reviews:
        all_pos_sentences.extend(split_into_sentences(r["review_text"]))
        
    all_neg_sentences = []
    for r in negative_reviews:
        all_neg_sentences.extend(split_into_sentences(r["review_text"]))
        
    # Get keywords for summary synthesis
    pos_aspects = extract_aspect_keywords(all_pos_sentences)
    neg_aspects = extract_aspect_keywords(all_neg_sentences)
    
    # Select best Pros (up to 3)
    # Simple score based on sentence length and aspect keywords
    def score_sentence(s, aspects):
        score = 0
        s_lower = s.lower()
        for aspect in aspects:
            if aspect in s_lower:
                score += 3
        # Penalize overly long sentences
        if 15 < len(s) < 80:
            score += 2
        elif len(s) >= 80:
            score += 1
        return score

    # Select Pros
    pro_candidates = list(set(all_pos_sentences))
    pro_candidates.sort(key=lambda s: score_sentence(s, pos_aspects), reverse=True)
    pros = pro_candidates[:3]
    if not pros:
        # Fallback to general review if no sentences extracted
        pros = [r["review_text"] for r in positive_reviews[:2]] if positive_reviews else ["No positive features highlighted yet."]
        
    # Select Cons
    con_candidates = list(set(all_neg_sentences))
    con_candidates.sort(key=lambda s: score_sentence(s, neg_aspects), reverse=True)
    cons = con_candidates[:3]
    if not cons:
        cons = [r["review_text"] for r in negative_reviews[:2]] if negative_reviews else ["No negative features reported."]
        
    # Clean pros/cons prefixes (remove any existing bullet points)
    pros = [re.sub(r'^[-\*\d\.\s\u2714]+', '', p).strip() for p in pros]
    cons = [re.sub(r'^[-\*\d\.\s\u2716\u2717]+', '', c).strip() for c in cons]
    
    # Synthesize short summary
    if len(positive_reviews) > len(negative_reviews):
        pro_terms = f"especially its {', '.join(pos_aspects)}" if pos_aspects else "its performance and features"
        con_terms = f"some users noted complaints about {', '.join(neg_aspects)}" if neg_aspects else "few complaints were filed"
        short_summary = f"Overall, customer feedback is highly positive. Buyers praise the product, {pro_terms}. On the downside, {con_terms}."
    elif len(negative_reviews) > len(positive_reviews):
        con_terms = f"particularly regarding {', '.join(neg_aspects)}" if neg_aspects else "its overall functionality"
        pro_terms = f"others still appreciated the {', '.join(pos_aspects)}" if pos_aspects else "some features"
        short_summary = f"The feedback indicates general dissatisfaction, {con_terms}. However, {pro_terms}."
    else:
        short_summary = "Customer feedback is mixed or largely neutral. Opinions are divided between minor utility issues and average performance satisfaction."
        
    # Determine recommendation
    if pos_ratio >= 0.70:
        recommendation = "Highly Recommended"
    elif pos_ratio >= 0.45:
        recommendation = "Recommended"
    elif pos_ratio >= 0.25:
        recommendation = "Recommended with Reservations"
    else:
        recommendation = "Not Recommended"
        
    return {
        "short_summary": short_summary,
        "pros": pros,
        "cons": cons,
        "recommendation": recommendation
    }
