# Mattermost Reactions Exporter

Утилита для экспорта реакций из постов Mattermost в YAML-формат.

## Требования

- Python 3.8+
- Зависимости из `requirements.txt`

## Установка

```bash
# Создать виртуальное окружение
python -m venv venv

# Активировать окружение
# macOS/Linux:
source venv/bin/activate
# Windows:
# venv\Scripts\activate

# Установить зависимости
pip install -r requirements.txt
```

## Запуск

```bash
streamlit run app.py
```

Приложение откроется в браузере по адресу `http://localhost:8501`

### Остановка приложения

Чтобы остановить приложение, нажмите `Ctrl+C` в терминале, где оно запущено.

Если приложение зависло:
```bash
pkill -f streamlit
```

## Использование

1. Введите URL сервера Mattermost
2. Введите личный токен доступа
3. Укажите URL или ID поста
4. Нажмите кнопку для получения реакций
5. Просмотрите результат в формате JSON
6. Скопируйте нужные данные

## Разработка

Проект находится в разработке. См. `prd_plan.md` для плана разработки.
