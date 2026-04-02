import logging

from api.app import app

logging.basicConfig(level=logging.INFO)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
