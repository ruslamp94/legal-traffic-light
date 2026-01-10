# Legal Traffic Light 🚦

Программа для анализа юридических документов с использованием AI.

## Возможности

✅ Сравнение документов (Jaccard + TF-IDF + N-grams + Levenstein)
✅ AI-анализ (OpenAI/Anthropic)
✅ Экспорт в HTML, DOCX, TXT, JSON
✅ История анализов
✅ Статус согласования ЮД
✅ Зоны риска по Регламенту АО НГПК

## Требования

- Python 3.8+
- pip

## Установка

1. Клонировать репозиторий:
```bash
git clone https://github.com/ruslamp94/legal-traffic-light.git
cd legal-traffic-light
```

2. Создать виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # На Windows: venv\\Scripts\\activate
```

3. Установить зависимости:
```bash
pip install -r requirements.txt
```

## Запуск

**Локально:**
```bash
streamlit run legal_traffic_light_v51.py
```

Приложение откроется в браузере на `http://localhost:8501`

## Для Streamlit Cloud

1. Создать файл `secrets.toml` в `.streamlit/`
2. Добавить API ключи:
```toml
ANTHROPIC_API_KEY = "your-key"
OPENAI_API_KEY = "your-key"
```

3. Развернуть на https://streamlit.io/cloud

## Структура проекта

- `legal_traffic_light_v51.py` - Главный файл приложения
- `requirements.txt` - Зависимости
- `.streamlit/config.toml` - Конфигурация Streamlit
- `.gitignore` - Исключения Git

## Автор

RUS LAMP - Legal Department
