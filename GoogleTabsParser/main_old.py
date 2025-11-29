import os
import re
import sys
import pytz
import time
import json
import math
import logging
import datetime as dt
from dateutil.relativedelta import relativedelta

import requests
from bs4 import BeautifulSoup

import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from gspread.utils import rowcol_to_a1

# ---------------- Config ----------------

SPREADSHEET_ID = "1T4GWzdcDTh6-3KsfzvT-V5ULHVCXdAmyvhLpxjfTgac"
WORKSHEET_NAME = "Лист1"
WORKSHEET_GID = 210996568

TIMEZONE = "Europe/Moscow"
DATE_FMT = "%Y-%m-%d"
WRITE_DASH_IF_NO_REGION_DATA = True  # если False — оставит пусто
BACKFILL_LOOKBACK_DAYS = 14
REQUEST_TIMEOUT = 40
RETRY_CNT = 3
RETRY_WAIT = 2.5

# Как агрегировать закуп по поставщикам региона: "min" | "avg" | "median"
ZAKUP_AGGREGATION = "min"

# Колонки в вашей таблице (первый ряд) -> ключи данных
COLUMN_MAP = {
    "Дата": "date ",
    "Номер региона": "region_id",
    "Регион": "region ",
    "АИ92_Закуп": "zakup_ai92",
    "АИ95_Закуп": "zakup_ai95",
    "ДТ_Закуп": "zakup_dt",
    "АИ92_Розница": "retail_ai92",
    "АИ95_Розница": "retail_ai95",
    "ДТ_Розница": "retail_dt",
}

