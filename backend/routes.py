import io
import csv
import openpyxl
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
import bcrypt
from jose import jwt, JWTError

from .database import get_db
from .models import User, Product, Review, AnalysisHistory
from .fake_review_model import predict_review
from .sentiment_analysis import analyze_sentiment
from .summarizer import summarize_reviews
from .advisor import generate_advisor_data

# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

router = APIRouter()

# JWT configuration
SECRET_KEY = "SUPER_SECRET_KEY_FOR_REVIEW_GUARD_AI_PROJECT"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 600  # Long expiration for easy project evaluation

from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)

def get_current_user(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided."
        )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        if email is None or user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token claims.")
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials.")
        
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    return user

# Helper functions
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Pydantic Schemas
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str

class ManualAnalysisRequest(BaseModel):
    product_name: str
    category: Optional[str] = "Electronics"
    reviews: List[str]

# API Endpoints

# --- AUTHENTICATION ---
@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered."
        )
    
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password=hash_password(user_data.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User registered successfully."}

@router.post("/auth/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user or not verify_password(user_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )
    
    token = create_access_token({"sub": user.email, "user_id": user.user_id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user.username
    }

# --- REVIEW ANALYSIS ---
@router.post("/analyze/manual")
def analyze_manual(
    request: ManualAnalysisRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not request.reviews:
        raise HTTPException(status_code=400, detail="Review list cannot be empty.")
        
    # Create product entry
    product = Product(product_name=request.product_name, category=request.category)
    db.add(product)
    db.commit()
    db.refresh(product)
    
    analyzed_reviews = []
    fake_count = 0
    genuine_count = 0
    
    for r_text in request.reviews:
        if not r_text.strip():
            continue
        # Run ML predictions
        pred_res = predict_review(r_text)
        sentiment = analyze_sentiment(r_text)
        
        pred_label = pred_res["prediction"]
        confidence = pred_res["confidence"]
        
        if pred_label == "Fake":
            fake_count += 1
        else:
            genuine_count += 1
            
        review_obj = Review(
            product_id=product.product_id,
            review_text=r_text,
            prediction=pred_label,
            confidence=confidence,
            sentiment=sentiment
        )
        db.add(review_obj)
        
        # Keep detailed response mapping
        analyzed_reviews.append({
            "review_text": r_text,
            "prediction": pred_label,
            "confidence": confidence,
            "sentiment": sentiment,
            "reasons": pred_res["reasons"],
            "metrics": pred_res["metrics"]
        })
        
    db.commit()
    
    # Run AI Summarization
    summary_res = summarize_reviews(analyzed_reviews)
    
    # Generate Scam Warning and AI Shopping Advisor data
    advisor_data = generate_advisor_data(request.product_name, analyzed_reviews)
    
    # Store in history
    history = AnalysisHistory(
        user_id=current_user.user_id,
        product_name=request.product_name,
        total_reviews=len(analyzed_reviews),
        fake_reviews=fake_count,
        genuine_reviews=genuine_count,
        summary=summary_res["short_summary"]
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    
    return {
        "history_id": history.history_id,
        "product_id": product.product_id,
        "product_name": product.product_name,
        "total_reviews": len(analyzed_reviews),
        "fake_reviews": fake_count,
        "genuine_reviews": genuine_count,
        "authenticity_score": round((genuine_count / len(analyzed_reviews)) * 100, 1) if analyzed_reviews else 0.0,
        "summary": summary_res,
        "reviews": analyzed_reviews,
        "scam_warning": advisor_data["scam_warning"],
        "advisor": advisor_data["advisor"]
    }

@router.post("/analyze/upload")
def analyze_upload(
    product_name: str = Form(...),
    category: str = Form("Electronics"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Read CSV contents
    try:
        contents = file.file.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV file: {e}")
        
    reviews_list = []
    # Identify CSV column
    text_col = None
    rating_col = None
    
    # Check headers (case insensitive)
    headers = reader.fieldnames if reader.fieldnames else []
    for h in headers:
        h_lower = h.lower()
        if "text" in h_lower or "review" in h_lower:
            text_col = h
        if "rating" in h_lower or "stars" in h_lower:
            rating_col = h
            
    # Default fallback to first column
    if not text_col and headers:
        text_col = headers[0]
        
    if not text_col:
        raise HTTPException(status_code=400, detail="No readable text column found in CSV.")
        
    # Read reviews
    for row in reader:
        text_val = row.get(text_col, "").strip()
        rating_val = 3
        if rating_col:
            try:
                rating_val = int(float(row.get(rating_col, 3)))
            except:
                pass
        if text_val:
            reviews_list.append((text_val, rating_val))
            
    if not reviews_list:
        raise HTTPException(status_code=400, detail="CSV file contains no records or empty reviews.")
        
    # Create product entry
    product = Product(product_name=product_name, category=category)
    db.add(product)
    db.commit()
    db.refresh(product)
    
    analyzed_reviews = []
    fake_count = 0
    genuine_count = 0
    
    for r_text, rating in reviews_list:
        pred_res = predict_review(r_text)
        sentiment = analyze_sentiment(r_text)
        
        pred_label = pred_res["prediction"]
        confidence = pred_res["confidence"]
        
        if pred_label == "Fake":
            fake_count += 1
        else:
            genuine_count += 1
            
        review_obj = Review(
            product_id=product.product_id,
            review_text=r_text,
            rating=rating,
            prediction=pred_label,
            confidence=confidence,
            sentiment=sentiment
        )
        db.add(review_obj)
        
        analyzed_reviews.append({
            "review_text": r_text,
            "rating": rating,
            "prediction": pred_label,
            "confidence": confidence,
            "sentiment": sentiment,
            "reasons": pred_res["reasons"],
            "metrics": pred_res["metrics"]
        })
        
    db.commit()
    
    # Run AI Summarization
    summary_res = summarize_reviews(analyzed_reviews)
    
    # Generate Scam Warning and AI Shopping Advisor data
    advisor_data = generate_advisor_data(product_name, analyzed_reviews)
    
    # Store in history
    history = AnalysisHistory(
        user_id=current_user.user_id,
        product_name=product_name,
        total_reviews=len(analyzed_reviews),
        fake_reviews=fake_count,
        genuine_reviews=genuine_count,
        summary=summary_res["short_summary"]
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    
    return {
        "history_id": history.history_id,
        "product_id": product.product_id,
        "product_name": product.product_name,
        "total_reviews": len(analyzed_reviews),
        "fake_reviews": fake_count,
        "genuine_reviews": genuine_count,
        "authenticity_score": round((genuine_count / len(analyzed_reviews)) * 100, 1) if analyzed_reviews else 0.0,
        "summary": summary_res,
        "reviews": analyzed_reviews,
        "scam_warning": advisor_data["scam_warning"],
        "advisor": advisor_data["advisor"]
    }

# --- HISTORY ---
@router.get("/history")
def get_history(
    search: Optional[str] = None, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(AnalysisHistory).filter(AnalysisHistory.user_id == current_user.user_id)
    if search:
        query = query.filter(AnalysisHistory.product_name.like(f"%{search}%"))
    history_items = query.order_by(AnalysisHistory.created_at.desc()).all()
    return history_items

@router.get("/history/{history_id}")
def get_history_detail(
    history_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    history = db.query(AnalysisHistory).filter(
        AnalysisHistory.history_id == history_id,
        AnalysisHistory.user_id == current_user.user_id
    ).first()
    if not history:
        raise HTTPException(status_code=404, detail="History record not found or access denied.")
        
    # Find matching product and reviews
    product = db.query(Product).filter(Product.product_name == history.product_name).order_by(Product.product_id.desc()).first()
    reviews = []
    if product:
        db_reviews = db.query(Review).filter(Review.product_id == product.product_id).all()
        for r in db_reviews:
            pred_res = predict_review(r.review_text)
            reviews.append({
                "review_text": r.review_text,
                "rating": r.rating,
                "prediction": r.prediction,
                "confidence": r.confidence,
                "sentiment": r.sentiment,
                "reasons": pred_res["reasons"],
                "metrics": pred_res["metrics"]
            })
            
    summary_res = summarize_reviews(reviews)
    
    # Generate Scam Warning and AI Shopping Advisor data
    advisor_data = generate_advisor_data(history.product_name, reviews)
    
    return {
        "history_id": history.history_id,
        "product_name": history.product_name,
        "total_reviews": history.total_reviews,
        "fake_reviews": history.fake_reviews,
        "genuine_reviews": history.genuine_reviews,
        "authenticity_score": round((history.genuine_reviews / history.total_reviews) * 100, 1) if history.total_reviews > 0 else 0.0,
        "summary": summary_res,
        "reviews": reviews,
        "scam_warning": advisor_data["scam_warning"],
        "advisor": advisor_data["advisor"],
        "created_at": history.created_at
    }

# --- REPORT GENERATION (PDF / CSV / EXCEL) ---
@router.get("/report/{history_id}/download")
def download_report(
    history_id: int, 
    format: str = "pdf", 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    history = db.query(AnalysisHistory).filter(
        AnalysisHistory.history_id == history_id,
        AnalysisHistory.user_id == current_user.user_id
    ).first()
    if not history:
        raise HTTPException(status_code=404, detail="History record not found or access denied.")
        
    product = db.query(Product).filter(Product.product_name == history.product_name).order_by(Product.product_id.desc()).first()
    db_reviews = []
    reviews = []
    if product:
        db_reviews = db.query(Review).filter(Review.product_id == product.product_id).all()
        for r in db_reviews:
            pred_res = predict_review(r.review_text)
            reviews.append({
                "review_text": r.review_text,
                "rating": r.rating,
                "prediction": r.prediction,
                "confidence": r.confidence,
                "sentiment": r.sentiment,
                "reasons": pred_res["reasons"],
                "metrics": pred_res["metrics"]
            })
    advisor_data = generate_advisor_data(history.product_name, reviews)
        
    # Output formats
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Review Text", "Rating", "Prediction", "Confidence", "Sentiment"])
        for r in db_reviews:
            writer.writerow([r.review_text, r.rating or "N/A", r.prediction, f"{int(r.confidence * 100)}%", r.sentiment])
        
        response = StreamingResponse(io.BytesIO(output.getvalue().encode("utf-8")), media_type="text/csv")
        response.headers["Content-Disposition"] = f"attachment; filename=reviewguard_{history_id}.csv"
        return response
        
    elif format == "excel":
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Review Analysis"
        
        # Summary Section
        ws.append(["ReviewGuard AI - Analysis Report"])
        ws.append(["Product Name", history.product_name])
        ws.append(["Total Reviews", history.total_reviews])
        ws.append(["Genuine Reviews", history.genuine_reviews])
        ws.append(["Fake Reviews", history.fake_reviews])
        ws.append(["Authenticity Score", f"{round((history.genuine_reviews / history.total_reviews) * 100, 1) if history.total_reviews > 0 else 0.0}%"])
        ws.append(["Scam Warning Level", advisor_data["scam_warning"]["risk_level"]])
        ws.append(["Scam Warning Message", advisor_data["scam_warning"]["warning_message"]])
        ws.append(["AI Advisor Verdict", advisor_data["advisor"]["verdict_title"]])
        ws.append(["AI Advisor Advice", advisor_data["advisor"]["buying_advice"]])
        ws.append(["AI Summary", history.summary])
        ws.append([])
        
        # Data Headers
        ws.append(["Review Text", "Rating", "Prediction", "Confidence", "Sentiment"])
        for r in db_reviews:
            ws.append([r.review_text, r.rating or "N/A", r.prediction, r.confidence, r.sentiment])
            
        file_stream = io.BytesIO()
        wb.save(file_stream)
        file_stream.seek(0)
        
        response = StreamingResponse(file_stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response.headers["Content-Disposition"] = f"attachment; filename=reviewguard_{history_id}.xlsx"
        return response
        
    elif format == "pdf":
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        story = []
        
        styles = getSampleStyleSheet()
        
        # Colors
        navy = colors.HexColor("#0F172A")
        blue = colors.HexColor("#2563EB")
        gray = colors.HexColor("#64748B")
        
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=24,
            leading=28,
            textColor=navy,
            spaceAfter=10
        )
        
        h2_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=16,
            leading=20,
            textColor=blue,
            spaceBefore=15,
            spaceAfter=10
        )
        
        body_style = styles['Normal']
        
        # Title
        story.append(Paragraph("ReviewGuard AI - Audit Report", title_style))
        story.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", body_style))
        story.append(Spacer(1, 15))
        
        # Scam Warning Alert in PDF
        scam_warning_level = advisor_data["scam_warning"]["risk_level"]
        scam_warning_msg = advisor_data["scam_warning"]["warning_message"]
        warning_color = colors.HexColor("#EF4444") if scam_warning_level == "HIGH RISK" else (colors.HexColor("#F59E0B") if scam_warning_level == "MODERATE RISK" else colors.HexColor("#10B981"))
        
        warning_style = ParagraphStyle(
            'WarningStyle',
            parent=styles['Normal'],
            textColor=colors.white,
            fontSize=10,
            leading=13,
            alignment=1 # centered
        )
        
        warning_table = Table([[Paragraph(f"<b>{scam_warning_level}:</b> {scam_warning_msg}", warning_style)]], colWidths=[500])
        warning_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), warning_color),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('PADDING', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(warning_table)
        story.append(Spacer(1, 15))
        
        # Metadata Table
        auth_score = f"{round((history.genuine_reviews / history.total_reviews) * 100, 1) if history.total_reviews > 0 else 0.0}%"
        meta_data = [
            [Paragraph("<b>Product Name:</b>", body_style), Paragraph(history.product_name, body_style)],
            [Paragraph("<b>Total Reviews:</b>", body_style), Paragraph(str(history.total_reviews), body_style)],
            [Paragraph("<b>Fake Reviews Flagged:</b>", body_style), Paragraph(f"{history.fake_reviews} ({round((history.fake_reviews/history.total_reviews)*100, 1) if history.total_reviews > 0 else 0.0}%)", body_style)],
            [Paragraph("<b>Authenticity Score:</b>", body_style), Paragraph(auth_score, body_style)]
        ]
        t = Table(meta_data, colWidths=[150, 350])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#E2E8F0")),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ('PADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(t)
        story.append(Spacer(1, 15))
        
        # AI Shopping Advisor Section in PDF
        story.append(Paragraph("AI Shopping Advisor (RAG + AI)", h2_style))
        advisor_verdict = advisor_data["advisor"]["verdict_title"]
        advisor_advice = advisor_data["advisor"]["buying_advice"]
        advisor_val = advisor_data["advisor"]["value_rating"]
        advisor_perf = advisor_data["advisor"]["performance_rating"]
        
        advisor_html = f"<b>Buying Verdict:</b> {advisor_verdict} | <b>Value Rating:</b> {advisor_val} | <b>Performance Index:</b> {advisor_perf}<br/><br/><b>Advisor Advice:</b> {advisor_advice}"
        story.append(Paragraph(advisor_html, body_style))
        
        if advisor_data["advisor"]["warnings"]:
            story.append(Spacer(1, 6))
            story.append(Paragraph("<b>Key Warnings & Alerts:</b>", body_style))
            for warn in advisor_data["advisor"]["warnings"]:
                story.append(Paragraph(f"• {warn}", body_style))
        story.append(Spacer(1, 15))
        
        # Summary Section
        story.append(Paragraph("AI-Generated Opinion Summary", h2_style))
        story.append(Paragraph(history.summary or "No summary available.", body_style))
        story.append(Spacer(1, 15))
        
        # Review Details Table
        story.append(Paragraph("Flagged Reviews Table", h2_style))
        
        # Table of reviews
        table_headers = [Paragraph("<b>Review Text</b>", body_style), Paragraph("<b>Sentiment</b>", body_style), Paragraph("<b>Prediction</b>", body_style), Paragraph("<b>Confidence</b>", body_style)]
        table_rows = [table_headers]
        
        for r in db_reviews[:15]: # Show first 15 reviews in PDF
            truncated_text = r.review_text[:120] + "..." if len(r.review_text) > 120 else r.review_text
            pred_color = "red" if r.prediction == "Fake" else "green"
            table_rows.append([
                Paragraph(truncated_text, body_style),
                Paragraph(r.sentiment, body_style),
                Paragraph(f"<font color='{pred_color}'><b>{r.prediction}</b></font>", body_style),
                Paragraph(f"{int(r.confidence * 100)}%", body_style)
            ])
            
        rt = Table(table_rows, colWidths=[280, 80, 80, 60])
        rt.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E2E8F0")),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#CBD5E1")),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(rt)
        
        if len(db_reviews) > 15:
            story.append(Spacer(1, 10))
            story.append(Paragraph(f"<i>* Showing top 15 out of {len(db_reviews)} reviews. Download CSV/Excel for full logs.</i>", body_style))
            
        doc.build(story)
        buffer.seek(0)
        
        response = StreamingResponse(buffer, media_type="application/pdf")
        response.headers["Content-Disposition"] = f"attachment; filename=reviewguard_{history_id}.pdf"
        return response
        
    else:
        raise HTTPException(status_code=400, detail="Invalid report format. Choose 'pdf', 'csv', or 'excel'.")
