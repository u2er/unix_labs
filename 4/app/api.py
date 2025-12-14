from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import pika
import json
import shutil
import time
import asyncio

from app.database import get_db, engine, Base
from app.models import User, Task
from app.app_logger import get_logger

Base.metadata.create_all(bind=engine)

logger = get_logger(__name__)
app = FastAPI()


SECRET_KEY = "fsefn-fafagefl93-falksebf-asbvey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid creds")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid creds")
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user



def send_task_id(task_id: int):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
    channel = connection.channel()
    channel.queue_declare(queue='summary_queue', durable=True)
    channel.basic_publish(
        exchange='',
        routing_key='summary_queue',
        body=json.dumps({"task_id": task_id}),
        properties=pika.BasicProperties(delivery_mode=2)
    )
    connection.close()


async def wait_for_task_result(task_id: int, db: Session, timeout: int = 120):
    start_time = time.time()
    while time.time() - start_time < timeout:
        task = db.query(Task).filter(Task.id == task_id).first()
        db.refresh(task)
        
        if task.status == "done":
            return task.result_text
        elif task.status == "error":
            raise HTTPException(status_code=500, detail=f"Processing failed: {task.result_text}")

        await asyncio.sleep(1)
        
    raise HTTPException(status_code=504, detail="Processing timeout")


@app.post("/register")
def register(username: str = Form(), password: str = Form(), api_key: str = Form(), db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    
    new_user = User(
        username=username, 
        password_hash=get_password_hash(password),
        gemini_api_key=api_key
    )
    db.add(new_user)
    db.commit()
    return {"message": "User created successfully"}


@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/summarize/youtube")
async def summarize_youtube(url: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_task = Task(
        user_id=current_user.id,
        type="youtube",
        source_data=url,
        status="pending"
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    send_task_id(new_task.id)
    logger.info(f"Queued YouTube task {new_task.id}")
    
    result = await wait_for_task_result(new_task.id, db)
    return {"summary": result}


@app.post("/summarize/file")
async def summarize_file(file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    file_location = f"temp/{file.filename}"
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)

    new_task = Task(
        user_id=current_user.id,
        type="file",
        source_data=file_location,
        status="pending"
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    send_task_id(new_task.id)
    logger.info(f"Queued File task {new_task.id}")

    result = await wait_for_task_result(new_task.id, db)
    return {"summary": result}