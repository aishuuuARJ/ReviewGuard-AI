import os
import sys
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

# Add current folder to path to enable local imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.preprocessing import clean_text
from backend.fake_review_model import save_model

def train_default():
    print("Generating training dataset for ReviewGuard AI...")
    
    # Synthetic dataset of e-commerce reviews for training
    # 0 = Genuine, 1 = Fake
    dataset = [
        # Genuine Reviews (0)
        ("Amazing battery life and camera quality. Highly recommended for daily use.", 0),
        ("Very satisfied with the performance. The display is bright and beautiful.", 0),
        ("Decent product. The build is premium but charging is slightly slow.", 0),
        ("Average speakers and the UI lags occasionally, but the camera is great.", 0),
        ("The phone heats up a bit during fast charging, but otherwise it works fine.", 0),
        ("Good value for money. Not the best phone in the world, but solid for the price.", 0),
        ("Excellent packaging and delivery. The device runs smooth and screen is perfect.", 0),
        ("The sound quality is crisp and clear, but the battery drains fast on gaming.", 0),
        ("Been using it for a week, screen quality is nice but the plastic back feels cheap.", 0),
        ("I had a small issue with the software update, but tech support resolved it quickly.", 0),
        ("Decent camera, good screen resolution, but the price is too high for these specs.", 0),
        ("Overall nice product, screen looks great and battery easily lasts all day.", 0),
        ("Perfect size for single hand use. Lightweight and battery back up is awesome.", 0),
        ("Decent performance, not a gaming phone but works well for social media.", 0),
        ("A bit disappointed with low light photography, but daytime shots are clean.", 0),
        ("Satisfied. The performance is smooth and calls are clear. No heating issues.", 0),
        ("Very good display panel and UI is neat. The fingerprint sensor is super fast.", 0),
        ("Camera is average, battery is average, but build quality is strong.", 0),
        ("I bought this for my father. He loves the battery backup and simple UI.", 0),
        ("Nice and compact. The audio is clear, but charging takes almost two hours.", 0),
        ("the screen is really cool but battery backup is bad imo, drains within 5 hours of use.", 0),
        ("cant complain much for this price, screen is nice and speaker is loud enough.", 0),
        ("its ok i guess. not the fastest but works. display is bright.", 0),
        ("good sound quality but design looks very cheap and plastic. ok battery.", 0),
        ("delivered fast. box was damaged but phone is safe. camera takes good daylight shots.", 0),
        ("software has some bugs, hope update fixes it. camera is awesome though.", 0),
        ("average battery, average screen, nothing fancy. ok for daily routine.", 0),
        ("really love the display colors, but speaker sound lacks bass.", 0),
        
        # Fake / Spam / AI-Generated Reviews (1)
        ("Best phone in the world!!! Buy now!!! Promo code DISCOUNT99!!!", 1),
        ("AMAZING PRODUCT!!! Click here to get a 100% refund. Best discount now!", 1),
        ("BUY NOW OR REGRET LATER!!! BEST QUALITY GUARANTEED!!! CHEAP PRICE!!!", 1),
        ("Best product ever!!! Buy now!!! Best phone in the world!!! Buy now!!!", 1),
        ("100% FREE GIFT inside! Click link to claim your reward. Safe and secure deal!", 1),
        ("Excellent purchase! Click here for refund instructions and discounts.", 1),
        ("Amazing price and deal of the day! Get your code at WWW.DEALS.COM now!", 1),
        ("Best quality and fast delivery. Make money working from home! Click here!", 1),
        ("This is the best product in the universe. Buy now for instant discount!!!", 1),
        ("PROMO DEAL!!! 100% SATISFACTION GUARANTEED OR CASH REFUND!!!", 1),
        ("Best phone ever. Click this link to get your free gift voucher today!!!", 1),
        ("AMAZING!!! CHEAPEST PRICE ON AMAZON!!! BUY HERE NOW FOR EXTRA VOUCHER!!!", 1),
        ("Guaranteed cash back. Make fast money online. Highly recommended promo link.", 1),
        ("Best product ever! Best product ever! Best product ever! Buy now!!!", 1),
        ("INCREDIBLE DISCOUNT! Instant cashback. Best item ever. Click now!", 1),
        ("Buy today and get 100% free shipping and a free bonus cover. Click here!", 1),
        ("Best deal of the year. Coupon code inside. Free shipping. Highly recommended!!!", 1),
        ("This changed my life! Best purchase ever. Get yours cheap on this site!", 1),
        ("Win a free iPhone! Just click the link and register. 100% legit deal!", 1),
        ("Amazing discounts available. Cheap price code coupon. Click link to buy now!!!", 1),
        ("I recently purchased this product, and I must say it has exceeded my expectations in every possible way. The performance is outstanding and the design is sleek.", 1),
        ("As someone who has tried multiple items, this standout device delivers on its promise. Not only is it fast, but the build quality is also phenomenal. Highly recommend.", 1),
        ("This flagship device represents a testament to modern engineering. Overall, this is a solid choice and worth every single penny. Look no further.", 1),
        ("I was excited to receive this item, but unfortunately, it has failed to deliver on its promise. Lackluster display and disappointing battery life. Highly recommend looking elsewhere.", 1),
        ("Furthermore, the user experience is incredibly seamless. I am thoroughly impressed by its sleek look and feel, making it an excellent flagship companion.", 1),
        ("In terms of performance, it truly stands out. A solid choice for anyone seeking a premium and reliable solution. Outstanding and highly recommended.", 1),
        ("I recently bought this product and overall, it is a solid choice. The battery backup is phenomenal, though one standout issue is the slightly long charging time.", 1),
        ("Moreover, the screen display is a testament to quality. Sleek design combined with stellar responsiveness. Highly recommend this amazing flagship.", 1)
    ]
    
    # Preprocess texts
    texts = [clean_text(item[0]) for item in dataset]
    labels = [item[1] for item in dataset]
    
    # Vectorize text using TF-IDF
    vectorizer = TfidfVectorizer(max_features=500, ngram_range=(1, 2))
    X = vectorizer.fit_transform(texts)
    
    # Train Logistic Regression model
    model = LogisticRegression(C=1.0)
    model.fit(X, labels)
    
    # Save files
    save_model(model, vectorizer)
    print("Default model training complete! Loaded and saved to disk.")

if __name__ == "__main__":
    train_default()
