from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)

class Product(Base):
    __tablename__ = "products"

    product_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)
    
    reviews = relationship("Review", back_populates="product", cascade="all, delete-orphan")

class Review(Base):
    __tablename__ = "reviews"

    review_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False)
    review_text = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)
    prediction = Column(String(20), nullable=False)  # 'Genuine' or 'Fake'
    confidence = Column(Float, nullable=False)       # confidence score (e.g. 0.95)
    sentiment = Column(String(20), nullable=False)   # 'Positive', 'Neutral', 'Negative'
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="reviews")

class AnalysisHistory(Base):
    __tablename__ = "analysis_history"

    history_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    product_name = Column(String(255), nullable=False)
    total_reviews = Column(Integer, nullable=False)
    fake_reviews = Column(Integer, nullable=False)
    genuine_reviews = Column(Integer, nullable=False)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
