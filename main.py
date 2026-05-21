from fastapi import FastAPI, Depends, HTTPException, status, Request, Form, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import timedelta, date
import models, schemas, database, auth
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def get_current_user_from_cookie(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        if token.startswith("Bearer "):
            token = token[7:]
        payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        user = db.query(models.User).filter(models.User.username == username).first()
        return user
    except auth.JWTError:
        return None

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, q: str = None, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if q:
        books = db.query(models.Book).filter(
            (models.Book.title.like(f"%{q}%")) |
            (models.Book.author.like(f"%{q}%")) |
            (models.Book.genre.like(f"%{q}%"))
        ).all()
    else:
        books = db.query(models.Book).all()
    return templates.TemplateResponse(request=request, name="search.html", context={"request": request, "books": books, "user": user, "q": q})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={"request": request})

@app.post("/login")
async def login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not auth.verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"request": request, "error": "Incorrect username or password"}
        )
    
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html", context={"request": request, "error": None})

@app.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    # Validate passwords match
    if password != confirm_password:
        return templates.TemplateResponse(request=request, name="register.html", context={"request": request, "error": "Passwords do not match."})
    
    # Check if username already exists
    existing_user = db.query(models.User).filter(models.User.username == username).first()
    if existing_user:
        return templates.TemplateResponse(request=request, name="register.html", context={"request": request, "error": "Username already taken."})
    
    # Check if email already exists
    existing_email = db.query(models.User).filter(models.User.email == email).first()
    if existing_email:
        return templates.TemplateResponse(request=request, name="register.html", context={"request": request, "error": "Email already registered."})
    
    # Create the new user
    new_user = models.User(
        username=username,
        email=email,
        hashed_password=auth.get_password_hash(password),
        role="user"
    )
    db.add(new_user)
    db.commit()
    
    # Auto-login after registration
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": new_user.username}, expires_delta=access_token_expires
    )
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response

@app.get("/logout")
async def logout(response: Response):
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("access_token")
    return response

@app.get("/book/{book_id}", response_class=HTMLResponse)
async def book_detail(request: Request, book_id: int, db: Session = Depends(get_db)):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    user = get_current_user_from_cookie(request, db)
    
    # Fetch similar books (same genre or author, excluding current book)
    similar_books = db.query(models.Book).filter(
        models.Book.id != book_id,
        (models.Book.genre == book.genre) | (models.Book.author == book.author)
    ).limit(3).all()
    
    # If not enough similar books, get some other books
    if len(similar_books) < 3:
        needed = 3 - len(similar_books)
        exclude_ids = [book.id] + [sb.id for sb in similar_books]
        extra_books = db.query(models.Book).filter(models.Book.id.notin_(exclude_ids)).limit(needed).all()
        similar_books.extend(extra_books)
        
    return templates.TemplateResponse(
        request=request, 
        name="book_detail.html", 
        context={"request": request, "book": book, "user": user, "similar_books": similar_books}
    )

@app.post("/borrow/{book_id}")
async def borrow_book(request: Request, book_id: int, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book or book.available_copies <= 0:
        raise HTTPException(status_code=400, detail="Book not available")
    
    existing_borrow = db.query(models.BorrowHistory).filter(models.BorrowHistory.user_id == user.id, models.BorrowHistory.book_id == book.id, models.BorrowHistory.return_date == None).first()
    if existing_borrow:
        raise HTTPException(status_code=400, detail="You have already borrowed this book")
    
    book.available_copies -= 1
    new_borrow = models.BorrowHistory(user_id=user.id, book_id=book.id, borrow_date=date.today())
    db.add(new_borrow)
    db.commit()
    
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)

@app.post("/return/{history_id}")
async def return_book(request: Request, history_id: int, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    borrow_record = db.query(models.BorrowHistory).filter(models.BorrowHistory.id == history_id, models.BorrowHistory.user_id == user.id).first()
    if not borrow_record or borrow_record.return_date is not None:
        raise HTTPException(status_code=400, detail="Invalid return request")
    
    borrow_record.return_date = date.today()
    book = db.query(models.Book).filter(models.Book.id == borrow_record.book_id).first()
    if book:
        book.available_copies += 1
        
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)

from ai_recommendation import get_recommendations

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    borrowed_books = db.query(models.BorrowHistory).filter(models.BorrowHistory.user_id == user.id, models.BorrowHistory.return_date == None).all()
    
    # Get user history titles
    history_titles = [h.book.title for h in db.query(models.BorrowHistory).filter(models.BorrowHistory.user_id == user.id).all()]
    
    # Get available catalog
    all_books = db.query(models.Book).filter(models.Book.available_copies > 0).all()
    catalog_data = [{"title": b.title, "author": b.author, "genre": b.genre} for b in all_books]
    
    recommendations = get_recommendations(history_titles, catalog_data)
    
    return templates.TemplateResponse(request=request, name="user_dashboard.html", context={"request": request, "user": user, "borrowed_books": borrowed_books, "recommendations": recommendations})

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user or user.role != "admin":
        return RedirectResponse(url="/")
    
    books = db.query(models.Book).all()
    return templates.TemplateResponse(request=request, name="admin.html", context={"request": request, "user": user, "books": books})

@app.post("/admin/add_book")
async def admin_add_book(
    request: Request, 
    title: str = Form(...), 
    author: str = Form(...), 
    genre: str = Form(...), 
    description: str = Form(None), 
    total_copies: int = Form(...), 
    cover_image_url: str = Form(None), 
    db: Session = Depends(get_db)
):
    user = get_current_user_from_cookie(request, db)
    if not user or user.role != "admin":
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    new_book = models.Book(
        title=title, 
        author=author, 
        genre=genre, 
        description=description, 
        total_copies=total_copies, 
        available_copies=total_copies, 
        cover_image_url=cover_image_url
    )
    db.add(new_book)
    db.commit()
    
    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
