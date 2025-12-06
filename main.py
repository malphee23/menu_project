import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

#python main.py - для запуска локального сайта в терминале PyCharm или cmd
#http://127.0.0.1:8000/docs - интерактивная документация
#Ip и порт будет показан в терминале или cmd

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


@app.get(
    "/books",
    tags=["Книги"],
    summary="Получиться все книги"
)
def read_books():
    return books

@app.get(
    "/books/{book_id}",
    tags=["Книги"],
    summary="Получить книгу"
)
def get_book(book_id: int):
    for book in books:
        if book["id"] == book_id:
            return book
        raise HTTPException(status_code=404, detail="Book not found")
    return None


class NewBook(BaseModel):
    title: str
    author: str

@app.post(
    "/books",
    tags=["Добавление"],
    summary="Добавить книгу"
)
def create_book(new_book: NewBook):
    books.append({
            "id": len(books) + 1,
            "title": new_book.title,
            "author": new_book.author,
        })
    return {"success": True}


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)