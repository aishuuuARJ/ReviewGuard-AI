import os
import re
import json
import urllib.request
import urllib.error
from typing import List, Dict

# Aspect categories for RAG extraction
ASPECTS = {
    "battery": ["battery", "charge", "charging", "drain", "power", "backup"],
    "performance": ["performance", "speed", "fast", "slow", "lag", "hang", "processor", "ram"],
    "camera": ["camera", "photo", "video", "lens", "picture", "megapixels"],
    "display": ["screen", "display", "resolution", "brightness", "panel", "amoled"],
    "value": ["price", "cost", "money", "worth", "expensive", "cheap", "value"],
    "quality": ["quality", "build", "material", "durability", "sturdy", "robust"]
}

def split_sentences(text: str) -> List[str]:
    """Helper to split text into sentences."""
    if not text:
        return []
    # Split by standard sentence terminators
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if len(s.strip()) > 8]

def retrieve_aspect_evidence(reviews: List[Dict], sentiment_filter: str = None) -> Dict[str, List[str]]:
    """
    RAG Helper: Retrieves sentences from reviews matching different product aspects.
    Filters by sentiment if provided ('Positive', 'Negative', 'Neutral').
    """
    evidence = {aspect: [] for aspect in ASPECTS}
    
    for r in reviews:
        # If sentiment filter is set, verify
        if sentiment_filter and r.get("sentiment") != sentiment_filter:
            continue
            
        sentences = split_sentences(r.get("review_text", ""))
        for sentence in sentences:
            sentence_lower = sentence.lower()
            for aspect, keywords in ASPECTS.items():
                if any(kw in sentence_lower for kw in keywords):
                    # Avoid duplicates and restrict size
                    if sentence not in evidence[aspect] and len(evidence[aspect]) < 3:
                        evidence[aspect].append(sentence)
                        
    return evidence

