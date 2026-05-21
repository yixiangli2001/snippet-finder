import os

# Set test environment variables before any module imports them.
# os.environ.setdefault only sets the value if it is not already present,
# so a real .env file will take precedence when running the actual server.
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-never-use-in-production!!")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
