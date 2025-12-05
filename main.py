import uvicorn
from fastapi import FastAPI

app = FastAPI()

#python main.py - для запуска в терминале или cmd
#http://127.0.0.1:8000/docs - интерактивная документация

books = [
    {
        "id": 1,
        "title": "Python Programming",
        "author": "Egor",
    },
    {
        "id": 2,
        "title": "Lol",
        "author": "Vova",
    }
]


@app.get("/books")

def read_books():
    return books

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)