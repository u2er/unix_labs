import pika
import time
import json
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Task, User
from app.summarizer import summirize_youtube_video, summirize_file
from app.app_logger import get_logger


logger = get_logger("worker")


def process_task(task_id):
    db: Session = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.error(f"Task {task_id} not found in DB")
            return

        user = db.query(User).filter(User.id == task.user_id).first()
        if not user or not user.gemini_api_key:
            task.status = "error"
            task.result_text = "User has no API Key"
            db.commit()
            return

        task.status = "processing"
        db.commit()

        logger.info(f"Processing task {task_id} ({task.type})")
        
        result_text = ""
        try:
            if task.type == "youtube":
                result_text = summirize_youtube_video(task.source_data, user.gemini_api_key)
            elif task.type == "file":
                result_text = summirize_file(task.source_data, user.gemini_api_key)
            
            task.result_text = result_text
            task.status = "done"
            
        except Exception as e:
            logger.error(f"Failed processing task {task_id}: {e}")
            task.result_text = str(e)
            task.status = "error"

        db.commit()
        logger.info(f"Task {task_id} finished")

    except Exception as e:
        logger.error(f"Critical worker error: {e}")
    finally:
        db.close()

def main():
    logger.info("Connecting to RabbitMQ...")
    connection = None
    while connection is None:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
        except pika.exceptions.AMQPConnectionError:
            time.sleep(5)

    channel = connection.channel()
    channel.queue_declare(queue='summary_queue', durable=True)

    def callback(ch, method, properties, body):
        data = json.loads(body)
        task_id = data.get("task_id")
        
        if task_id:
            process_task(task_id)
        
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='summary_queue', on_message_callback=callback)

    logger.info(' [*] Worker started. Waiting for messages.')
    channel.start_consuming()

if __name__ == '__main__':
    main()