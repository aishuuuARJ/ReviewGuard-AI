import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer

# Safe download of NLTK resources
def download_nltk_resources():
    resources = ['stopwords', 'punkt', 'vader_lexicon']
    for res in resources:
        try:
            nltk.data.find(f'corpora/{res}' if res != 'vader_lexicon' else f'sentiment/{res}')
        except LookupError:
            try:
                nltk.download(res, quiet=True)
            except Exception as e:
                print(f"Warning: Failed to download NLTK resource {res}: {e}")

# Run downloader
download_nltk_resources()

# Initialize stemmer and stopwords list
stemmer = PorterStemmer()
try:
    stop_words = set(stopwords.words('english'))
except Exception:
    stop_words = set()

# Promotional words check (XAI Heuristics)
PROMO_KEYWORDS = [
    r"\bbuy\s+now\b", r"\bbest\s+product\b", r"\bdeal\b", r"\bcoupon\b", 
    r"\bdiscount\b", r"\bfree\b", r"\bguarantee\b", r"\brefund\b", 
    r"\bclick\s+here\b", r"\b100%\b", r"\bpromo\b", r"\bcode\b",
    r"\bget\s+yours\b", r"\bonly\s+\$\b", r"\bcheap\b", r"\binstant\b"
]

# ChatGPT / AI generated text patterns
AI_KEYWORDS = [
    r"\bexceeded\s+my\s+expectations\b",
    r"\brecently\s+purchased\b",
    r"\bdelivers\s+on\s+its\s+promise\b",
    r"\btestament\s+to\b",
    r"\bstandout\s+feature\b",
    r"\blook\s+no\s+further\b",
    r"\bnot\s+only\b.*\bbut\s+also\b",
    r"\bworth\s+every\s+penny\b",
    r"\bsolid\s+choice\b",
    r"\bflagship\s+device\b",
    r"\bseamless\b",
    r"\bphenomenal\b",
    r"\bhighly\s+recommend\b",
    r"\boverall,?\s+this\s+is\b",
    r"\bone\s+standout\b",
    r"\bbuild\s+quality\b",
    r"\blook\s+and\s+feel\b"
]

FORMAL_TRANSITIONS = [
    r"\bfurthermore\b", r"\bmoreover\b", r"\bconsequently\b",
    r"\btherefore\b", r"\bhowever\b", r"\badditionally\b",
    r"\bin\s+addition\b", r"\bnevertheless\b"
]

INFORMAL_INDICATORS = [
    r"\bdont\b", r"\bcant\b", r"\bwont\b", r"\bdidnt\b", r"\bshouldnt\b",
    r"\bcouldnt\b", r"\bim\b", r"\bive\b", r"\btbh\b", r"\bmeh\b",
    r"\blmao\b", r"\blol\b", r"\bomg\b", r"\bpls\b", r"\bthx\b", r"\bbro\b",
    r"\bgonna\b", r"\bwanna\b"
]

def clean_text(text: str) -> str:
    """
    Cleans raw review text for vectorization.
    """
    if not text:
        return ""
    # Lowercase
    text = text.lower()
    # Remove HTML tags/brackets
    text = re.sub(r'<[^>]+>', '', text)
    # Keep only alphabetical characters
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    # Tokenize
    words = text.split()
    # Filter stopwords and stem
    cleaned = [stemmer.stem(w) for w in words if w not in stop_words]
    return " ".join(cleaned)

def extract_xai_metrics(text: str) -> dict:
    """
    Extracts visual text features explaining why a review is predicted fake/genuine.
    """
    if not text:
        return {
            "exclamation_count": 0,
            "capitals_ratio": 0.0,
            "lexical_diversity": 1.0,
            "promotional_score": 0,
            "repeated_phrases_found": False,
            "caps_lock_detected": False,
            "excessive_punctuation": False,
            "text_length": 0
        }
    
    # Text length
    length = len(text)
    
    # Exclamation mark count
    exclamation_count = text.count("!")
    
    # Check for excessive punctuation (e.g. !!! or ???)
    excessive_punctuation = bool(re.search(r'!{2,}', text)) or (exclamation_count >= 3)
    
    # Capitals ratio
    letters = re.sub(r'[^a-zA-Z]', '', text)
    uppercase = re.sub(r'[^A-Z]', '', text)
    capitals_ratio = len(uppercase) / len(letters) if len(letters) > 0 else 0.0
    caps_lock_detected = capitals_ratio > 0.35 and len(text) > 15
    
    # Lexical diversity (repetition)
    words = text.lower().split()
    unique_words = set(words)
    lexical_diversity = len(unique_words) / len(words) if len(words) > 0 else 1.0
    repeated_phrases_found = lexical_diversity < 0.65 and len(words) > 8
    
    # Promotional score
    promotional_score = 0
    for pattern in PROMO_KEYWORDS:
        if re.search(pattern, text, re.IGNORECASE):
            promotional_score += 1
            
    # AI Score Calculation
    ai_score = 0.0
    for pattern in AI_KEYWORDS:
        if re.search(pattern, text, re.IGNORECASE):
            ai_score += 1.5
            
    for pattern in FORMAL_TRANSITIONS:
        if re.search(pattern, text, re.IGNORECASE):
            ai_score += 1.0
            
    # Penalize for informal human markers (AI never writes like this)
    for pattern in INFORMAL_INDICATORS:
        if re.search(pattern, text, re.IGNORECASE):
            ai_score -= 1.5
            
    # Check for lowercase 'i' as standalone word
    if re.search(r'\bi\b', text):
        ai_score -= 2.0

    # Ensure score is not negative
    ai_score = max(0.0, ai_score)
    ai_patterns_detected = ai_score >= 2.5 and len(words) > 10
            
    return {
        "exclamation_count": exclamation_count,
        "capitals_ratio": round(capitals_ratio, 2),
        "lexical_diversity": round(lexical_diversity, 2),
        "promotional_score": promotional_score,
        "repeated_phrases_found": repeated_phrases_found,
        "caps_lock_detected": caps_lock_detected,
        "excessive_punctuation": excessive_punctuation,
        "text_length": length,
        "ai_score": round(ai_score, 2),
        "ai_patterns_detected": ai_patterns_detected
    }
