"""
WSGI entry point for production deployment
"""
from api_server import app

if __name__ == "__main__":
    app.run()
