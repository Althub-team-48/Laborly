from app.database.config import Base, engine

def init_db():
    # Create all tables defined in the models
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()