# ---------------- Regions mapping ----------------
# Имя для таблицы -> {benz_region_id, aliases для поиска на neftregion.ru}
# Алиасы помогают сопоставить "г. Москва" vs "МОСКВА" vs "Москва и МО".
REGIONS = {
    "г. Москва": {"benz_region_id": 77, "aliases": ["МОСКВА"]},
    "Московская область и новая Москва": {"benz_region_id": 50, "aliases": ["МОСКОВСКАЯ ОБЛАСТЬ", "МОСКОВСКАЯ ОБЛ.", "МОСКВА И МО"]},
    "г. Санкт-Петербург": {"benz_region_id": 78, "aliases": ["САНКТ-ПЕТЕРБУРГ", "ПЕТЕРБУРГ"]},
    "Ленинградская область": {"benz_region_id": 47, "aliases": ["ЛЕНИНГРАДСКАЯ ОБЛАСТЬ", "ЛЕНИНГРАДСКАЯ ОБЛ."]},
    "Алтайский край": {"benz_region_id": 22, "aliases": ["АЛТАЙСКИЙ КРАЙ"]},
    "Амурская область": {"benz_region_id": 28, "aliases": ["АМУРСКАЯ ОБЛАСТЬ"]},
    "Архангельская область": {"benz_region_id": 29, "aliases": ["АРХАНГЕЛЬСКАЯ ОБЛАСТЬ"]},
    "Астраханская область": {"benz_region_id": 30, "aliases": ["АСТРАХАНСКАЯ ОБЛАСТЬ"]},
    "Белгородская область": {"benz_region_id": 31, "aliases": ["БЕЛГОРОДСКАЯ ОБЛАСТЬ"]},
    "Брянская область": {"benz_region_id": 32, "aliases": ["БРЯНСКАЯ ОБЛАСТЬ"]},
    "Владимирская область": {"benz_region_id": 33, "aliases": ["ВЛАДИМИРСКАЯ ОБЛАСТЬ"]},
    "Волгоградская область": {"benz_region_id": 34, "aliases": ["ВОЛГОГРАДСКАЯ ОБЛАСТЬ"]},
    "Вологодская область": {"benz_region_id": 35, "aliases": ["ВОЛОГОДСКАЯ ОБЛАСТЬ"]},
    "Воронежская область": {"benz_region_id": 36, "aliases": ["ВОРОНЕЖСКАЯ ОБЛАСТЬ"]},
    "Еврейская автономная область": {"benz_region_id": 79, "aliases": ["ЕВРЕЙСКАЯ АВТОНОМНАЯ ОБЛАСТЬ", "ЕАО"]},
    "Забайкальский край": {"benz_region_id": 75, "aliases": ["ЗАБАЙКАЛЬСКИЙ КРАЙ"]},
    "Ивановская область": {"benz_region_id": 37, "aliases": ["ИВАНОВСКАЯ ОБЛАСТЬ"]},
    "Иркутская область": {"benz_region_id": 38, "aliases": ["ИРКУТСКАЯ ОБЛАСТЬ"]},
    "Кабардино-Балкарская Республика": {"benz_region_id": 7, "aliases": ["КАБАРДИНО-БАЛКАРСКАЯ РЕСПУБЛИКА", "КБР"]},
    "Калининградская область": {"benz_region_id": 39, "aliases": ["КАЛИНИНГРАДСКАЯ ОБЛАСТЬ"]},
    "Калужская область": {"benz_region_id": 40, "aliases": ["КАЛУЖСКАЯ ОБЛАСТЬ"]},
    "Камчатский край": {"benz_region_id": 41, "aliases": ["КАМЧАТСКИЙ КРАЙ"]},
    "Кемеровская область": {"benz_region_id": 42, "aliases": ["КЕМЕРОВСКАЯ ОБЛАСТЬ"]},
    "Кировская область": {"benz_region_id": 43, "aliases": ["КИРОВСКАЯ ОБЛАСТЬ"]},
    "Костромская область": {"benz_region_id": 44, "aliases": ["КОСТРОМСКАЯ ОБЛАСТЬ"]},
    "Краснодарский край": {"benz_region_id": 23, "aliases": ["КРАСНОДАРСКИЙ КРАЙ"]},
    "Красноярский край": {"benz_region_id": 24, "aliases": ["КРАСНОЯРСКИЙ КРАЙ"]},
    "Курганская область": {"benz_region_id": 45, "aliases": ["КУРГАНСКАЯ ОБЛАСТЬ"]},
    "Курская область": {"benz_region_id": 46, "aliases": ["КУРСКАЯ ОБЛАСТЬ"]},
    "Липецкая область": {"benz_region_id": 48, "aliases": ["ЛИПЕЦКАЯ ОБЛАСТЬ"]},
    "Магаданская область": {"benz_region_id": 49, "aliases": ["МАГАДАНСКАЯ ОБЛАСТЬ"]},
    "Мурманская область": {"benz_region_id": 51, "aliases": ["МУРМАНСКАЯ ОБЛАСТЬ"]},
    "Ненецкий автономный округ": {"benz_region_id": 83, "aliases": ["НЕНЕЦКИЙ АО", "НАО", "НЕНЕЦКИЙ АВТОНОМНЫЙ ОКРУГ"]},
    "Нижегородская область": {"benz_region_id": 52, "aliases": ["НИЖЕГОРОДСКАЯ ОБЛАСТЬ"]},
    "Новгородская область": {"benz_region_id": 53, "aliases": ["НОВГОРОДСКАЯ ОБЛАСТЬ"]},
    "Новосибирская область": {"benz_region_id": 54, "aliases": ["НОВОСИБИРСКАЯ ОБЛАСТЬ"]},
    "Омская область": {"benz_region_id": 55, "aliases": ["ОМСКАЯ ОБЛАСТЬ"]},
    "Оренбургская область": {"benz_region_id": 56, "aliases": ["ОРЕНБУРГСКАЯ ОБЛАСТЬ"]},
    "Орловская область": {"benz_region_id": 57, "aliases": ["ОРЛОВСКАЯ ОБЛАСТЬ"]},
    "Пензенская область": {"benz_region_id": 58, "aliases": ["ПЕНЗЕНСКАЯ ОБЛАСТЬ"]},
    "Пермский край": {"benz_region_id": 59, "aliases": ["ПЕРМСКИЙ КРАЙ"]},
    "Приморский край": {"benz_region_id": 25, "aliases": ["ПРИМОРСКИЙ КРАЙ"]},
    "Псковская область": {"benz_region_id": 60, "aliases": ["ПСКОВСКАЯ ОБЛАСТЬ"]},
    "Республика Адыгея": {"benz_region_id": 1, "aliases": ["РЕСПУБЛИКА АДЫГЕЯ"]},
    "Республика Алтай (Горный Алтай)": {"benz_region_id": 4, "aliases": ["РЕСПУБЛИКА АЛТАЙ"]},
    "Республика Башкортостан": {"benz_region_id": 2, "aliases": ["РЕСПУБЛИКА БАШКОРТОСТАН"]},
    "Республика Бурятия": {"benz_region_id": 3, "aliases": ["РЕСПУБЛИКА БУРЯТИЯ"]},
    "Республика Дагестан": {"benz_region_id": 5, "aliases": ["РЕСПУБЛИКА ДАГЕСТАН"]},
    "Республика Ингушетия": {"benz_region_id": 6, "aliases": ["РЕСПУБЛИКА ИНГУШЕТИЯ"]},
    "Республика Калмыкия": {"benz_region_id": 8, "aliases": ["РЕСПУБЛИКА КАЛМЫКИЯ"]},
    "Республика Карачаево-Черкесия": {"benz_region_id": 9, "aliases": ["КАРАЧАЕВО-ЧЕРКЕССКАЯ РЕСПУБЛИКА"]},
    "Республика Карелия": {"benz_region_id": 10, "aliases": ["РЕСПУБЛИКА КАРЕЛИЯ"]},
    "Республика Коми": {"benz_region_id": 11, "aliases": ["РЕСПУБЛИКА КОМИ"]},
    "Республика Марий Эл": {"benz_region_id": 12, "aliases": ["РЕСПУБЛИКА МАРИЙ ЭЛ"]},
    "Республика Мордовия": {"benz_region_id": 13, "aliases": ["РЕСПУБЛИКА МОРДОВИЯ"]},
    "Республика Саха (Якутия)": {"benz_region_id": 14, "aliases": ["РЕСПУБЛИКА САХА", "ЯКУТИЯ"]},
    "Республика Северная Осетия-Алания": {"benz_region_id": 15, "aliases": ["СЕВЕРНАЯ ОСЕТИЯ-АЛАНИЯ"]},
    "Республика Татарстан": {"benz_region_id": 16, "aliases": ["РЕСПУБЛИКА ТАТАРСТАН"]},
    "Республика Тыва": {"benz_region_id": 17, "aliases": ["РЕСПУБЛИКА ТЫВА", "ТУВА"]},
    "Республика Хакасия": {"benz_region_id": 19, "aliases": ["РЕСПУБЛИКА ХАКАСИЯ"]},
    "Ростовская область": {"benz_region_id": 61, "aliases": ["РОСТОВСКАЯ ОБЛАСТЬ"]},
    "Рязанская область": {"benz_region_id": 62, "aliases": ["РЯЗАНСКАЯ ОБЛАСТЬ"]},
    "Самарская область": {"benz_region_id": 63, "aliases": ["САМАРСКАЯ ОБЛАСТЬ"]},
    "Саратовская область": {"benz_region_id": 64, "aliases": ["САРАТОВСКАЯ ОБЛАСТЬ"]},
    "Сахалинская область": {"benz_region_id": 65, "aliases": ["САХАЛИНСКАЯ ОБЛАСТЬ"]},
    "Свердловская область": {"benz_region_id": 66, "aliases": ["СВЕРДЛОВСКАЯ ОБЛАСТЬ"]},
    "Смоленская область": {"benz_region_id": 67, "aliases": ["СМОЛЕНСКАЯ ОБЛАСТЬ"]},
    "Ставропольский край": {"benz_region_id": 26, "aliases": ["СТАВРОПОЛЬСКИЙ КРАЙ"]},
    "Тамбовская область": {"benz_region_id": 68, "aliases": ["ТАМБОВСКАЯ ОБЛАСТЬ"]},
    "Тверская область": {"benz_region_id": 69, "aliases": ["ТВЕРСКАЯ ОБЛАСТЬ"]},
    "Томская область": {"benz_region_id": 70, "aliases": ["ТОМСКАЯ ОБЛАСТЬ"]},
    "Тульская область": {"benz_region_id": 71, "aliases": ["ТУЛЬСКАЯ ОБЛАСТЬ"]},
    "Тюменская область": {"benz_region_id": 72, "aliases": ["ТЮМЕНСКАЯ ОБЛАСТЬ"]},
    "Удмуртская Республика": {"benz_region_id": 18, "aliases": ["УДМУРТСКАЯ РЕСПУБЛИКА"]},
    "Ульяновская область": {"benz_region_id": 73, "aliases": ["УЛЬЯНОВСКАЯ ОБЛАСТЬ"]},
    "Хабаровский край": {"benz_region_id": 27, "aliases": ["ХАБАРОВСКИЙ КРАЙ"]},
    "Ханты-Мансийский автономный округ - Югра": {"benz_region_id": 86, "aliases": ["ХМАО", "ХАНТЫ-МАНСИЙСКИЙ АО", "ЮГРА"]},
    "Челябинская область": {"benz_region_id": 74, "aliases": ["ЧЕЛЯБИНСКАЯ ОБЛАСТЬ"]},
    "Чеченская республика": {"benz_region_id": 95, "aliases": ["ЧЕЧЕНСКАЯ РЕСПУБЛИКА"]},
    "Чувашская Республика": {"benz_region_id": 21, "aliases": ["ЧУВАШСКАЯ РЕСПУБЛИКА"]},
    "Чукотский автономный округ": {"benz_region_id": 87, "aliases": ["ЧУКОТСКИЙ АО"]},
    "Ямало-Ненецкий автономный округ": {"benz_region_id": 89, "aliases": ["ЯНАО", "ЯМАЛО-НЕНЕЦКИЙ АО"]},
    "Ярославская область": {"benz_region_id": 76, "aliases": ["ЯРОСЛАВСКАЯ ОБЛАСТЬ"]},
    "г. Севастополь": {"benz_region_id": 2040, "aliases": ["СЕВАСТОПОЛЬ"]},
    "Крым": {"benz_region_id": 2043, "aliases": ["РЕСПУБЛИКА КРЫМ", "КРЫМ"]},
}

