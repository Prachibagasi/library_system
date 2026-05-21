from database import SessionLocal, engine, Base
import models
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def seed_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if db.query(models.User).count() == 0:
        admin = models.User(
            username="admin",
            email="admin@library.com",
            hashed_password=pwd_context.hash("admin123"),
            role="admin"
        )
        user1 = models.User(
            username="john",
            email="john@example.com",
            hashed_password=pwd_context.hash("password"),
            role="user"
        )
        db.add(admin)
        db.add(user1)

    if db.query(models.Book).count() == 0:
        books = [
            models.Book(title="The Hobbit", author="J.R.R. Tolkien", genre="Fantasy", description="A hobbit's journey.", total_copies=5, available_copies=5, cover_image_url="https://images.unsplash.com/photo-1618666012174-83b441c0bc76?w=400"),
            models.Book(title="Dune", author="Frank Herbert", genre="Sci-Fi", description="Spice must flow.", total_copies=3, available_copies=3, cover_image_url="https://images.unsplash.com/photo-1541963463532-d68292c34b19?w=400"),
            models.Book(title="1984", author="George Orwell", genre="Dystopian", description="Big Brother is watching.", total_copies=2, available_copies=2, cover_image_url="https://images.unsplash.com/photo-1512820790803-83ca734da794?w=400"),
            models.Book(title="Foundation", author="Isaac Asimov", genre="Sci-Fi", description="The fall of the galactic empire.", total_copies=4, available_copies=4, cover_image_url="https://images.unsplash.com/photo-1614728263952-84ea256f9679?w=400"),
            models.Book(title="Pride and Prejudice", author="Jane Austen", genre="Romance", description="A classic romance novel.", total_copies=3, available_copies=3, cover_image_url="https://images.unsplash.com/photo-1589829085413-56de8ae18c73?w=400")
        ]
        db.add_all(books)

    db.commit()
    db.close()
    print("Database seeded successfully.")

if __name__ == "__main__":
    seed_db()