def run_gemini_api(prompt: str, api_key: str) -> str:
    """Calls Google Gemini API using urllib."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=8) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"Gemini API invocation failed: {e}")
        return ""

def run_openai_api(prompt: str, api_key: str) -> str:
    """Calls OpenAI API using urllib."""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are ReviewGuard AI, a smart shopping assistant. Generate shopping advice in JSON format."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"}
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=8) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"OpenAI API invocation failed: {e}")
        return ""

def generate_advisor_data(product_name: str, reviews: List[Dict]) -> Dict:
    """
    Analyzes reviews, calculates scam warning levels, and retrieves RAG-based 
    shopping advice utilizing local synthesis or Gemini/OpenAI if API keys are set.
    """
    total = len(reviews)
    if total == 0:
        return {
            "scam_warning": {
                "risk_level": "LOW RISK",
                "color": "success",
                "warning_message": "No reviews analyzed yet.",
                "details": []
            },
            "advisor": {
                "verdict_title": "No Recommendation",
                "verdict": "neutral",
                "buying_advice": "Please input customer reviews to run the shopping assistant advisor.",
                "warnings": ["Insufficient review volume to evaluate product reliability."],
                "value_rating": "N/A",
                "performance_rating": "N/A",
                "evidence": []
            }
        }

    # 1. Compute Authenticity & Risk
    fake_reviews = [r for r in reviews if r.get("prediction") == "Fake"]
    genuine_reviews = [r for r in reviews if r.get("prediction") == "Genuine"]
    fake_count = len(fake_reviews)
    genuine_count = len(genuine_reviews)
    
    authenticity_score = (genuine_count / total) * 100
    
    # Analyze warnings from fake reviews
    warning_details = []
    has_shouting = any(r.get("metrics", {}).get("caps_lock_detected") for r in fake_reviews)
    has_excessive_punct = any(r.get("metrics", {}).get("excessive_punctuation") for r in fake_reviews)
    has_ai_patterns = any(r.get("metrics", {}).get("ai_patterns_detected") for r in fake_reviews)
    
    if has_shouting:
        warning_details.append("Detected reviews in ALL-CAPS (shouting/promotional tone).")
    if has_excessive_punct:
        warning_details.append("Detected reviews with suspicious repetitive punctuation (e.g., !!!).")
    if has_ai_patterns:
        warning_details.append("AI-style language patterns matched (e.g. ChatGPT templates).")
    if fake_count > 0:
        warning_details.append(f"Flagged {fake_count} reviews as fake/promotional spam.")

    if authenticity_score < 50:
        risk_level = "HIGH RISK"
        color = "danger"
        warning_message = "CRITICAL: The majority of reviews on this product are simulated, highly promotional, or bot-generated. Proceed with extreme caution."
    elif authenticity_score < 75:
        risk_level = "MODERATE RISK"
        color = "warning"
        warning_message = "CAUTION: Suspicious activity detected. Several reviews contain promotional keywords or match AI templates."
    else:
        risk_level = "LOW RISK"
        color = "success"
        warning_message = "SAFE: Reviews exhibit healthy organic vocabulary variety, natural sentence structures, and standard customer feedback."
        warning_details = ["No suspicious anomalies or promotional bot reviews detected."]

    # 2. Extract Evidence using RAG
    positive_evidence = retrieve_aspect_evidence(genuine_reviews, "Positive")
    negative_evidence = retrieve_aspect_evidence(genuine_reviews, "Negative")
    
    # Collect some real quotes to show as evidence
    evidence_sentences = []
    for aspect in ASPECTS:
        if positive_evidence[aspect]:
            evidence_sentences.append(f"Genuine Pro: \"{positive_evidence[aspect][0]}\"")
        if negative_evidence[aspect]:
            evidence_sentences.append(f"Genuine Con: \"{negative_evidence[aspect][0]}\"")
            
    # Restrict total evidence items shown
    evidence_sentences = evidence_sentences[:4]
    
    # 3. Check for API Keys
    gemini_key = os.environ.get("GEMINI_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    
    # Prompt construction
    prompt = f"""
    Analyze the customer reviews for the product: "{product_name}".
    Here is some context:
    - Total reviews analyzed: {total}
    - Authenticity Score: {authenticity_score:.1f}% (percentage of genuine organic reviews)
    - Flagged fake reviews: {fake_count}
    - Real positive feedback quotes: {json.dumps(positive_evidence)}
    - Real negative feedback quotes: {json.dumps(negative_evidence)}
    
    Generate buying advice for a customer. Respond ONLY in valid JSON format matching this schema:
    {{
        "verdict_title": "Highly Recommended" | "Proceed with Caution" | "Not Recommended",
        "verdict": "buy" | "caution" | "avoid",
        "buying_advice": "Detailed, paragraph-long shopping advice highlighting product strength vs flaws based on reviews",
        "warnings": ["warning bullet 1", "warning bullet 2"],
        "value_rating": "High" | "Medium" | "Low",
        "performance_rating": "Excellent" | "Average" | "Poor"
    }}
    Do not add markdown formatting or backticks around the JSON.
    """

    advisor_res = None
    if gemini_key:
        raw_res = run_gemini_api(prompt, gemini_key)
        # Clean potential markdown output
        raw_res = re.sub(r"```json\s*", "", raw_res)
        raw_res = re.sub(r"\s*```", "", raw_res)
        try:
            advisor_res = json.loads(raw_res.strip())
        except Exception:
            pass
            
    if not advisor_res and openai_key:
        raw_res = run_openai_api(prompt, openai_key)
        raw_res = re.sub(r"```json\s*", "", raw_res)
        raw_res = re.sub(r"\s*```", "", raw_res)
        try:
            advisor_res = json.loads(raw_res.strip())
        except Exception:
            pass

    # 4. Fallback to Local RAG Synthesis if API fails or no key
    if not advisor_res:
        # Determine Ratings
        pos_aspects = [a for a, list_s in positive_evidence.items() if len(list_s) > 0]
        neg_aspects = [a for a, list_s in negative_evidence.items() if len(list_s) > 0]
        
        value_rating = "High" if "value" in pos_aspects else ("Low" if "value" in neg_aspects else "Medium")
        perf_rating = "Excellent" if "performance" in pos_aspects else ("Poor" if "performance" in neg_aspects else "Average")
        
        # Verdict logic
        if authenticity_score >= 75:
            if len(positive_evidence.get("quality", [])) > 0 or len(positive_evidence.get("performance", [])) > 0:
                verdict_title = "Highly Recommended"
                verdict = "buy"
                advice = f"The {product_name} is a solid buy based on organic consumer reviews. Buyers express high satisfaction with its core capabilities (particularly {', '.join(pos_aspects[:2]) or 'overall design'}). The reviews are highly authentic and free from bot manipulation."
            else:
                verdict_title = "Recommended"
                verdict = "buy"
                advice = f"The {product_name} is recommended for general use. Genuine customers note satisfactory performance. The reviews are highly authentic with low risk of manipulation."
            warnings_list = ["Compare prices with local retailers for the best deal."]
        elif authenticity_score >= 50:
            verdict_title = "Proceed with Caution"
            verdict = "caution"
            advice = f"The review data for {product_name} is mixed, with some indicators of review manipulation. Genuine buyers highlight quality features, but also flag complaints regarding {', '.join(neg_aspects[:2]) or 'reliability'}. Research alternatives before buying."
            warnings_list = [f"Spam indicators flagged in {fake_count} reviews.", "Some reviews appear AI-generated."]
        else:
            verdict_title = "Not Recommended"
            verdict = "avoid"
            advice = f"We advise against buying the {product_name} based on this listing. Over {100 - authenticity_score:.1f}% of reviews are flagged as fake, suspicious, or promotional spam. The organic reviews indicate critical issues and the product rating is artificially inflated."
            warnings_list = ["High risk of review manipulation.", "Vast majority of reviews are fake.", "Organic reviews suggest quality issues."]

        # Enrich local warnings list with aspect specific ones
        if len(negative_evidence.get("battery", [])) > 0:
            warnings_list.append("Genuine buyers report fast battery drainage.")
        if len(negative_evidence.get("quality", [])) > 0:
            warnings_list.append("Some complaints about long-term build durability.")
        if len(negative_evidence.get("value", [])) > 0:
            warnings_list.append("A few organic buyers mention it feels overpriced.")

        advisor_res = {
            "verdict_title": verdict_title,
            "verdict": verdict,
            "buying_advice": advice,
            "warnings": warnings_list[:3],
            "value_rating": value_rating,
            "performance_rating": perf_rating
        }

    # Inject retrieved RAG evidence into advisor response
    advisor_res["evidence"] = evidence_sentences

    return {
        "scam_warning": {
            "risk_level": risk_level,
            "color": color,
            "warning_message": warning_message,
            "details": warning_details
        },
        "advisor": advisor_res
    }
