from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium .webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import lxml
import requests
from datetime import datetime, date
import json
import lxml
import requests
import logging
import time
import random
from fake_useragent import UserAgent
import re
from fp.fp import FreeProxy


logging.basicConfig(
level=logging.INFO,
format='%(asctime)s - %(levelname)s - %(message)s', 
handlers=[
        logging.FileHandler('parser.log', encoding='utf-8'),
        logging.StreamHandler() 
    ]
)
logger = logging.getLogger(__name__)

class privatePetrol():
    __url = None
    __regions = None
    __ua = None
    __driver = None
    __chrome_options = None
    __service = None
    __wait = None
    __petrolPrice = None #92, 95, DieselFuel



    def __init__(self):
        self.__url = f"https://www.benzin-price.ru/stat_month.php?month={datetime.now().month}&year={datetime.now().year}&region_id="
        try:
            with open("regions.json", 'r') as f:
                self.__regions = json.load(f)
            logger.info(f"{__name__}: Regions list has been loaded")
        except Exception as e:
            logger.warning(f"{__name__} - {e}: Regions list hasn't been uploaded, try do something with source-file")
        self.__petrolPrice = list()
        self.__ua = UserAgent()
        self.__driverInit()
        self.__service = Service(ChromeDriverManager().install())
        self.__wait = WebDriverWait(self.__driver, 100, poll_frequency=33)
        self.__parsing()
        toJson = self.toJson(self.getPetrolPrice())
        
    def __driverInit(self):
        self.__chrome_options = Options()
        #self.__chrome_options.add_argument(f"--proxy-server=85.142.49.127:62482:1VhPW2GD:ruDrK86M")
        self.__chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        self.__chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.__chrome_options.add_experimental_option('useAutomationExtension', False)
        self.__chrome_options.add_argument('--no-sandbox')
        self.__chrome_options.add_argument('--disable-dev-shm-usage')
        self.__chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        self.__chrome_options.add_argument('--disable-extensions')
        self.__chrome_options.add_argument('--disable-plugins')
        self.__chrome_options.add_argument('--disable-images')
        self.__driver = webdriver.Chrome(options=self.__chrome_options)
        self.__driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def __parsing(self):
        for region in self.__regions:            
            try:
                time.sleep(random.uniform(30, 100))
                self.__driver.get(f"{self.__url}{region['code']}")
                time.sleep(random.uniform(3, 7))                 
                self.__driver.execute_script(f"window.scrollTo(0, {random.randint(100, 500)});")
                time.sleep(random.uniform(3, 7))            
                self.__wait.until(EC.presence_of_element_located(("tag name", "body")))
                time.sleep(random.uniform(1, 7))
                self.__wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
                time.sleep(random.uniform(1, 5))
                bsData = BeautifulSoup(self.__driver.page_source, 'lxml')
                if (len(str(bsData)) > 1000):
                    logging.info(f"{__name__}: {self.__url}{region['code']} has been opened and rethrowed to BS parsing")   
                    self.__priceParsing(bsData, region['region'], region['code']) 
                    logger.info(f"priceParsing has been gone")                  
                else:
                    logging.error(f"{__name__} - {e}: {self.__url}{region['code']} couldn't be opened, retry later")                      
                time.sleep(random.uniform(14, 65))
                # self.__driver.execute_script(f"window.scrollTo(0, {random.randint(100, 500)});")
                # time.sleep(random.uniform(3, 17))  
            except Exception as e:
                logging.error(f"{__name__} - {e}: {self.__url}{region['code']} couldn't be opened, retry later")
                #time.sleep(random.uniform(12, 5))
                #self.__driver.execute_script(f"window.scrollTo(0, {random.randint(100, 500)});")
                #time.sleep(random.uniform(60, 127))
 
    def __priceParsing(self, bs, region, code): 
        petrol92 = 2
        petrol95 = 4
        diesel = 10    
        try:    
            data = bs.find('body')        
            data = data.findChildren(recursive=False)[9]
            data = data.findChildren(recursive=False)[0]
            data = data.findChildren(recursive=False)[0]
            data = data.findChildren(recursive=False)[1]
            data = data.findChildren(recursive=False)[5]
            data = data.findChildren(recursive=False)[0]
            pricesFromthisRegionRepeat = False
            for i in range(4, 0, -1):            
                row = data.find_all("tr")[i]
                col = row.find_all("td")                
                if col[petrol92].text.strip() == '' and col[petrol95].text.strip() == '' and col[diesel].text.strip() == '' or pricesFromthisRegionRepeat==True:
                    pass
                else:
                    appendence = [region, code, col[petrol92].text, col[petrol95].text, col[diesel].text]
                    self.__petrolPrice.append(appendence)
                    pricesFromthisRegionRepeat = True
            logger.info(f"For {region}: 92 is {col[petrol92].text}, 95 is {col[petrol95].text}, diesel is {col[diesel].text}")
        except Exception as e:
            logger.error(f"{e}: for {region} can't to parse prices")
    
    def getPetrolPrice(self):
        return self.__petrolPrice
    
    class toJson():
        __parentsArray = None

        def __init__(self, parentsArray):
            self.__parentsArray = parentsArray
            self.__arrayToJson()

        def __arrayToJson(self):
            #filename = f"{datetime.date.today()}_b2c.json" 
            filename = f"{date.today()}_b2c.json"
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    data = []
                    for chain in self.__parentsArray:
                        data.append({
                            'region': chain[0],
                            'code' : chain[1],
                            'petrol92': chain[2],
                            'petrol95': chain[3],
                            'diesel': chain[4]
                        })
                    json.dump(data, f, ensure_ascii=False, indent=2)
                logger.info(f"Write to {filename} {chain[0]}")
            except Exception as e:
                logger.error(f"Data hasn't been writed to {filename} from {chain[0]}")
