"""
Регламент Светофор v7.8
АО «СПК» — Старая перевозочная компания

Дизайн в стиле НПК (npktrans.ru):
- Светлый фон
- Красный акцент
- Минималистичный стиль
"""

import streamlit as st
import re, json, hashlib, io, time
from datetime import datetime, date
from typing import Dict, List, Tuple, Optional

# Библиотеки
DOCX_AVAILABLE = False
PDF_AVAILABLE = False
REQUESTS_AVAILABLE = False

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except:
    pass

try:
    from PyPDF2 import PdfReader
    PDF_AVAILABLE = True
except:
    pass

try:
    import requests
    REQUESTS_AVAILABLE = True
except:
    pass

# Настройки
st.set_page_config(
    page_title="Регламент Светофор | СПК",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# КОНСТАНТЫ
# ============================================================================

РОЛЬ_АДМИН = "администратор"
РОЛЬ_ЮЗЕР = "пользователь"

DEFAULT_ORG = {
    "full_name": 'АО «Старая перевозочная компания»',
    "short_name": 'АО «СПК»',
    "inn": "7701234567",
}

DEFAULT_THRESHOLDS = {
    "зелёная_тф_макс": 100_000,
    "зелёная_нетф_макс": 50_000,
    "жёлтая_макс": 5_000_000,
}

ПОЛЬЗОВАТЕЛИ = {
    "admin": {"хеш": hashlib.sha256("admin123".encode()).hexdigest(), "роль": РОЛЬ_АДМИН, "имя": "Администратор"},
    "legal": {"хеш": hashlib.sha256("legal123".encode()).hexdigest(), "роль": РОЛЬ_АДМИН, "имя": "Руководитель ЮД"},
}

AI_ПРОВАЙДЕРЫ = {
    "openai": {"название": "OpenAI GPT-4", "url": "https://platform.openai.com/api-keys", "цена": "$0.15/1M"},
    "anthropic": {"название": "Anthropic Claude", "url": "https://console.anthropic.com/settings/keys", "цена": "$0.25/1M"},
    "gigachat": {"название": "GigaChat", "url": "https://developers.sber.ru/portal/products/gigachat-api", "цена": "Бесплатно"},
    "yandexgpt": {"название": "YandexGPT", "url": "https://console.cloud.yandex.ru/", "цена": "1.2₽/1000"},
}

ПОДРАЗДЕЛЕНИЯ = ["Юридический департамент", "Департамент перевозок", "Коммерческий департамент", 
                 "Департамент подвижного состава", "Финансовый департамент", "ИТ-департамент"]
ДОЛЖНОСТИ = ["Специалист", "Ведущий специалист", "Начальник отдела", "Руководитель департамента"]

КРАСНАЯ_ЗОНА = ["Аренда вагонов", "Лизинг вагонов", "Покупка вагонов", "Договор с РЖД", "Кредит", "Займ"]
ЖЁЛТАЯ_ЗОНА = ["Договор ТЭО", "Рамочный договор", "Единственный поставщик"]
ФОРМЫ_ДОКУМЕНТА = ["Типовая форма (ТФ)", "Форма контрагента", "Свободная форма"]

# ============================================================================
# ТИПОВЫЕ ФОРМЫ
# ============================================================================

ТИПОВЫЕ_ФОРМЫ = {
    "услуги_тэо": {
        "название": "Договор ТЭО",
        "код": "ТФ-СПК-001",
        "роль": "Заказчик",
        "маркеры": ["исполнитель", "заказчик", "услуги", "вагон", "перевозка"],
        "пункты": {
            "предоплата": {"эталон": "Предоплата не более 30%", "паттерн": r"предоплат\w*.*?(?:[4-9]\d|100)\s*%", "критичность": "красный"},
            "срок_оплаты": {"эталон": "Оплата в течение 5 рабочих дней", "паттерн": r"оплат\w*.*?(?:1|2|3)\s*(?:рабоч|календарн|банковск)", "критичность": "жёлтый"},
            "неустойка": {"эталон": "Неустойка не более 0.1% в день", "паттерн": r"неустойк\w*.*?(?:0[,.]?[3-9]|[1-9])\s*%", "критичность": "красный"},
            "штраф_простой": {"эталон": "Штраф за простой не более 2500 руб/сутки", "паттерн": r"(?:штраф|простой).*?(?:[3-9]\d{3}|[1-9]\d{4,})\s*(?:руб|₽)", "критичность": "красный"},
            "штраф_конфиденциальность": {"эталон": "Штраф за конфиденциальность не более 3 млн", "паттерн": r"(?:штраф|конфиденциальност).*?(?:[5-9]|[1-9]\d)\s*(?:000\s*000|млн)", "критичность": "красный"},
            "все_риски": {"эталон": "Риски распределяются между сторонами", "паттерн": r"заказчик.*?(?:несёт|принимает).*?(?:все|любые|полн)\w*\s*риск", "критичность": "красный"},
            "одностороннее_изменение": {"эталон": "Изменение цены по соглашению сторон", "паттерн": r"односторонн\w+.*?(?:изменен|повыш)\w*.*?(?:цен|тариф)", "критичность": "красный"},
            "молчание_согласие": {"эталон": "Услуги приняты после подписания акта", "паттерн": r"молчани\w*.*?(?:согласи|акцепт|принят)", "критичность": "жёлтый"},
            "без_ограничения": {"эталон": "Неустойка с ограничением 10%", "паттерн": r"без\s*(?:ограничен|лимит|предел)", "критичность": "жёлтый"},
        }
    },
    "поставка": {
        "название": "Договор поставки",
        "код": "ТФ-СПК-002",
        "роль": "Покупатель",
        "маркеры": ["поставщик", "покупатель", "товар", "поставка"],
        "пункты": {
            "предоплата": {"эталон": "Предоплата не более 30%", "паттерн": r"предоплат\w*.*?(?:[4-9]\d|100)\s*%", "критичность": "красный"},
            "гарантия": {"эталон": "Гарантия не менее 12 месяцев", "паттерн": r"гарантия.*?(?:[1-6])\s*месяц", "критичность": "жёлтый"},
        }
    },
}

ДЕМО_ДОГОВОР = """ДОГОВОР ОКАЗАНИЯ УСЛУГ № 2025/ТЭО-001

г. Москва                                           «15» января 2025 г.

ООО «ТрансЛогистик» (ИНН 7707999888), именуемое «Исполнитель», и
АО «СПК» (ИНН 7701234567), именуемое «Заказчик», заключили договор:

1. ПРЕДМЕТ ДОГОВОРА
1.1. Исполнитель оказывает услуги по предоставлению вагонов для перевозки грузов.

2. СТОИМОСТЬ И РАСЧЁТЫ
2.1. Стоимость: 8 500 000 рублей.
2.2. Предоплата 50% в течение 5 дней.
2.3. Оплата в течение 3 календарных дней после счёта.
2.4. Исполнитель вправе в одностороннем порядке изменять тарифы.

3. ПРИЁМКА
3.1. Молчание Заказчика более 3 дней считается согласием с актом.

4. ОТВЕТСТВЕННОСТЬ
4.1. Штраф за простой 5000 рублей за вагоно-сутки.
4.2. Неустойка 0,5% за день без ограничения.
4.3. Заказчик несёт все риски по вагонам.

5. КОНФИДЕНЦИАЛЬНОСТЬ
5.1. Штраф за нарушение: 15 000 000 рублей.

РЕКВИЗИТЫ:
Заказчик: АО «СПК», ИНН 7701234567
Исполнитель: ООО «ТрансЛогистик», ИНН 7707999888
"""

# ============================================================================
# СТИЛИ В СТИЛЕ НПК (СВЕТЛЫЙ, КРАСНЫЙ АКЦЕНТ)
# ============================================================================

def применить_стили():
    st.markdown("""
<style>
/* ========== ЦВЕТА НПК ========== */
:root {
    --npk-red: #c41e3a;
    --npk-dark-red: #a01830;
    --npk-black: #1a1a1a;
    --npk-gray: #666666;
    --npk-light-gray: #f5f5f5;
    --npk-border: #e0e0e0;
    --npk-white: #ffffff;
}

/* ========== ОСНОВНОЙ ФОН ========== */
.stApp {
    background-color: var(--npk-white) !important;
}

[data-testid="stAppViewContainer"] {
    background-color: var(--npk-white) !important;
}

/* ========== SIDEBAR ========== */
[data-testid="stSidebar"] {
    background-color: var(--npk-white) !important;
    border-right: 1px solid var(--npk-border) !important;
}

[data-testid="stSidebar"] * {
    color: var(--npk-black) !important;
}

/* ========== ХЕДЕР С ЛОГОТИПОМ НПК ========== */
.npk-header {
    padding: 20px 0;
    border-bottom: 1px solid var(--npk-border);
    margin-bottom: 30px;
}

.npk-logo {
    display: flex;
    align-items: center;
    gap: 15px;
}

.npk-logo-icon {
    width: 50px;
    height: 50px;
    position: relative;
}

.npk-logo-icon::before {
    content: "";
    position: absolute;
    width: 40px;
    height: 20px;
    border: 4px solid var(--npk-red);
    border-bottom: none;
    border-radius: 40px 40px 0 0;
    top: 5px;
    left: 5px;
}

.npk-logo-text {
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--npk-black);
    line-height: 1.2;
}

.npk-logo-text span {
    color: var(--npk-red);
    font-weight: 700;
}

/* ========== НАВИГАЦИЯ ========== */
.npk-nav {
    display: flex;
    gap: 30px;
    padding: 15px 0;
    border-bottom: 1px solid var(--npk-border);
    margin-bottom: 30px;
}

.npk-nav a {
    color: var(--npk-gray);
    text-decoration: none;
    font-size: 0.95rem;
    font-weight: 500;
    transition: color 0.2s;
}

.npk-nav a:hover, .npk-nav a.active {
    color: var(--npk-red);
}

/* ========== ЗАГОЛОВКИ ========== */
.npk-title {
    font-size: 3rem;
    font-weight: 300;
    color: var(--npk-light-gray);
    letter-spacing: 2px;
    margin-bottom: 30px;
}

.npk-subtitle {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--npk-black);
    margin-bottom: 20px;
    padding-bottom: 10px;
    border-bottom: 2px solid var(--npk-red);
    display: inline-block;
}

/* ========== СЕКЦИИ ========== */
.npk-section {
    margin-bottom: 40px;
}

.npk-section-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--npk-black);
    margin-bottom: 15px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--npk-border);
}

/* ========== ТАБЛИЦА ДАННЫХ ========== */
.npk-table {
    width: 100%;
}

.npk-table-row {
    display: flex;
    padding: 12px 0;
    border-bottom: 1px solid var(--npk-border);
}

.npk-table-label {
    width: 200px;
    color: var(--npk-gray);
    font-size: 0.95rem;
}

.npk-table-value {
    flex: 1;
    color: var(--npk-black);
    font-size: 0.95rem;
}

.npk-table-value a {
    color: var(--npk-black);
    text-decoration: underline;
}

/* ========== КАРТОЧКИ ЗОН ========== */
.zone-card {
    border-radius: 4px;
    padding: 20px;
    margin: 20px 0;
    border-left: 4px solid;
}

.zone-card.зелёная { 
    background: #f0fdf4; 
    border-left-color: #22c55e; 
}
.zone-card.жёлтая { 
    background: #fffbeb; 
    border-left-color: #f59e0b; 
}
.zone-card.красная { 
    background: #fef2f2; 
    border-left-color: var(--npk-red); 
}

.zone-card h3 {
    margin: 0 0 10px 0;
    color: var(--npk-black);
    font-size: 1.2rem;
}

.zone-card p {
    margin: 5px 0;
    color: var(--npk-gray);
}

/* ========== КАРТОЧКИ РИСКОВ ========== */
.risk-card {
    background: var(--npk-white);
    border: 1px solid var(--npk-border);
    border-radius: 4px;
    padding: 15px;
    margin: 15px 0;
    border-left: 4px solid;
}

.risk-card.red { border-left-color: var(--npk-red); }
.risk-card.yellow { border-left-color: #f59e0b; }

.risk-card strong {
    color: var(--npk-black);
}

.risk-card .context {
    background: var(--npk-light-gray);
    padding: 10px;
    border-radius: 4px;
    margin: 10px 0;
    font-style: italic;
    color: var(--npk-gray);
    font-size: 0.9rem;
}

/* ========== МЕТРИКИ ========== */
.npk-metrics {
    display: flex;
    gap: 20px;
    margin: 20px 0;
}

.npk-metric {
    flex: 1;
    text-align: center;
    padding: 20px;
    background: var(--npk-light-gray);
    border-radius: 4px;
}

.npk-metric-value {
    font-size: 2.5rem;
    font-weight: 700;
    color: var(--npk-black);
}

.npk-metric-value.red { color: var(--npk-red); }
.npk-metric-value.yellow { color: #f59e0b; }
.npk-metric-value.green { color: #22c55e; }

.npk-metric-label {
    font-size: 0.85rem;
    color: var(--npk-gray);
    margin-top: 5px;
}

/* ========== КНОПКИ В СТИЛЕ НПК ========== */
.stButton > button {
    background: var(--npk-white) !important;
    color: var(--npk-black) !important;
    border: 1px solid var(--npk-border) !important;
    border-radius: 4px !important;
    padding: 10px 25px !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}

.stButton > button:hover {
    border-color: var(--npk-red) !important;
    color: var(--npk-red) !important;
}

.stButton > button[kind="primary"] {
    background: var(--npk-red) !important;
    color: white !important;
    border-color: var(--npk-red) !important;
}

.stButton > button[kind="primary"]:hover {
    background: var(--npk-dark-red) !important;
}

/* ========== ИЗВЛЕЧЁННЫЕ ДАННЫЕ ========== */
.extract-card {
    background: var(--npk-light-gray);
    border-radius: 4px;
    padding: 20px;
    margin: 20px 0;
}

.extract-card h4 {
    color: var(--npk-black);
    margin-bottom: 15px;
    font-size: 1rem;
}

/* ========== ТИП ДОКУМЕНТА ========== */
.doc-type {
    display: flex;
    align-items: center;
    gap: 15px;
    padding: 15px 20px;
    border-radius: 4px;
    margin: 15px 0;
}

.doc-type.договор {
    background: #f0fdf4;
    border: 1px solid #22c55e;
}

.doc-type.не-договор {
    background: #fffbeb;
    border: 1px solid #f59e0b;
}

.doc-type-icon {
    font-size: 1.5rem;
}

.doc-type-text strong {
    color: var(--npk-black);
    display: block;
}

.doc-type-text small {
    color: var(--npk-gray);
}

/* ========== AI РЕЗУЛЬТАТ ========== */
.ai-result {
    background: var(--npk-light-gray);
    border: 1px solid var(--npk-border);
    border-radius: 4px;
    padding: 25px;
    margin-top: 20px;
    line-height: 1.7;
    color: var(--npk-black);
}

/* ========== ЗАГРУЗКА С ПОЕЗДОМ ========== */
.loading-train {
    text-align: center;
    padding: 40px;
    background: var(--npk-light-gray);
    border-radius: 4px;
    margin: 20px 0;
}

.loading-train .train {
    font-size: 2.5rem;
    animation: trainMove 2s ease-in-out infinite;
}

@keyframes trainMove {
    0%, 100% { transform: translateX(-20px); }
    50% { transform: translateX(20px); }
}

.loading-train .text {
    color: var(--npk-gray);
    margin-top: 15px;
    font-size: 1rem;
}

/* ========== СВЕТОФОР ========== */
.traffic-light {
    display: flex;
    gap: 8px;
    margin-bottom: 10px;
}

.traffic-light span {
    width: 16px;
    height: 16px;
    border-radius: 50%;
}

.tl-red { background: var(--npk-red); }
.tl-yellow { background: #f59e0b; }
.tl-green { background: #22c55e; }

/* ========== БЕЙДЖИ ========== */
.admin-badge {
    background: var(--npk-red);
    color: white;
    padding: 4px 12px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
}

.user-badge {
    background: var(--npk-gray);
    color: white;
    padding: 4px 12px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
}

/* ========== TABS ========== */
.stTabs [data-baseweb="tab-list"] {
    gap: 30px;
    border-bottom: 1px solid var(--npk-border);
}

.stTabs [data-baseweb="tab"] {
    color: var(--npk-gray) !important;
    font-weight: 500;
}

.stTabs [aria-selected="true"] {
    color: var(--npk-red) !important;
    border-bottom-color: var(--npk-red) !important;
}

/* ========== INPUTS ========== */
.stTextInput > div > div > input,
.stSelectbox > div > div,
.stNumberInput > div > div > input {
    border-color: var(--npk-border) !important;
    border-radius: 4px !important;
}

.stTextInput > div > div > input:focus,
.stSelectbox > div > div:focus {
    border-color: var(--npk-red) !important;
}

/* ========== FOOTER ========== */
.npk-footer {
    margin-top: 50px;
    padding: 20px 0;
    border-top: 1px solid var(--npk-border);
    color: var(--npk-gray);
    font-size: 0.85rem;
}

.npk-footer strong {
    color: var(--npk-red);
}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# ЭКСТРАКТОР ДАННЫХ
# ============================================================================

def извлечь_дату(текст: str):
    месяцы = {'января':1,'февраля':2,'марта':3,'апреля':4,'мая':5,'июня':6,
              'июля':7,'августа':8,'сентября':9,'октября':10,'ноября':11,'декабря':12}
    m = re.search(r'«?(\d{1,2})»?\s*([а-яё]+)\s*(\d{4})', текст.lower())
    if m:
        try:
            return date(int(m.group(3)), месяцы.get(m.group(2), 1), int(m.group(1)))
        except:
            pass
    m = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', текст)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except:
            pass
    return None


def извлечь_номер(текст: str):
    m = re.search(r'№\s*([A-Za-zА-Яа-я0-9\-/]+)', текст[:500])
    if m and len(m.group(1).strip()) >= 3:
        return m.group(1).strip()
    return None


def извлечь_сумму(текст: str):
    m = re.search(r'(\d[\d\s]*\d)\s*(?:\([^)]+\))?\s*руб', текст.lower())
    if m:
        try:
            return float(re.sub(r'\s', '', m.group(1)))
        except:
            pass
    return None


def извлечь_контрагента(текст: str):
    юрлица = re.findall(r'((?:ООО|ОАО|ЗАО|ПАО|АО)\s*[«"]([^»"]+)[»"])', текст)
    for полное, название in юрлица:
        if 'СПК' not in название.upper() and 'СТАРАЯ' not in название.upper():
            return полное
    return None


def определить_тип_документа(текст: str):
    текст_l = текст[:2000].lower()
    if "договор" in текст_l or "контракт" in текст_l:
        if "услуг" in текст_l and ("вагон" in текст_l or "перевоз" in текст_l):
            return {"тип": "услуги_тэо", "название": "Договор ТЭО", "это_договор": True}
        elif "поставк" in текст_l:
            return {"тип": "поставка", "название": "Договор поставки", "это_договор": True}
        return {"тип": "иной", "название": "Договор", "это_договор": True}
    if "счёт" in текст_l or "счет" in текст_l:
        return {"тип": "счёт", "название": "Счёт на оплату", "это_договор": False}
    if "акт" in текст_l[:200]:
        return {"тип": "акт", "название": "Акт", "это_договор": False}
    return {"тип": "неизвестно", "название": "Документ", "это_договор": False}


def извлечь_все_данные(текст: str):
    return {
        "тип_док": определить_тип_документа(текст),
        "дата": извлечь_дату(текст),
        "номер": извлечь_номер(текст),
        "сумма": извлечь_сумму(текст),
        "контрагент": извлечь_контрагента(текст),
    }


# ============================================================================
# RAG АНАЛИЗАТОР
# ============================================================================

def анализ_rag(текст: str, код_тф: str):
    результат = {
        "успех": False, "название_тф": "", "нарушения": [],
        "красных": 0, "жёлтых": 0, "соответствие": 100, "вердикт": "", "резюме": ""
    }
    
    все_тф = {**ТИПОВЫЕ_ФОРМЫ, **st.session_state.get("пользовательские_тф", {})}
    if код_тф not in все_тф:
        результат["резюме"] = "Типовая форма не найдена"
        return результат
    
    тф = все_тф[код_тф]
    результат["название_тф"] = тф.get("название", "")
    результат["успех"] = True
    текст_l = текст.lower()
    
    for название, данные in тф.get("пункты", {}).items():
        паттерн = данные.get("паттерн", "")
        if not паттерн:
            continue
        try:
            match = re.search(паттерн, текст_l, re.IGNORECASE | re.DOTALL)
            if match:
                start = max(0, match.start() - 50)
                end = min(len(текст), match.end() + 80)
                контекст = текст[start:end].replace('\n', ' ').strip()
                текст_до = текст[max(0, match.start()-100):match.start()]
                пункт_m = re.search(r'(\d+\.\d+)', текст_до)
                результат["нарушения"].append({
                    "название": название,
                    "эталон": данные.get("эталон", ""),
                    "критичность": данные.get("критичность", "жёлтый"),
                    "пункт": пункт_m.group(1) if пункт_m else None,
                    "контекст": f"...{контекст}..."
                })
        except:
            pass
    
    результат["красных"] = sum(1 for н in результат["нарушения"] if н["критичность"] == "красный")
    результат["жёлтых"] = sum(1 for н in результат["нарушения"] if н["критичность"] == "жёлтый")
    штраф = результат["красных"] * 15 + результат["жёлтых"] * 5
    результат["соответствие"] = max(0, 100 - штраф)
    
    if результат["красных"] == 0 and результат["жёлтых"] <= 2:
        результат["вердикт"] = "СООТВЕТСТВУЕТ"
        результат["резюме"] = f"Договор соответствует ТФ ({результат['соответствие']}%)"
    elif результат["красных"] <= 2:
        результат["вердикт"] = "ЧАСТИЧНО"
        результат["резюме"] = f"Частичное соответствие ({результат['соответствие']}%)"
    else:
        результат["вердикт"] = "НЕ_СООТВЕТСТВУЕТ"
        результат["резюме"] = f"Не соответствует ТФ ({результат['соответствие']}%)"
    
    return результат


# ============================================================================
# ОПРЕДЕЛЕНИЕ ЗОНЫ
# ============================================================================

def определить_зону(сумма: float, форма: str, тип_сделки: str):
    пороги = st.session_state.get("пороги", DEFAULT_THRESHOLDS)
    
    if тип_сделки in КРАСНАЯ_ЗОНА:
        return {"зона": "красная", "причина": f"Тип сделки: {тип_сделки}", "юд": True, "срок": 10}
    if сумма > пороги.get("жёлтая_макс", 5_000_000):
        return {"зона": "красная", "причина": f"Сумма превышает {пороги['жёлтая_макс']:,}₽", "юд": True, "срок": 10}
    if тип_сделки in ЖЁЛТАЯ_ЗОНА:
        return {"зона": "жёлтая", "причина": f"Тип сделки: {тип_сделки}", "юд": True, "срок": 5}
    if форма == "Типовая форма (ТФ)":
        if сумма > пороги.get("зелёная_тф_макс", 100_000):
            return {"зона": "жёлтая", "причина": f"ТФ свыше {пороги['зелёная_тф_макс']:,}₽", "юд": True, "срок": 5}
    else:
        if сумма > пороги.get("зелёная_нетф_макс", 50_000):
            return {"зона": "жёлтая", "причина": f"Нетиповая форма свыше {пороги['зелёная_нетф_макс']:,}₽", "юд": True, "срок": 5}
    return {"зона": "зелёная", "причина": "Зелёный коридор (п. 4.1 Регламента)", "юд": False, "срок": 0}

# ============================================================================
# AI КЛИЕНТ
# ============================================================================

def ai_анализ(текст: str, извлечённые: dict, rag: dict):
    api_ключи = st.session_state.get("api_ключи", {})
    орг = st.session_state.get("орг", DEFAULT_ORG)
    
    провайдер = None
    ключ = ""
    for pid in ["openai", "anthropic", "yandexgpt"]:
        if api_ключи.get(pid):
            провайдер = pid
            ключ = api_ключи[pid]
            break
    
    if not провайдер:
        return False, "Не настроен AI-провайдер"
    
    тип_док = извлечённые.get("тип_док", {})
    нарушения_текст = ""
    for i, н in enumerate(rag.get("нарушения", [])[:8], 1):
        emoji = "🔴" if н["критичность"] == "красный" else "🟡"
        пункт = f"п.{н['пункт']}" if н.get("пункт") else ""
        нарушения_текст += f"\n{i}. {emoji} [{пункт}] {н['эталон']}\n   Контекст: {н.get('контекст', '')[:100]}"
    
    промпт = f"""Ты — корпоративный юрист {орг.get('short_name', 'АО СПК')}.

ДОКУМЕНТ: {тип_док.get('название', 'Договор')}
Контрагент: {извлечённые.get('контрагент', '—')}
Сумма: {извлечённые.get('сумма', 0):,.0f}₽

ТЕКСТ:
{текст[:5000]}

НАРУШЕНИЯ:
{нарушения_текст if нарушения_текст else "Не выявлено"}

{'Это НЕ договор. Опиши что это.' if not тип_док.get('это_договор') else '''
ЗАДАНИЕ — детальный анализ:

## 1. ЧТО ЭТО
Кратко: тип договора, стороны, предмет, сумма.

## 2. КРИТИЧЕСКИЕ ПУНКТЫ
Для каждого:
- **Пункт X.X** — проблема
- Текст: "цитата"
- ❌ Риск: пояснение
- ✅ Исправить: "готовая формулировка"

## 3. ЗАМЕЧАНИЯ
Аналогично.

## 4. РЕКОМЕНДАЦИЯ
Одно из: ✅ СОГЛАСОВАТЬ / ⚠️ С ЗАМЕЧАНИЯМИ / 🔄 ДОРАБОТАТЬ / ❌ ОТКЛОНИТЬ

Указывай НОМЕРА пунктов и ГОТОВЫЕ формулировки.
'''}"""

    try:
        if провайдер == "openai":
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {ключ}", "Content-Type": "application/json"},
                json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": промпт}], "max_tokens": 3000, "temperature": 0.3},
                timeout=90
            )
            if response.status_code == 200:
                return True, response.json()["choices"][0]["message"]["content"]
            return False, f"Ошибка: {response.status_code}"
        
        elif провайдер == "anthropic":
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": ключ, "Content-Type": "application/json", "anthropic-version": "2023-06-01"},
                json={"model": "claude-3-haiku-20240307", "max_tokens": 3000, "messages": [{"role": "user", "content": промпт}]},
                timeout=90
            )
            if response.status_code == 200:
                return True, response.json()["content"][0]["text"]
            return False, f"Ошибка: {response.status_code}"
        
        elif провайдер == "yandexgpt":
            folder = st.session_state.get("yandex_folder", "")
            if not folder:
                return False, "Укажите Folder ID"
            response = requests.post(
                "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
                headers={"Authorization": f"Api-Key {ключ}", "Content-Type": "application/json"},
                json={"modelUri": f"gpt://{folder}/yandexgpt-lite", "completionOptions": {"maxTokens": 3000}, "messages": [{"role": "user", "text": промпт}]},
                timeout=90
            )
            if response.status_code == 200:
                return True, response.json()["result"]["alternatives"][0]["message"]["text"]
            return False, f"Ошибка: {response.status_code}"
        
        return False, "Неизвестный провайдер"
    except requests.exceptions.Timeout:
        return False, "Таймаут"
    except Exception as e:
        return False, str(e)


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ
# ============================================================================

def загрузить_файл(f):
    if not f:
        return False, ""
    try:
        content = f.read()
        name = f.name.lower()
        
        if name.endswith('.txt'):
            for enc in ['utf-8', 'cp1251', 'cp866']:
                try:
                    return True, content.decode(enc)
                except:
                    pass
            return True, content.decode('utf-8', errors='replace')
        
        elif name.endswith('.docx') and DOCX_AVAILABLE:
            doc = DocxDocument(io.BytesIO(content))
            text = '\n'.join([p.text for p in doc.paragraphs if p.text.strip()])
            return (True, text) if text else (False, "Пустой документ")
        
        elif name.endswith('.pdf') and PDF_AVAILABLE:
            reader = PdfReader(io.BytesIO(content))
            text = '\n'.join([p.extract_text() or '' for p in reader.pages])
            return (True, text) if text.strip() else (False, "Не удалось извлечь")
        
        return False, "Неподдерживаемый формат"
    except Exception as e:
        return False, str(e)


def это_админ():
    return st.session_state.get("роль", "") == РОЛЬ_АДМИН


def инициализация():
    defaults = {
        "авторизован": False, "пользователь": None, "роль": РОЛЬ_ЮЗЕР,
        "текст": "", "извлечённые": None, "зона": None, "rag": None, "ai": "",
        "история": [], "орг": DEFAULT_ORG.copy(), "пороги": DEFAULT_THRESHOLDS.copy(),
        "api_ключи": {}, "yandex_folder": "", "пользовательские_тф": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ============================================================================
# СТРАНИЦА ВХОДА (СТИЛЬ НПК)
# ============================================================================

def страница_входа():
    st.markdown('''
    <div style="text-align:center;padding:60px 20px;">
        <div class="traffic-light" style="justify-content:center;margin-bottom:20px;">
            <span class="tl-red"></span>
            <span class="tl-yellow"></span>
            <span class="tl-green"></span>
        </div>
        <div class="npk-title">РЕГЛАМЕНТ СВЕТОФОР</div>
        <div style="margin-bottom:10px;">
            <span style="color:#c41e3a;font-weight:600;font-size:1.2rem;">СТАРАЯ ПЕРЕВОЗОЧНАЯ</span>
        </div>
        <p style="color:#666;margin-bottom:40px;">Система анализа договоров v7.8</p>
    </div>
    ''', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        tab1, tab2 = st.tabs(["Пользователь", "Администратор"])
        
        with tab1:
            st.markdown('<div class="npk-section-title">Вход в систему</div>', unsafe_allow_html=True)
            with st.form("user_form"):
                имя = st.text_input("ФИО", placeholder="Иванов Иван Иванович")
                должность = st.selectbox("Должность", ["— Выберите —"] + ДОЛЖНОСТИ)
                подразделение = st.selectbox("Подразделение", ["— Выберите —"] + ПОДРАЗДЕЛЕНИЯ)
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.form_submit_button("Войти", use_container_width=True):
                        if имя and должность != "— Выберите —" and подразделение != "— Выберите —":
                            st.session_state.авторизован = True
                            st.session_state.пользователь = {"имя": имя, "должность": должность}
                            st.session_state.роль = РОЛЬ_ЮЗЕР
                            st.rerun()
                        else:
                            st.error("Заполните все поля")
                with c2:
                    if st.form_submit_button("Демо-режим", use_container_width=True):
                        st.session_state.авторизован = True
                        st.session_state.пользователь = {"имя": "Демо", "должность": "Специалист"}
                        st.session_state.роль = РОЛЬ_ЮЗЕР
                        st.session_state.текст = ДЕМО_ДОГОВОР
                        st.rerun()
        
        with tab2:
            st.markdown('<div class="npk-section-title">Вход администратора</div>', unsafe_allow_html=True)
            with st.form("admin_form"):
                логин = st.text_input("Логин", placeholder="admin")
                пароль = st.text_input("Пароль", type="password")
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.form_submit_button("Войти", use_container_width=True):
                        if логин in ПОЛЬЗОВАТЕЛИ and ПОЛЬЗОВАТЕЛИ[логин]["хеш"] == hashlib.sha256(пароль.encode()).hexdigest():
                            st.session_state.авторизован = True
                            st.session_state.пользователь = {"имя": ПОЛЬЗОВАТЕЛИ[логин]["имя"], "должность": "Администратор"}
                            st.session_state.роль = РОЛЬ_АДМИН
                            st.rerun()
                        else:
                            st.error("Неверный логин или пароль")
                with c2:
                    if st.form_submit_button("Демо-админ", use_container_width=True):
                        st.session_state.авторизован = True
                        st.session_state.пользователь = {"имя": "Демо-админ", "должность": "Администратор"}
                        st.session_state.роль = РОЛЬ_АДМИН
                        st.session_state.текст = ДЕМО_ДОГОВОР
                        st.rerun()
            
            st.caption("Учётные записи: admin/admin123, legal/legal123")
    
    # Футер
    st.markdown('''
    <div class="npk-footer" style="text-align:center;">
        <strong>АО «Старая перевозочная компания»</strong><br>
        105066, Россия, г. Москва
    </div>
    ''', unsafe_allow_html=True)


# ============================================================================
# БОКОВАЯ ПАНЕЛЬ
# ============================================================================

def боковая_панель():
    with st.sidebar:
        # Логотип НПК
        st.markdown('''
        <div class="npk-logo" style="margin-bottom:20px;">
            <div class="npk-logo-icon"></div>
            <div class="npk-logo-text">
                <span>СТАРАЯ</span><br>ПЕРЕВОЗОЧНАЯ
            </div>
        </div>
        ''', unsafe_allow_html=True)
        
        user = st.session_state.пользователь
        is_admin = это_админ()
        
        badge = "admin-badge" if is_admin else "user-badge"
        badge_text = "АДМИНИСТРАТОР" if is_admin else "ПОЛЬЗОВАТЕЛЬ"
        
        st.markdown(f'''
        <div style="padding:15px;background:#f5f5f5;border-radius:4px;margin-bottom:20px;">
            <div style="font-weight:600;color:#1a1a1a;margin-bottom:5px;">{user["имя"]}</div>
            <div style="color:#666;font-size:0.9rem;margin-bottom:10px;">{user["должность"]}</div>
            <span class="{badge}">{badge_text}</span>
        </div>
        ''', unsafe_allow_html=True)
        
        if st.button("Выйти", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()
        
        st.markdown("---")
        
        # Контакты
        st.markdown('''
        <div class="npk-section-title">Контакты</div>
        <div class="npk-table">
            <div class="npk-table-row">
                <div class="npk-table-label">Подразделение</div>
                <div class="npk-table-value">Юридический департамент</div>
            </div>
            <div class="npk-table-row">
                <div class="npk-table-label">Телефон</div>
                <div class="npk-table-value">+7 (495) 445-05-75</div>
            </div>
        </div>
        ''', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Пороги
        пороги = st.session_state.get("пороги", DEFAULT_THRESHOLDS)
        st.markdown(f'''
        <div class="npk-section-title">Пороги зон</div>
        <div class="npk-table">
            <div class="npk-table-row">
                <div class="npk-table-label">🟢 ТФ</div>
                <div class="npk-table-value">≤ {пороги['зелёная_тф_макс']:,}₽</div>
            </div>
            <div class="npk-table-row">
                <div class="npk-table-label">🟢 Иные</div>
                <div class="npk-table-value">≤ {пороги['зелёная_нетф_макс']:,}₽</div>
            </div>
            <div class="npk-table-row">
                <div class="npk-table-label">🟡 Жёлтая</div>
                <div class="npk-table-value">до {пороги['жёлтая_макс']:,}₽</div>
            </div>
            <div class="npk-table-row">
                <div class="npk-table-label">🔴 Красная</div>
                <div class="npk-table-value">> {пороги['жёлтая_макс']:,}₽</div>
            </div>
        </div>
        ''', unsafe_allow_html=True)
        
        # Статус AI
        api = st.session_state.get("api_ключи", {})
        активные = [p for p in AI_ПРОВАЙДЕРЫ if api.get(p)]
        
        st.markdown("---")
        if активные:
            st.success(f"AI: {len(активные)} провайдер(а)")
        else:
            st.warning("AI не настроен")

# ============================================================================
# ВКЛАДКА АНАЛИЗА
# ============================================================================

def вкладка_анализа():
    st.markdown('<div class="npk-title">АНАЛИЗ ДОГОВОРА</div>', unsafe_allow_html=True)
    
    # Загрузка
    st.markdown('<div class="npk-section-title">Загрузка документа</div>', unsafe_allow_html=True)
    
    файл = st.file_uploader("Выберите файл (DOCX, PDF, TXT)", type=["txt", "docx", "pdf"], label_visibility="collapsed")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        btn_demo = st.button("Загрузить демо", use_container_width=True)
    with col2:
        btn_clear = st.button("Очистить", use_container_width=True)
    with col3:
        показать_текст = st.checkbox("Ввести текст вручную")
    
    if btn_demo:
        st.session_state.текст = ДЕМО_ДОГОВОР
        st.session_state.извлечённые = извлечь_все_данные(ДЕМО_ДОГОВОР)
        st.rerun()
    
    if btn_clear:
        st.session_state.текст = ""
        st.session_state.извлечённые = None
        st.session_state.зона = None
        st.session_state.rag = None
        st.session_state.ai = ""
        st.rerun()
    
    if файл:
        ok, текст = загрузить_файл(файл)
        if ok and текст != st.session_state.текст:
            st.session_state.текст = текст[:300000]
            st.session_state.извлечённые = извлечь_все_данные(текст)
            st.success(f"Загружено: {len(текст):,} символов")
            st.rerun()
        elif not ok:
            st.error(текст)
    
    if показать_текст:
        новый = st.text_area("Текст договора:", value=st.session_state.текст, height=150)
        if st.button("Применить"):
            if len(новый) > 50:
                st.session_state.текст = новый
                st.session_state.извлечённые = извлечь_все_данные(новый)
                st.rerun()
    
    # ========== ДАННЫЕ ==========
    if st.session_state.текст and st.session_state.извлечённые:
        извл = st.session_state.извлечённые
        тип_док = извл.get("тип_док", {})
        
        # Тип документа
        if тип_док.get("это_договор"):
            st.markdown(f'''
            <div class="doc-type договор">
                <div class="doc-type-icon">📑</div>
                <div class="doc-type-text">
                    <strong>{тип_док.get("название", "Договор")}</strong>
                    <small>Документ определён как договор</small>
                </div>
            </div>
            ''', unsafe_allow_html=True)
        else:
            st.markdown(f'''
            <div class="doc-type не-договор">
                <div class="doc-type-icon">⚠️</div>
                <div class="doc-type-text">
                    <strong>{тип_док.get("название", "Документ")}</strong>
                    <small>Это не договор</small>
                </div>
            </div>
            ''', unsafe_allow_html=True)
        
        # Извлечённые данные
        st.markdown('<div class="npk-section-title">Извлечённые данные</div>', unsafe_allow_html=True)
        st.markdown(f'''
        <div class="npk-table" style="margin-bottom:20px;">
            <div class="npk-table-row">
                <div class="npk-table-label">Контрагент</div>
                <div class="npk-table-value">{извл.get("контрагент") or "—"}</div>
            </div>
            <div class="npk-table-row">
                <div class="npk-table-label">Номер</div>
                <div class="npk-table-value">{извл.get("номер") or "—"}</div>
            </div>
            <div class="npk-table-row">
                <div class="npk-table-label">Дата</div>
                <div class="npk-table-value">{извл["дата"].strftime("%d.%m.%Y") if извл.get("дата") else "—"}</div>
            </div>
            <div class="npk-table-row">
                <div class="npk-table-label">Сумма</div>
                <div class="npk-table-value">{f'{извл["сумма"]:,.0f} ₽' if извл.get("сумма") else "—"}</div>
            </div>
        </div>
        ''', unsafe_allow_html=True)
        
        # Поля редактирования
        st.markdown('<div class="npk-section-title">Параметры договора</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            контрагент = st.text_input("Контрагент", value=извл.get("контрагент") or "")
            сумма_str = st.text_input("Сумма (₽)", value=f"{извл['сумма']:,.0f}".replace(",", " ") if извл.get("сумма") else "")
        with c2:
            форма = st.selectbox("Форма документа", ФОРМЫ_ДОКУМЕНТА)
            тип_сделки = st.selectbox("Тип сделки", ["— Обычный —"] + КРАСНАЯ_ЗОНА + ЖЁЛТАЯ_ЗОНА)
        
        сумма = 0
        if сумма_str:
            try:
                сумма = float(re.sub(r'[^\d]', '', сумма_str))
            except:
                pass
        
        if тип_сделки == "— Обычный —":
            тип_сделки = ""
        
        st.session_state.текущие = {"контрагент": контрагент, "сумма": сумма}
        
        st.markdown("---")
        
        # ========== КНОПКИ ==========
        st.markdown('<div class="npk-section-title">Анализ</div>', unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        
        with c1:
            if st.button("🚦 Определить зону", type="primary", use_container_width=True):
                st.session_state.зона = определить_зону(сумма, форма, тип_сделки)
                st.rerun()
        
        with c2:
            все_тф = {**ТИПОВЫЕ_ФОРМЫ, **st.session_state.get("пользовательские_тф", {})}
            тф_опции = ["— Авто —"] + [v["название"] for v in все_тф.values()]
            тф_выбор = st.selectbox("Типовая форма", тф_опции, label_visibility="collapsed")
            
            код_тф = тип_док.get("тип") if тф_выбор == "— Авто —" else None
            if тф_выбор != "— Авто —":
                for k, v in все_тф.items():
                    if v["название"] == тф_выбор:
                        код_тф = k
                        break
        
        with c3:
            if st.button("📊 RAG-сличение", type="primary", use_container_width=True):
                if код_тф and код_тф in все_тф:
                    st.session_state.rag = анализ_rag(st.session_state.текст, код_тф)
                    st.rerun()
                else:
                    st.error("Выберите типовую форму")
        
        # AI
        api = st.session_state.get("api_ключи", {})
        есть_ai = any(api.get(p) for p in AI_ПРОВАЙДЕРЫ)
        
        if есть_ai:
            if st.button("🤖 AI-экспертиза", type="primary", use_container_width=True):
                placeholder = st.empty()
                placeholder.markdown('''
                <div class="loading-train">
                    <div class="train">🚂🚃🚃🚃</div>
                    <div class="text">AI анализирует договор...</div>
                </div>
                ''', unsafe_allow_html=True)
                
                rag = st.session_state.get("rag") or {"нарушения": []}
                ok, результат = ai_анализ(st.session_state.текст, извл, rag)
                placeholder.empty()
                
                if ok:
                    st.session_state.ai = результат
                    st.rerun()
                else:
                    st.error(результат)
        else:
            st.info("Для AI-анализа добавьте API-ключ в Настройках")
        
        # ========== РЕЗУЛЬТАТЫ ==========
        
        # Зона
        if st.session_state.зона:
            з = st.session_state.зона
            emoji = {"зелёная": "🟢", "жёлтая": "🟡", "красная": "🔴"}.get(з["зона"], "⚪")
            название = {"зелёная": "ЗЕЛЁНАЯ ЗОНА", "жёлтая": "ЖЁЛТАЯ ЗОНА", "красная": "КРАСНАЯ ЗОНА"}.get(з["зона"], "")
            
            st.markdown(f'''
            <div class="zone-card {з["зона"]}">
                <h3>{emoji} {название}</h3>
                <p>{з["причина"]}</p>
                <p><strong>Требуется ЮД:</strong> {"Да" if з["юд"] else "Нет"} | <strong>Срок:</strong> {з["срок"]} дн.</p>
            </div>
            ''', unsafe_allow_html=True)
        
        # RAG
        if st.session_state.rag:
            показать_rag()
        
        # AI
        if st.session_state.ai:
            st.markdown('<div class="npk-section-title">Экспертное заключение AI</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="ai-result">{st.session_state.ai}</div>', unsafe_allow_html=True)


def показать_rag():
    rag = st.session_state.rag
    
    st.markdown(f'<div class="npk-section-title">Результаты RAG-сличения: {rag.get("название_тф", "")}</div>', unsafe_allow_html=True)
    
    # Метрики
    соотв = rag.get("соответствие", 0)
    цвет_класс = "green" if соотв >= 70 else ("yellow" if соотв >= 40 else "red")
    
    st.markdown(f'''
    <div class="npk-metrics">
        <div class="npk-metric">
            <div class="npk-metric-value {цвет_класс}">{соотв}%</div>
            <div class="npk-metric-label">Соответствие ТФ</div>
        </div>
        <div class="npk-metric">
            <div class="npk-metric-value red">{rag.get("красных", 0)}</div>
            <div class="npk-metric-label">Критических</div>
        </div>
        <div class="npk-metric">
            <div class="npk-metric-value yellow">{rag.get("жёлтых", 0)}</div>
            <div class="npk-metric-label">Замечаний</div>
        </div>
        <div class="npk-metric">
            <div class="npk-metric-value">{rag.get("вердикт", "")}</div>
            <div class="npk-metric-label">Вердикт</div>
        </div>
    </div>
    ''', unsafe_allow_html=True)
    
    st.markdown(f"**{rag.get('резюме', '')}**")
    
    # Нарушения
    нарушения = rag.get("нарушения", [])
    красные = [н for н in нарушения if н["критичность"] == "красный"]
    жёлтые = [н for н in нарушения if н["критичность"] == "жёлтый"]
    
    if красные:
        st.markdown('<div class="npk-section-title" style="color:#c41e3a;">Критические несоответствия</div>', unsafe_allow_html=True)
        for н in красные:
            пункт = f"<strong>Пункт {н['пункт']}</strong> — " if н.get("пункт") else ""
            st.markdown(f'''
            <div class="risk-card red">
                {пункт}Нарушение эталона ТФ
                <div class="context">{н.get("контекст", "")[:250]}</div>
                <strong style="color:#22c55e;">✅ Эталон:</strong> {н.get("эталон", "")}<br>
                <strong style="color:#3b82f6;">➡️ Рекомендация:</strong> Изменить на формулировку из ТФ
            </div>
            ''', unsafe_allow_html=True)
    
    if жёлтые:
        with st.expander(f"Замечания ({len(жёлтые)})"):
            for н in жёлтые:
                пункт = f"п.{н['пункт']} — " if н.get("пункт") else ""
                st.markdown(f'''
                <div class="risk-card yellow">
                    <strong>{пункт}{н.get("эталон", "")}</strong><br>
                    <small style="color:#666;">{н.get("контекст", "")[:150]}</small>
                </div>
                ''', unsafe_allow_html=True)

# ============================================================================
# ВКЛАДКА ИСТОРИИ
# ============================================================================

def вкладка_истории():
    st.markdown('<div class="npk-title">ИСТОРИЯ</div>', unsafe_allow_html=True)
    
    история = st.session_state.get("история", [])
    
    if not история:
        st.info("История пуста")
        return
    
    for з in история:
        emoji = {"зелёная": "🟢", "жёлтая": "🟡", "красная": "🔴"}.get(з.get("зона", ""), "⚪")
        st.markdown(f'''
        <div class="npk-table-row" style="padding:15px;background:#f5f5f5;border-radius:4px;margin:10px 0;">
            <div>{emoji} <strong>{з.get("контрагент", "Н/Д")}</strong></div>
            <div style="color:#666;">{з.get("сумма", 0):,.0f}₽ | {з.get("дата", "")}</div>
        </div>
        ''', unsafe_allow_html=True)
    
    if st.button("Очистить историю"):
        st.session_state.история = []
        st.rerun()


# ============================================================================
# ВКЛАДКА НАСТРОЕК
# ============================================================================

def вкладка_настроек():
    st.markdown('<div class="npk-title">НАСТРОЙКИ</div>', unsafe_allow_html=True)
    st.success("Режим администратора")
    
    tabs = st.tabs(["Организация", "Пороги", "API-ключи", "Типовые формы"])
    
    with tabs[0]:
        st.markdown('<div class="npk-section-title">Реквизиты организации</div>', unsafe_allow_html=True)
        орг = st.session_state.get("орг", DEFAULT_ORG)
        
        new_name = st.text_input("Название", value=орг.get("short_name", ""))
        new_inn = st.text_input("ИНН", value=орг.get("inn", ""))
        
        if st.button("Сохранить", key="save_org"):
            st.session_state.орг = {"short_name": new_name, "inn": new_inn, "full_name": new_name}
            st.success("Сохранено")
    
    with tabs[1]:
        st.markdown('<div class="npk-section-title">Пороговые значения</div>', unsafe_allow_html=True)
        пороги = st.session_state.get("пороги", DEFAULT_THRESHOLDS)
        
        new_tf = st.number_input("Зелёная ТФ макс (₽)", value=пороги.get("зелёная_тф_макс", 100000), step=10000)
        new_ntf = st.number_input("Зелёная нетиповая макс (₽)", value=пороги.get("зелёная_нетф_макс", 50000), step=10000)
        new_yellow = st.number_input("Жёлтая → Красная (₽)", value=пороги.get("жёлтая_макс", 5000000), step=100000)
        
        if st.button("Сохранить", key="save_thresh"):
            st.session_state.пороги = {"зелёная_тф_макс": new_tf, "зелёная_нетф_макс": new_ntf, "жёлтая_макс": new_yellow}
            st.success("Сохранено")
    
    with tabs[2]:
        st.markdown('<div class="npk-section-title">API-ключи для AI</div>', unsafe_allow_html=True)
        
        api = st.session_state.get("api_ключи", {})
        
        for pid, info in AI_ПРОВАЙДЕРЫ.items():
            st.markdown(f'''
            <div class="npk-table-row">
                <div class="npk-table-label"><strong>{info["название"]}</strong></div>
                <div class="npk-table-value"><a href="{info["url"]}" target="_blank">{info["url"]}</a> — {info["цена"]}</div>
            </div>
            ''', unsafe_allow_html=True)
            
            новый = st.text_input(f"Ключ {info['название']}", type="password", value=api.get(pid, ""), key=f"api_{pid}", label_visibility="collapsed")
            if новый != api.get(pid, ""):
                if "api_ключи" not in st.session_state:
                    st.session_state.api_ключи = {}
                st.session_state.api_ключи[pid] = новый
        
        st.markdown("---")
        st.text_input("YandexGPT Folder ID", value=st.session_state.get("yandex_folder", ""), key="yf")
    
    with tabs[3]:
        st.markdown('<div class="npk-section-title">Типовые формы</div>', unsafe_allow_html=True)
        
        for код, тф in ТИПОВЫЕ_ФОРМЫ.items():
            st.markdown(f'''
            <div class="npk-table-row">
                <div class="npk-table-label">{тф["название"]}</div>
                <div class="npk-table-value">{тф["код"]} | {len(тф.get("пункты", {}))} эталонов</div>
            </div>
            ''', unsafe_allow_html=True)


# ============================================================================
# ГЛАВНАЯ
# ============================================================================

def главная():
    орг = st.session_state.get("орг", DEFAULT_ORG)
    
    # Хедер в стиле НПК
    st.markdown(f'''
    <div class="npk-header">
        <div class="npk-logo">
            <div class="npk-logo-icon"></div>
            <div class="npk-logo-text">
                <span>СТАРАЯ</span><br>ПЕРЕВОЗОЧНАЯ
            </div>
        </div>
    </div>
    ''', unsafe_allow_html=True)
    
    боковая_панель()
    
    # Навигация
    st.markdown('''
    <div style="display:flex;align-items:center;gap:20px;margin-bottom:20px;">
        <div class="traffic-light">
            <span class="tl-red"></span>
            <span class="tl-yellow"></span>
            <span class="tl-green"></span>
        </div>
        <div style="font-size:1.5rem;font-weight:600;color:#1a1a1a;">Регламент Светофор <span style="color:#666;font-weight:normal;">v7.8</span></div>
    </div>
    ''', unsafe_allow_html=True)
    
    if это_админ():
        tabs = st.tabs(["АНАЛИЗ", "ИСТОРИЯ", "НАСТРОЙКИ"])
        with tabs[0]:
            вкладка_анализа()
        with tabs[1]:
            вкладка_истории()
        with tabs[2]:
            вкладка_настроек()
    else:
        tabs = st.tabs(["АНАЛИЗ", "ИСТОРИЯ"])
        with tabs[0]:
            вкладка_анализа()
        with tabs[1]:
            вкладка_истории()
    
    # Футер
    st.markdown(f'''
    <div class="npk-footer">
        <strong>АО «{орг.get("short_name", "СПК")}»</strong><br>
        105066, Россия, г. Москва | ИНН: {орг.get("inn", "")}
    </div>
    ''', unsafe_allow_html=True)


def main():
    применить_стили()
    инициализация()
    
    if not st.session_state.авторизован:
        страница_входа()
    else:
        главная()


if __name__ == "__main__":
    main()
