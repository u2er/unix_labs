import click
import requests
import json
import os
from pathlib import Path

API_URL = "http://localhost:8000"
CONFIG_FILE = Path.home() / ".scale_app_config.json"

def save_token(token, username):
    """Сохраняет токен и имя пользователя в файл конфигурации."""
    config = {"access_token": token, "username": username}
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

def load_token():
    """Загружает токен из файла конфигурации."""
    if not CONFIG_FILE.exists():
        return None
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            return data.get("access_token")
    except (json.JSONDecodeError, IOError):
        return None

def get_headers():
    """Возвращает заголовки с токеном авторизации."""
    token = load_token()
    if not token:
        click.secho("Вы не авторизованы. Используйте команду 'login'.", fg="red")
        exit(1)
    return {"Authorization": f"Bearer {token}"}

@click.group()
def cli():
    """CLI клиент для сервиса суммаризации контента."""
    pass

@cli.command()
@click.option('--username', prompt='Имя пользователя', help='Ваш логин')
@click.option('--password', prompt='Пароль', hide_input=True, help='Ваш пароль')
@click.option('--api-key', prompt='Gemini API Key', help='Ваш Google Gemini API Key')
def register(username, password, api_key):
    """Регистрация нового пользователя."""
    data = {
        "username": username,
        "password": password,
        "api_key": api_key
    }
    try:
        response = requests.post(f"{API_URL}/register", data=data)
        if response.status_code == 200:
            click.secho(f"Успешная регистрация пользователя {username}!", fg="green")
        elif response.status_code == 400:
            click.secho(f"Ошибка: {response.json().get('detail')}", fg="yellow")
        else:
            click.secho(f"Ошибка сервера: {response.status_code}", fg="red")
    except requests.exceptions.ConnectionError:
        click.secho("Не удалось подключиться к API. Проверьте, запущен ли сервер.", fg="red")

@cli.command()
@click.option('--username', prompt='Имя пользователя', help='Ваш логин')
@click.option('--password', prompt='Пароль', hide_input=True, help='Ваш пароль')
def login(username, password):
    """Авторизация и получение токена."""
    data = {
        "username": username,
        "password": password
    }
    try:
        response = requests.post(f"{API_URL}/token", data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            save_token(token_data["access_token"], username)
            click.secho(f"Вы успешно вошли как {username}.", fg="green")
        else:
            click.secho(f"Ошибка входа: {response.json().get('detail')}", fg="red")
    except requests.exceptions.ConnectionError:
        click.secho("Не удалось подключиться к API.", fg="red")

@cli.command()
@click.argument('url')
def youtube(url):
    """Суммаризация YouTube видео по ссылке.
    
    URL: Ссылка на видео (https://youtube.com/...)
    """
    headers = get_headers()
    click.secho(f"Отправка задачи на обработку видео: {url}...", fg="cyan")
    click.secho("Ожидание результата (это может занять время)...", fg="yellow")

    try:
        response = requests.post(f"{API_URL}/summarize/youtube", params={"url": url}, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            click.secho("\n--- Результат ---", fg="green", bold=True)
            click.echo(result.get("summary"))
        else:
            detail = response.json().get('detail') if response.content else response.text
            click.secho(f"Ошибка при обработке: {detail}", fg="red")
            
    except requests.exceptions.ConnectionError:
        click.secho("Ошибка соединения с сервером.", fg="red")
    except requests.exceptions.ReadTimeout:
        click.secho("Таймаут ожидания ответа.", fg="red")

@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
def file(file_path):
    """Суммаризация локального файла (аудио/видео/текст).
    
    FILE_PATH: Путь к файлу на диске.
    """
    headers = get_headers()
    file_name = os.path.basename(file_path)
    click.secho(f"Загрузка файла: {file_name}...", fg="cyan")
    click.secho("Ожидание результата (это может занять время)...", fg="yellow")

    try:
        with open(file_path, 'rb') as f:
            files = {'file': (file_name, f)}
            response = requests.post(f"{API_URL}/summarize/file", files=files, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            click.secho("\n--- Результат ---", fg="green", bold=True)
            click.echo(result.get("summary"))
        else:
            detail = response.json().get('detail') if response.content else response.text
            click.secho(f"Ошибка при обработке: {detail}", fg="red")

    except requests.exceptions.ConnectionError:
        click.secho("Ошибка соединения с сервером.", fg="red")

@cli.command()
def logout():
    """Выход из системы (удаление токена)."""
    if CONFIG_FILE.exists():
        os.remove(CONFIG_FILE)
        click.secho("Токен удален. Вы вышли из системы.", fg="yellow")
    else:
        click.secho("Вы и так не авторизованы.", fg="yellow")

if __name__ == '__main__':
    cli()