# ---------------- Logging ----------------

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

# ---------------- Utils ----------------

def moscow_today():
    return dt.datetime.now(pytz.timezone(TIMEZONE)).date()

def safe_float(text):
    if text is None:
        return None
    t = str(text).strip()
    if t in ("", "-", "—"):
        return None
    t = t.replace("\xa0", " ")
    t = re.sub(r"[^\d,.\- ]", "", t)  # убрать ₽, стрелки, буквы
    t = t.replace(" ", "").replace(",", ".")
    try:
        return float(t)
    except:
        return None

def median(values):
    s = sorted(values)
    n = len(s)
    if n == 0:
        return None
    if n % 2 == 1:
        return s[n//2]
    return (s[n//2 - 1] + s[n//2]) / 2.0

def aggregate(values, mode="min"):
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    if mode == "min":
        return min(vals)
    if mode == "avg":
        return sum(vals) / len(vals)
    if mode == "median":
        return median(vals)
    return min(vals)

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import random

REQUEST_TIMEOUT = (10, 60)  # (connect, read)
RETRY_CNT = 5
RETRY_WAIT_BASE = 1.5

_session = None
def get_session():
    global _session
    if _session is None:
        _session = requests.Session()
        retry = Retry(
            total=RETRY_CNT,
            connect=RETRY_CNT,
            read=RETRY_CNT,
            backoff_factor=RETRY_WAIT_BASE,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD", "OPTIONS"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=50, pool_maxsize=50)
        _session.mount("https://", adapter)
        _session.mount("http://", adapter)
        _session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
        })
    return _session

def http_get(url):
    sess = get_session()
    last_exc = None
    for attempt in range(RETRY_CNT):
        try:
            r = sess.get(url, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            return r
        except Exception as e:
            last_exc = e
            wait = (RETRY_WAIT_BASE * (2 ** attempt)) + random.uniform(0, 0.7)
            logging.warning(f"http_get: попытка {attempt+1}/{RETRY_CNT} для {url} неудачна: {e}. Повтор через {wait:.1f}с")
            time.sleep(wait)
    logging.error(f"http_get: все попытки исчерпаны для {url}: {last_exc}")
    raise last_exc

def fetch_retail_month(year, month, region_id):
    key = (year, month, region_id)
    if key in _RETAIL_MONTH_CACHE:
        return _RETAIL_MONTH_CACHE[key]

    url = f"https://www.benzin-price.ru/stat_month.php?month={month}&year={year}&region_id={region_id}"
    try:
        r = http_get(url)
    except Exception as e:
        logging.warning(f"Не удалось получить розницу {url}: {e}. Вернём пусто, включится backfill.")
        _RETAIL_MONTH_CACHE[key] = {}
        return {}

    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find("table")
    if not table:
        _RETAIL_MONTH_CACHE[key] = {}
        return {}

    headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
    if not headers:
        first_tr = table.find("tr")
        if first_tr:
            headers = [td.get_text(strip=True).lower() for td in first_tr.find_all("td")]

    def find_col(possible):
        for p in possible:
            for i, h in enumerate(headers):
                if p in h:
                    return i
        return None

    day_col = find_col(["дата", "число", "день"])
    a92_col = find_col(["аи-92", "92"])
    a95_col = find_col(["аи-95", "95"])
    dt_col  = find_col(["дт", "диз"])

    data = {}
    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if not tds or day_col is None or day_col >= len(tds):
            continue
        day_text = tds[day_col].get_text(strip=True)
        if not day_text:
            continue

        date_obj = None
        if day_text.isdigit():
            try:
                date_obj = dt.date(year, month, int(day_text))
            except:
                pass
        if not date_obj:
            for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d-%m-%Y"):
                try:
                    date_obj = dt.datetime.strptime(day_text, fmt).date()
                    break
                except:
                    pass
        if not date_obj:
            continue

        rec = {}
        if a92_col is not None and a92_col < len(tds):
            rec["retail_ai92"] = safe_float(tds[a92_col].get_text())
        if a95_col is not None and a95_col < len(tds):
            rec["retail_ai95"] = safe_float(tds[a95_col].get_text())
        if dt_col is not None and dt_col < len(tds):
            rec["retail_dt"] = safe_float(tds[dt_col].get_text())
        data[date_obj] = rec

    _RETAIL_MONTH_CACHE[key] = data
    return data

# def fetch_retail_month(year, month, region_id):
#     key = (year, month, region_id)
#     if key in _RETAIL_MONTH_CACHE:
#         return _RETAIL_MONTH_CACHE[key]

#     url = f"https://www.benzin-price.ru/stat_month.php?month={month}&year={year}&region_id={region_id}"
#     try:
#         r = http_get(url)
#     except Exception as e:
#         logging.warning(f"Не удалось получить розницу {url}: {e}. Вернём пусто, включится backfill.")
#         _RETAIL_MONTH_CACHE[key] = {}
#         return {}

#     soup = BeautifulSoup(r.text, "lxml")
#     table = soup.find("table")
#     if not table:
#         _RETAIL_MONTH_CACHE[key] = {}
#         return {}

#     headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
#     if not headers:
#         first_tr = table.find("tr")
#         if first_tr:
#             headers = [td.get_text(strip=True).lower() for td in first_tr.find_all("td")]

#     def find_col(possible):
#         for p in possible:
#             for i, h in enumerate(headers):
#                 if p in h:
#                     return i
#         return None

#     day_col = find_col(["дата", "число", "день"])
#     a92_col = find_col(["аи-92", "92"])
#     a95_col = find_col(["аи-95", "95"])
#     dt_col  = find_col(["дт", "диз"])

#     data = {}
#     for tr in table.find_all("tr"):
#         tds = tr.find_all("td")
#         if not tds or day_col is None or day_col >= len(tds):
#             continue
#         day_text = tds[day_col].get_text(strip=True)
#         if not day_text:
#             continue

#         date_obj = None
#         if day_text.isdigit():
#             try:
#                 date_obj = dt.date(year, month, int(day_text))
#             except:
#                 pass
#         if not date_obj:
#             for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d-%m-%Y"):
#                 try:
#                     date_obj = dt.datetime.strptime(day_text, fmt).date()
#                     break
#                 except:
#                     pass
#         if not date_obj:
#             continue

#         rec = {}
#         if a92_col is not None and a92_col < len(tds):
#             rec["retail_ai92"] = safe_float(tds[a92_col].get_text())
#         if a95_col is not None and a95_col < len(tds):
#             rec["retail_ai95"] = safe_float(tds[a95_col].get_text())
#         if dt_col is not None and dt_col < len(tds):
#             rec["retail_dt"] = safe_float(tds[dt_col].get_text())
#         data[date_obj] = rec

#     _RETAIL_MONTH_CACHE[key] = data
#     return data

def get_retail_for_date(date_obj, region_id):
    monthly = fetch_retail_month(date_obj.year, date_obj.month, region_id)
    return monthly.get(date_obj)

# ---------------- Google Sheets ----------------

from googleapiclient.discovery import build
from googleapiclient.discovery_cache.base import Cache
class NoCache(Cache):
    def get(self, url): return None
    def set(self, url, content): pass

def get_ws_and_api():
    creds = Credentials.from_service_account_file(
        "credentials.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"],
    )
    gc = gspread.authorize(creds)
    # Ключевое: cache_discovery=False — убирает предупреждение про file_cache
    sheets_api = build("sheets", "v4", credentials=creds, cache_discovery=False)
    sh = gc.open_by_key(SPREADSHEET_ID)
    ws = next((w for w in sh.worksheets() if w.id == WORKSHEET_GID), None)
    if ws is None:
        raise RuntimeError(f"Worksheet gid={WORKSHEET_GID} не найден")
    return sh, ws, sheets_api

def get_header(ws):
    return ws.row_values(1)

def build_index(ws, header):
    values = ws.get_all_values()
    if len(values) <= 1:
        return {}
    idx_date = header.index("Дата ") if "Дата " in header else None
    idx_region = header.index("Регион ") if "Регион " in header else None
    index = {}
    for r in values[1:]:
        if not r:
            continue
        date_s = r[idx_date] if idx_date is not None and idx_date < len(r) else ""
        region = r[idx_region] if idx_region is not None and idx_region < len(r) else ""
        if date_s and region:
            index[(date_s, region)] = r
    return index

# def get_white_mask(sheets_api, ws, start_row, end_row, start_col, end_col):
#     rng = f"'{ws.title}'!R{start_row}C{start_col}:R{end_row}C{end_col}"
#     resp = sheets_api.spreadsheets().get(
#         spreadsheetId=SPREADSHEET_ID,
#         ranges=[rng],
#         includeGridData=True
#     ).execute()
#     data = resp["sheets"][0]["data"][0].get("rowData", [])
#     mask = []
#     for r in data:
#         row_mask = []
#         for c in r.get("values", []):
#             fmt = c.get("userEnteredFormat", {}) or {}
#             bg = fmt.get("backgroundColor")
#             if not bg:
#                 row_mask.append(True)
#             else:
#                 is_white = all(abs(bg.get(k, 1.0) - 1.0) < 1e-3 for k in ("red", "green", "blue"))
#                 row_mask.append(is_white)
#         mask.append(row_mask)
#     return mask

def get_white_mask(sheets_api, ws, start_row, end_row, start_col, end_col):
    # Правильный формат диапазона без дублирования названия листа
    rng = f"!R{start_row}C{start_col}:R{end_row}C{end_col}"
    
    resp = sheets_api.spreadsheets().get(
        spreadsheetId=SPREADSHEET_ID,
        ranges=[rng],
        includeGridData=True
    ).execute()
    
    data = resp["sheets"][0]["data"][0].get("rowData", [])
    mask = []
    for r in data:
        row_mask = []
        for c in r.get("values", []):
            fmt = c.get("userEnteredFormat", {}) or {}
            bg = fmt.get("backgroundColor")
            if not bg:
                row_mask.append(True)
            else:
                is_white = all(abs(bg.get(k, 1.0) - 1.0) < 1e-3 for k in ("red", "green", "blue"))
                row_mask.append(is_white)
        mask.append(row_mask)
    return mask

from gspread.utils import rowcol_to_a1

def write_rows_respecting_white(ws, sheets_api, rows, header):
    """Упрощенная запись данных в таблицу"""
    if not rows:
        logging.info("Нет новых данных для записи")
        return

    logging.info(f"Начинаю запись {len(rows)} строк...")
    
    # Просто добавляем строки через append_row
    for i, row in enumerate(rows):
        try:
            ws.append_row(row, value_input_option="USER_ENTERED")
            if (i + 1) % 50 == 0:  # Логируем прогресс каждые 50 строк
                logging.info(f"Записано {i + 1}/{len(rows)} строк")
        except Exception as e:
            logging.error(f"Ошибка при записи строки {i + 1}: {e}")
    
    logging.info(f"Запись завершена. Всего записано строк: {len(rows)}")

# def write_rows_respecting_white(ws, sheets_api, rows, header):
#     if not rows:
#         return

#     # Узнаем текущую последнюю заполненную строку и добавим нужное количество
#     start_row = ws.row_count + 1
#     ws.add_rows(len(rows))

#     # Черновая запись
#     ws.update(f"A{start_row}", rows, value_input_option="USER_ENTERED")

#     end_row = start_row + len(rows) - 1
#     start_col = 1
#     end_col = len(header)

#     # Правильный конец диапазона в A1
#     end_a1 = rowcol_to_a1(end_row, end_col)
#     rng_a1 = f"{ws.title}!A{start_row}:{end_a1}"

#     # Текущие значения (только что записанные)
#     current = ws.get(rng_a1)

#     # Маска белых
#     mask = get_white_mask(sheets_api, ws, start_row, end_row, start_col, end_col)

#     # Оставляем значения только в белых ячейках
#     final = []
#     for r in range(len(current)):
#         row_vals = []
#         for c in range(len(current[r])):
#             if r < len(mask) and c < len(mask[r]) and mask[r][c]:
#                 row_vals.append(current[r][c])
#             else:
#                 row_vals.append("")
#         final.append(row_vals)

#     ws.update(f"A{start_row}", final, value_input_option="USER_ENTERED")

# ---------------- Retail: benzin-price.ru ----------------


    def find_col(possible):
        for p in possible:
            for i, h in enumerate(headers):
                if p in h:
                    return i
        return None
    # day_col = find_col(["дата", "число", "день"])
    # a92_col = find_col(["аи-92", "92"])
    # a95_col = find_col(["аи-95", "95"])
    # dt_col  = find_col(["дт", "диз"])
    # data = {}
    # for tr in table.find_all("tr"):
    #     tds = tr.find_all("td")
    #     if not tds:
    #         continue
    #     if day_col is None or day_col >= len(tds):
    #         continue
    #     day_text = tds[day_col].get_text(strip=True)
    #     if not day_text:
    #         continue
    #     # Парс даты
    #     date_obj = None
    #     if day_text.isdigit():
    #         try:
    #             date_obj = dt.date(year, month, int(day_text))
    #         except:
    #             continue
    #     else:
    #         # Популярные форматы
    #         for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d-%m-%Y"):
    #             try:
    #                 date_obj = dt.datetime.strptime(day_text, fmt).date()
    #                 break
    #             except:
    #                 pass
    #     if not date_obj:
    #         continue
    #     rec = {}
    #     if a92_col is not None and a92_col < len(tds):
    #         rec["retail_ai92"] = safe_float(tds[a92_col].get_text())
    #     if a95_col is not None and a95_col < len(tds):
    #         rec["retail_ai95"] = safe_float(tds[a95_col].get_text())
    #     if dt_col is not None and dt_col < len(tds):
    #         rec["retail_dt"] = safe_float(tds[dt_col].get_text())
    #     data[date_obj] = rec
    # return data

def get_retail_for_date(date_obj, region_id):
    monthly = fetch_retail_month(date_obj.year, date_obj.month, region_id)
    return monthly.get(date_obj)

# ---------------- Zakup: neftregion.ru (главная) ----------------

REGION_TITLE_NORMALIZER = re.compile(r"[^А-ЯA-ZЁ0-9 ]+", re.IGNORECASE)

def norm_title(s: str) -> str:
    if not s:
        return ""
    s = s.upper().replace("Ё", "Е")
    s = REGION_TITLE_NORMALIZER.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def region_matches(title: str, aliases: list) -> bool:
    t = norm_title(title)
    for a in aliases:
        if norm_title(a) in t:
            return True
    return False

def fetch_neftregion_main():
    r = http_get("https://neftregion.ru/")
    return BeautifulSoup(r.text, "lxml")

def extract_prices_from_region_block(block):
    # Ищем таблицу с поставщиками в блоке региона
    table = block.find("table")
    if not table:
        return None
    # Определим индексы колонок по заголовкам
    headers = [th.get_text(" ", strip=True).upper() for th in table.find_all("th")]
    # Часто в заголовках встречаются "АИ-92", "АИ92", "92", "ДТ"
    def find_col_idx(names):
        for i, h in enumerate(headers):
            for n in names:
                if n in h:
                    return i
        return None
    idx_92 = find_col_idx(["АИ-92", "АИ92", " 92 "])
    idx_95 = find_col_idx(["АИ-95", "АИ95", " 95 "])
    idx_dt = find_col_idx(["ДТ", "ДИЗ"])

    vals_92, vals_95, vals_dt = [], [], []
    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if not tds:
            continue
        # Берем по каждому столбцу число, игнорируя пустые/текстовые/стрелки
        if idx_92 is not None and idx_92 < len(tds):
            v = safe_float(tds[idx_92].get_text(" ", strip=True))
            if v is not None:
                vals_92.append(v)
        if idx_95 is not None and idx_95 < len(tds):
            v = safe_float(tds[idx_95].get_text(" ", strip=True))
            if v is not None:
                vals_95.append(v)
        if idx_dt is not None and idx_dt < len(tds):
            v = safe_float(tds[idx_dt].get_text(" ", strip=True))
            if v is not None:
                vals_dt.append(v)
    return {
        "zakup_ai92": aggregate(vals_92, ZAKUP_AGGREGATION),
        "zakup_ai95": aggregate(vals_95, ZAKUP_AGGREGATION),
        "zakup_dt": aggregate(vals_dt, ZAKUP_AGGREGATION),
    }

def get_zakup_for_region_from_main(soup, region_aliases):
    # Блоки регионов часто оформлены как секции с зеленым заголовком (h2/h3/div)
    # 1) пройдемся по всем заголовкам и найдём тот, где есть одно из алиасов
    headers = soup.find_all(["h1", "h2", "h3", "div", "span"], string=True)
    candidate_blocks = []
    for h in headers:
        text = h.get_text(" ", strip=True)
        if not text:
            continue
        if region_matches(text, region_aliases):
            # Берём ближайший родитель/сосед, где есть таблица
            # Сначала проверим родителя
            blk = h
            for _ in range(4):
                if blk and blk.find("table"):
                    candidate_blocks.append(blk)
                    break
                blk = blk.parent
            # Если не нашли — посмотрим следующих соседей
            sib = h
            for _ in range(6):
                sib = sib.find_next_sibling()
                if not sib:
                    break
                if sib.find("table"):
                    candidate_blocks.append(sib)
                    break
    # Выберем первый валидный
    for blk in candidate_blocks:
        prices = extract_prices_from_region_block(blk)
        if prices and any(prices.values()):
            return prices
    # fallback: глобально искать секцию, где в тексте встречается алиас и есть таблица
    for sec in soup.find_all(["section", "div"]):
        text = sec.get_text(" ", strip=True)[:500].upper() if sec else ""
        if any(norm_title(a) in norm_title(text) for a in region_aliases):
            prices = extract_prices_from_region_block(sec)
            if prices and any(prices.values()):
                return prices
    return None

# ---------------- Backfill ----------------

# def get_previous_values(index, date_obj, region_name, header):
#     # вернем словарь по ключам данных COLUMN_MAP, взятый из предыдущих строк листа
#     prev_date = date_obj - dt.timedelta(days=1)
#     for _ in range(BACKFILL_LOOKBACK_DAYS):
#         k = (prev_date.strftime(DATE_FMT), region_name)
#         row = index.get(k)
#         if row:
#             # построим map: имя колонки -> значение
#             col_pos = {name: i for i, name in enumerate(header)}
#             out = {}
#             for col, key in COLUMN_MAP.items():
#                 if col in col_pos and col_pos[col] < len(row):
#                     cell = row[col_pos[col]].strip()
#                     out[key] = safe_float(cell) if key not in ("date", "region", "region_id") and cell not in ("", "-") else None
#             return out
#         prev_date -= dt.timedelta(days=1)
#     return None

def get_previous_values(index, date_obj, region_name, header):
    # вернем словарь по ключам данных COLUMN_MAP, взятый из предыдущих строк листа
    prev_date = date_obj - dt.timedelta(days=1)
    for _ in range(BACKFILL_LOOKBACK_DAYS):
        k = (prev_date.strftime(DATE_FMT), region_name)
        row = index.get(k)
        if row:
            # построим map: имя колонки -> значение
            col_pos = {name: i for i, name in enumerate(header)}
            out = {}
            for col, key in COLUMN_MAP.items():
                if col in col_pos and col_pos[col] < len(row):
                    cell_value = row[col_pos[col]]
                    # ИСПРАВЛЕНИЕ: безопасно обрабатываем разные типы данных
                    if isinstance(cell_value, (int, float)):
                        # Если это число, используем как есть
                        out[key] = cell_value
                    elif isinstance(cell_value, str):
                        # Если это строка, обрабатываем её
                        cell = cell_value.strip()
                        out[key] = safe_float(cell) if key not in ("date", "region", "region_id") and cell not in ("", "-") else None
                    else:
                        # Для других типов (None и т.д.)
                        out[key] = None
            return out
        prev_date -= dt.timedelta(days=1)
    return None

def merge_current_with_backfill(current, previous):
    if current is None and previous is None:
        return None
    if current is None:
        return previous
    if previous is None:
        return current
    out = current.copy()
    for k, v in previous.items():
        if out.get(k) is None:
            out[k] = v
    return out

# ---------------- Row builder ----------------

def make_row(header, date_obj, region_name, region_id, data):
    m = {
        "date": date_obj.strftime(DATE_FMT),
        "region": region_name,
        "region_id": region_id,
        "zakup_ai92": data.get("zakup_ai92"),
        "zakup_ai95": data.get("zakup_ai95"),
        "zakup_dt": data.get("zakup_dt"),
        "retail_ai92": data.get("retail_ai92"),
        "retail_ai95": data.get("retail_ai95"),
        "retail_dt": data.get("retail_dt"),
    }
    row = []
    for col in header:
        key = COLUMN_MAP.get(col)
        if not key:
            row.append("")
            continue
        v = m.get(key)
        if key in ("date", "region", "region_id"):
            row.append(v)
        else:
            if v is None:
                row.append("-" if WRITE_DASH_IF_NO_REGION_DATA else "")
            else:
                row.append(v)
    return row


def fetch_retail_month(year, month, region_id):
    key = (year, month, region_id)
    if key in _RETAIL_MONTH_CACHE:
        return _RETAIL_MONTH_CACHE[key]
    url = f"https://www.benzin-price.ru/stat_month.php?month={month}&year={year}&region_id={region_id}"
    try:
        r = http_get(url)
    except Exception as e:
        logging.warning(f"Не удалось получить розницу {url}: {e}. Вернём пусто, включится backfill.")
        _RETAIL_MONTH_CACHE[key] = {}
        return {}
    # разбор soup ...
    _RETAIL_MONTH_CACHE[key] = data
    return data

# ---------------- Main ----------------

def main():
    sh, ws, sheets_api = get_ws_and_api()
    header = get_header(ws)
    if not {"Дата", "Регион"}.issubset(set(header)):
        logging.error("В заголовке листа должны быть колонки как минимум: 'Дата' и 'Регион'. Текущие: %s", header)
        sys.exit(1)

    # Индекс существующих строк (для backfill и для определения стартовой даты)
    index = build_index(ws, header)

    # Определим, с какой даты качать
    max_date = None
    for (date_s, _region) in index.keys():
        try:
            d = dt.datetime.strptime(date_s, DATE_FMT).date()
            if not max_date or d > max_date:
                max_date = d
        except:
            continue
    today = moscow_today()
    start_date = (max_date + dt.timedelta(days=1)) if max_date else (today - dt.timedelta(days=7))
    end_date = today

    # Предварительно скачаем DOM neftregion один раз на запуск
    soup = fetch_neftregion_main()

    # Готовим список строк для записи
    rows = []

    for date_obj in (start_date + dt.timedelta(days=i) for i in range((end_date - start_date).days + 1)):
        logging.info(f"Дата: {date_obj}")
        for region_name, meta in REGIONS.items():
            benz_id = meta["benz_region_id"]
            aliases = [region_name] + meta.get("aliases", [])
            try:
                retail = get_retail_for_date(date_obj, benz_id)
            except Exception as e:
                logging.warning(f"Розница недоступна для {region_name} на {date_obj}: {e}. Будет backfill.")
                retail = None

            try:
                zakup = get_zakup_for_region_from_main(soup, aliases)
            except Exception as e:
                logging.warning(f"Закуп недоступен для {region_name} на {date_obj}: {e}. Будет backfill.")
                zakup = None
            # Если нет на дату — попробуем backfill из таблицы
            prev_vals = get_previous_values(index, date_obj, region_name, header)
            combined = {}
            if zakup:
                combined.update(zakup)
            if retail:
                combined.update(retail)
            combined = merge_current_with_backfill(combined if (zakup or retail) else None, prev_vals)
            if not combined:
                combined = {}

            row = make_row(header, date_obj, region_name, benz_id, combined)
            rows.append(row)

            # обновим индекс в памяти (чтобы backfill работал в рамках текущего запуска)
            index[(date_obj.strftime(DATE_FMT), region_name)] = row

    if rows:
        logging.info(f"Подготовлено {len(rows)} строк для записи")
        write_rows_respecting_white(ws, sheets_api, rows, header)
    else:
        logging.info("Нет новых строк к записи.")

if __name__ == "__main__":
    main()