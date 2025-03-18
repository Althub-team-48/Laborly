from fastapi import FastAPI
from app.utils.logger import setup_logging

# Initialize logging
setup_logging()

# Create FastAPI instance
app = FastAPI(
    title="Laborly API",
    description="API for the Laborly platform",
    version="0.1.0"
)

# Basic route to test the API
@app.get("/")
def read_root():
    return {"message": "Welcome to Laborly API"}

# Run the server using Uvicorn when executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
