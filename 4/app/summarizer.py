import os
import time
import uuid

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

import google.generativeai as genai

from app_logger import get_logger


logger = get_logger(__name__)
os.makedirs('temp', exist_ok=True)

template = '''# Role
You are an expert Content Analyst and Summarizer. Your task is to process the provided text—which may be a transcript from a video, an audio recording, or the content of a document—and generate a structured, professional, and comprehensive summary.

# Input Context
The text provided below may contain conversational fillers (um, ah, like), timestamps, or minor transcription errors. Please ignore these and focus solely on the informational content and context.

# Instructions
1. **Analyze:** Read the entire text to understand the main topic, context, and speaker intent.
2. **Extract:** Identify the most critical points, arguments, facts, and numerical data.
3. **Structure:** Organize the information logically using the format defined below.
4. **Clarify:** Ensure the summary is distinct, easy to read, and free of repetition.
5. **Output format:** Use markdown syntax.
6. **Answer lenguage:** Russian.
'''


def get_youtube_transcript(video_url, request_id):
    try:
        if "v=" in video_url:
            video_id = video_url.split("v=")[1].split("&")[0]
        elif "youtu.be" in video_url: # Добавил поддержку коротких ссылок
            video_id = video_url.split("/")[-1]
        elif "youtube" in video_url:
            video_id = video_url.split("/")[-1]
        else:
            return None

        transcript = YouTubeTranscriptApi().fetch(video_id, languages=('en', 'ru'))
        formatter = TextFormatter()
        return formatter.format_transcript(transcript)

    except Exception as e:
        logger.error(f'Transcription getting error for request {request_id}: {e}')
        return None


def _process_with_gemini(file_path, api_key, request_id):
    """Вынес общую логику обработки"""
    try:
        genai.configure(api_key=api_key)    
        media_file = genai.upload_file(path=file_path)

        while media_file.state.name == "PROCESSING":
            time.sleep(2)
            media_file = genai.get_file(media_file.name)

        if media_file.state.name == "FAILED":
            logger.error(f'Ошибка обработки файла на серверах Google for request {request_id}')
            raise Exception("Ошибка обработки файла на серверах Google.")
        
        llm = genai.GenerativeModel(model_name="gemini-2.5-flash")

        atts = 5
        for i in range(atts):
            try:
                response = llm.generate_content([media_file, template])
                if os.path.exists(file_path):
                     os.remove(file_path)

                return response.text

            except Exception as e:
                logger.error(f'Iteration {i} failed for request {request_id}: {e}')
                time.sleep(2)

        else:
            logger.error(f'Response not generated for {request_id}')
            return "Failed to generate summary after retries"
    
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return f"Processing error: {e}"
    

def summirize_youtube_video(link, api_key):
    try:
        request_id = uuid.uuid4()
        transcription = get_youtube_transcript(link, request_id)

        if transcription:
            logger.info(f'Handling request {request_id} for youtube video')
            file_path = f'temp/transcription_{request_id}.txt'
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(f'YouTube video transcription:\n{transcription}')

            return _process_with_gemini(file_path, api_key, request_id)

        else:
            logger.debug(f'No transcription provided for request {request_id}')
            return 'Could not get transcription'
    
    except Exception as e:
        logger.error(f'Error while handling request {request_id}: {e}')
        return 'Handling error'
    

def summirize_file(file_path, api_key):
    try:
        request_id = uuid.uuid4()
        if os.path.exists(file_path):
            logger.info(f'Handling request {request_id} for file {file_path}')
            return _process_with_gemini(file_path, api_key, request_id)

        else:
            logger.debug(f'No such file {file_path} for {request_id}')
            return f'File was not found for request {request_id}'
        
    except Exception as e:
        logger.error(f'Error while handling request {request_id}: {e}')
        return 'Handling error'