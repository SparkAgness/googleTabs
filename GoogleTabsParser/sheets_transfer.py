import gspread
from google.oauth2.service_account import Credentials
import logging
from datetime import datetime, date, timedelta
import json
import time

logging.basicConfig(
level=logging.INFO,
format='%(asctime)s - %(levelname)s - %(message)s', 
handlers=[
        logging.FileHandler('parser.log', encoding='utf-8'),
        logging.StreamHandler() 
    ]
)
logger = logging.getLogger(__name__)

class toSheets():
    __cPath = None
    __tableUrl = None    
    __scopes = None
    __credendial = None
    __gc = None
    __table = None
    __worksheet = None
    __b2bPrices = None
    __b2cPrices = None
    __rowForBeginning = None
    

    def __init__(self):
        self.__cPath = "credentials.json"
        self.__tableUrl = "https://docs.google.com/spreadsheets/d/1T4GWzdcDTh6-3KsfzvT-V5ULHVCXdAmyvhLpxjfTgac/edit?gid=210996568#gid=210996568&fvid=1288793110"
        #self.__tableUrl = "https://docs.google.com/spreadsheets/d/1T4GWzdcDTh6-3KsfzvT-V5ULHVCXdAmyvhLpxjfTgac/edit?pli=1&gid=210996568#gid=210996568"
        self.__scopes = [
                        'https://www.googleapis.com/auth/spreadsheets',
                        'https://www.googleapis.com/auth/drive'
                        ]
        try:
            self.__credendial = Credentials.from_service_account_file(self.__cPath, scopes = self.__scopes)
            self.__gc = gspread.authorize(self.__credendial)
            logger.info(f"API has been opened successfully")
        except Exception as e:
            logger.error(f"{__name__} - {e}: cant to authorize")
        try:
            self.__table = self.__gc.open_by_url(self.__tableUrl)
            logger.info(f"Table {self.__tableUrl} has been connected")
        except Exception as e:
            logger.error(f"{__name__} - {e}: cant to open tabe {self.__tableUrl}")
        try:
            self.__worksheet = self.__table.worksheet("Лист1")
            logger.info(f"Лист 1 has been opened")
        except Exception as e:
            logger.error(f"{__name__} - {e}: cant to open Лист 1")
        self.__b2bPrices = self.__b2bPricesSet()
        self.__b2cPrices = self.__b2cPricesSet()
        # self.__previousB2bPrices = self.__previousDayB2bPricesSet

    def __b2bPricesSet(self):
        try:                
            for i in range(0,4):
                    try:
                        filename = f"{date.today() - timedelta(days=i)}_b2b.json"
                        with open(filename, 'r', encoding='utf-8') as f: 
                            logger.info(f"{filename} has been opened")   
                            self.__previousB2BPricesDay = date.today() - timedelta(days=i+1)                       
                            return json.load(f)
                    except Exception as e:
                        logger.error(f"{e}: Cant to open {filename}, trying previous date")
                        continue 
        except Exception as e:
            logger.error(f"{__name__} - {e}: Cant to open json, check the files, please...")
            return None



    def __b2cPricesSet(self):
        try:                
            for i in range(0,4):
                    try:
                        filename = f"{date.today() - timedelta(days=i)}_b2c.json"
                        with open(filename, 'r', encoding='utf-8') as f: 
                            logger.info(f"{filename} has been opened")                            
                            return json.load(f)
                    except Exception as e:
                        logger.error(f"{e}: Cant to open {filename}, trying previous date")
                        continue 
        except Exception as e:
            logger.error(f"{__name__} - {e}: Cant to open json, check the files, please...")
            return None

    def insertData(self):
        dateColumn = self.__worksheet.col_values(1)
        rowToPaste = len(dateColumn)+1
        self.__rowForBeginning = rowToPaste 
        i = 0
        current_date = datetime.now().strftime('%Y-%m-%d')
        row = []
        for addings in self.__b2bPrices:            
            try:
                if (addings.get('region', '') == 'Санкт-Петербург и Ленинградская область'):
                    row_datas = [
                        current_date,                    
                        78,
                        'Санкт-Петербург и Ленинградская область',
                        addings.get('petrol92', ''),
                        addings.get('petrol95', ''),
                        addings.get('diesel', ''), 
                        addings.get('winter-diesel', '')
                    ]
                elif (addings.get('region', '') == 'Москва и Московская область'):
                    row_datas = [
                        current_date,                    
                        77,
                        'Москва и Московская область',
                        addings.get('petrol92', ''),
                        addings.get('petrol95', ''),
                        addings.get('diesel', ''), 
                        addings.get('winter-diesel', '')
                    ]
                else:
                    row_datas = [
                        current_date,                    
                        addings.get('code', ''),
                        addings.get('region', ''),
                        addings.get('petrol92', ''),
                        addings.get('petrol95', ''),
                        addings.get('diesel', ''), 
                        addings.get('winter-diesel', '')
                    ]
                row.append(row_datas)
                # self.__worksheet.update(f"A{rowToPaste+i}:G{rowToPaste+i}", row)
                logger.info(f"{row_datas[2]} has been added")
            except Exception as e:
                logger.error(f"{e}: cant to paste for {row_datas[2]}")
            i += 1
            # if (i%50 == 0 and i > 0): time.sleep(70)
        # time.sleep(70)
        try:
            updates = [
                {
                    'range': f"A{self.__rowForBeginning}:G{self.__rowForBeginning + len(row)}",
                    'values': row
                }
            ]
            self.__worksheet.batch_update(updates)
            logger.info(f"b2b data has been inserted")
        except Exception as e:
            logger.error(f"{e}: cant to insert b2b datas")
        self.insertB2Cdata()
        # self.__remove_first_char_in_range(self.__rowForBeginning, self.__rowForBeginning+len(self.__b2bPrices))
        # self.__setDateformat(self.__rowForBeginning, self.__rowForBeginning+len(self.__b2bPrices))
        self.__insertDate(self.__rowForBeginning, self.__rowForBeginning+len(self.__b2bPrices) - 1)

    def __insertDate(self, start_row, end_row):       
            try:
                spreadsheet_id = self.__table.id
                sheet_id = self.__worksheet.id                
                # date_obj = datetime.strptime('20.11.2025', '%d.%m.%Y').date()
                date_obj = date.today()
                base_date = date(1899, 12, 30)
                serial_number = (date_obj - base_date).days          
                requests = [{
                    'updateCells': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': start_row - 1,
                            'endRowIndex': end_row,
                            'startColumnIndex': 0,
                            'endColumnIndex': 1
                        },
                        'rows': [
                            {
                                'values': [{
                                    'userEnteredValue': {
                                        'numberValue': serial_number
                                    },
                                    'userEnteredFormat': {
                                        'numberFormat': {
                                            'type': 'DATE',
                                            'pattern': 'dd.mm.yyyy'
                                        }
                                    }
                                }]
                            } for _ in range(start_row, end_row + 1)
                        ],
                        'fields': 'userEnteredValue,userEnteredFormat.numberFormat'
                    }
                }]                
                self.__table.batch_update({'requests': requests})                
            except Exception as e:
                logger.error(f"Error inserting formatted date: {e}")

    def insertB2Cdata(self):
        appendData = []        
        for b2b in self.__b2bPrices:
            rowPaste = [0.0, 0.0, 0.0]
            for b2c in self.__b2cPrices:
                if b2c.get('code', '') == b2b.get('code', ''):                    
                    rowPaste = [
                        self.__convertToFloat(b2c.get('petrol92', '0')),
                        self.__convertToFloat(b2c.get('petrol95', '0')),
                        self.__convertToFloat(b2c.get('diesel', '0'))
                        ]
                    logger.info(f"For {b2c.get('code', '')} prices has been found: {rowPaste}")                                    
            appendData.append(rowPaste)
        updates = [
            {
                'range': f'L{self.__rowForBeginning}:N{self.__rowForBeginning + len(appendData) - 1}',
                'values': appendData
            }
        ]
        try:
            self.__worksheet.batch_update(updates)
            logger.info(f"b2c has been updated")
        except Exception as e:
            logger.error(f"{e}: cant to update b2c")

    def __convertToFloat(self, value):
        if value is None:
            return 0.0
        str_value = str(value).strip() 
        str_value = str_value.replace('\xa0', '')  # Неразрывный пробел
        str_value = str_value.replace('\u2009', '') # Тонкий пробел
        str_value = str_value.replace('\u202f', '') # Узкий неразрывный пробел
        str_value = str_value.replace(' ', '')      # Обычный пробел
        str_value = str_value.replace(',', '.')     # Запятая на точку
        cleaned = ''.join(ch for ch in str_value if ch.isdigit() or ch in '.-') 
        if not cleaned or cleaned == '-' or cleaned == '.':
            return 0.0
        try:
            return float(cleaned)
        except ValueError:
            logger.warning(f"Could not convert '{value}' (cleaned: '{cleaned}') to float")
            return 0.0

    def __setDateformat(self, start_row, end_row, column_letter="A", date_pattern="dd.mm.YYYY"):
        try:
            col_index = ord(column_letter.upper()) - 65  # A=0, B=1, etc.        
            request = {
                "repeatCell": {
                    "range": {
                        "sheetId": self.__worksheet.id,
                        "startRowIndex": start_row - 1,  # Convert to 0-based
                        "endRowIndex": end_row,          # End index is exclusive
                        "startColumnIndex": col_index,
                        "endColumnIndex": col_index + 1
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "numberFormat": {
                                "type": "DATE",
                                "pattern": date_pattern
                            }
                        }
                    },
                    "fields": "userEnteredFormat.numberFormat"
                }
            }       
            self.__table.batch_update({"requests": [request]})        
            logger.info(f"Date format applied to {column_letter}{start_row}:{column_letter}{end_row}")        
        except Exception as e:
            logger.error(f"Error setting date format: {e}")

    def __remove_first_char_in_range(self, start_row, end_row):
        try:
            spreadsheet_id = self.__table.id  # ID таблицы
            sheet_id = self.__worksheet.id    # ID листа
            requests = [{
                'updateCells': {
                    'range': {
                        'sheetId': sheet_id,  # Используем ID листа
                        'startRowIndex': start_row - 1,
                        'endRowIndex': end_row,
                        'startColumnIndex': 0,  # Column A
                        'endColumnIndex': 1
                    },
                    'rows': [
                        {
                            'values': [{
                                'userEnteredValue': {
                                    'formulaValue': f'=MID(A{i}, 2, LEN(A{i}))'
                                }
                            }]
                        } for i in range(start_row, end_row + 1)
                    ],
                    'fields': 'userEnteredValue'
                }
            }]          
            self.__table.batch_update({'requests': requests})
            logger.info(f"First character removed in range A{start_row}:A{end_row}")        
        except Exception as e:
            logger.error(f"Error removing first character: {e}")