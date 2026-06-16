from nltk.sentiment.vader import SentimentIntensityAnalyzer

_analyzer = None

def get_analyzer():
    global _analyzer
    if _analyzer is None:
        try:
            _analyzer = SentimentIntensityAnalyzer()
        except Exception:
            # Fallback if VADER lexicon is missing/failed to load
            import nltk
            nltk.download('vader_lexicon', quiet=True)
            _analyzer = SentimentIntensityAnalyzer()
    return _analyzer

def analyze_sentiment(text: str) -> str:
    """
    Analyzes text and returns 'Positive', 'Neutral', or 'Negative'.
    """
    if not text or not text.strip():
        return "Neutral"
        
    try:
        analyzer = get_analyzer()
        scores = analyzer.polarity_scores(text)
        compound = scores["compound"]
        
        if compound >= 0.05:
            return "Positive"
        elif compound <= -0.05:
            return "Negative"
        else:
            return "Neutral"
    except Exception as e:
        print(f"Error in sentiment analysis: {e}. Falling back to default.")
        # Super simple rule-based fallback if VADER fails
        text_lower = text.lower()
        pos_words = ["good", "great", "excellent", "love", "best", "satisfied", "amazing", "awesome", "perfect"]
        neg_words = ["bad", "worst", "hate", "terrible", "poor", "heating", "broken", "waste", "disappointed"]
        
        pos_count = sum(text_lower.count(w) for w in pos_words)
        neg_count = sum(text_lower.count(w) for w in neg_words)
        
        if pos_count > neg_count:
            return "Positive"
        elif neg_count > pos_count:
            return "Negative"
        else:
            return "Neutral"
