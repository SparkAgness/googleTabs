# https://neftregion.ru/blocks/selectregion.php?id=al
# //*[@id="regionsnow"]/div[1] - the list of all regions  mm

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium .webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import lxml
import requests
import logging
import time
import random
from fake_useragent import UserAgent
import re
from datetime import date, timedelta
import json

logging.basicConfig(
level=logging.INFO,
format='%(asctime)s - %(levelname)s - %(message)s', 
handlers=[
        logging.FileHandler('parser.log', encoding='utf-8'),
        logging.StreamHandler() 
    ]
)
logger = logging.getLogger(__name__)


class corporatePetrol():
    
    __url  = None
    __chrome_options = None
    __service = None
    __driver = None  
    __response = None    
    __headers = None
    __soup = None
    __regionsList = None
    __wait = None
    __region_parser = None
    __priceList = None 



    def __init__(self):
        self.__priceList = list()
        try:        
            logger.info('Class "corporatePetrol" initialization')            
            self.__url = "https://neftregion.ru"
            self.__headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            self.__response = requests.get(self.__url, headers=self.__headers).text     
            self.__soup = BeautifulSoup(self.__response, 'lxml') 
            self.__chrome_options = webdriver.ChromeOptions()
            self.__chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            self.__chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36")
            self.__chrome_options.add_argument("--no-sandbox")
            self.__chrome_options.add_argument("--disable-dev-shm-usage")
            self.__chrome_options.add_argument("--disable-gpu")
            self.__chrome_options.add_argument("--disable-extensions")
            self.__service = Service(ChromeDriverManager().install())
            self.__driver = webdriver.Chrome(service=self.__service, options=self.__chrome_options)
            self.__wait = WebDriverWait(self.__driver, 100, poll_frequency=1)
            self.__setRegionsList()
            logger.info('Class "corporatePetrol" has been successfull initialized')
        except Exception as e:
            logger.error(e)
        for priceInfo in self.__priceList:
            print(priceInfo)           

    def getUrl(self):
        return self.__url

    def getHeaders(self):
        return self.__headers

    def __setRegionsList(self):
        try:
            logger.info('Regions definition') 
            regionsList = self.__soup.find('body')
            regionsList = regionsList.find(class_='wrapper')
            regionsList = regionsList.find(class_='middle')
            regionsList = regionsList.find(class_='container')
            regionsList = regionsList.find(class_='content')
            regionsList = regionsList.find(class_='allregions2')
            regionsList = regionsList.find(class_='regionsnow') 
            regionsList = regionsList.find(class_='regionsnow5')
            links = regionsList.select('div.regionsnow5 ul li a')
            self.__regionsList = [link.get('href') for link in links]
            logger.info("Regions has been succefully defined:")
            # for i in self.__regionsList: print(i) #only for debug
        except Exception as e:
            logger.error(e)

    def getRegionsList(self):
        return self.__regionsList

    def getPriceList(self):
        return self.__priceList   

    def searchingValues(self):
        for i in range(len(self.__regionsList)-1):
            try:
                self.__region_parser = self.regionParser(self, i)
            except Exception as e:
                logger.error(f"{__name__} - {e}: can't to open url {self.__regionsList[i]}")
            try:
                self.__priceList.append(self.__region_parser.getParsingData())
                logger.info(f"for {self.__region_parser.getParsingData()[0]} data has been parsed")
            except Exception as e:
                logger.error(f"Cant to insert datas from {self.__regionsList[i]}")
            jsn = self.__toJson(self.__priceList)
        
    def getDriver(self):
        return self.__driver

    class regionParser:
        __url = None
        __sp = None
        __parent = None
        __driver = None
        __petrol = None
        __region = None
        __date = None
        __previousB2bPrices = None

        def __init__(self, parent, queuer: int):
            try:
                self.__parent = parent
                self.__url = parent.getUrl() + parent.getRegionsList()[queuer]
                logger.info(f"Object {self.__url} has been created")
                self.__driver = parent.getDriver()
            except Exception as e:
                logger.error(f"{__name__} - {e}: Object {self.__url} has not been created!!!")            
            self.__soupSetting()
            self.__date = date.today()
            self.__petrol = list() #92, 95, Diesel, winter-diesel
            self.__priceParsing()
            self.__previousB2bPrices = self.__previousDayB2bPricesSet()
  
        def __previousDayB2bPricesSet(self):
                try:
                    for i in range(0, 4):
                        try:
                            filename = f"{date.today() - timedelta(days=i)}_b2b.json"
                            with open(filename, 'r', encoding='utf-8') as f:
                                logger.info(f"{__name__}: previous prices has been founded at {date.today() - timedelta(days=i)}")
                                return json.load(f)
                        except Exception as e:
                            logger.error(f"{__name__} - {e}: cant to open previous prices from {date.today() - timedelta(days=i)}, trying previous date...")
                            continue
                except Exception as e:
                    logger.error(f"{__name__} - {e}: Cant to open json with previous prices, check the files, please...")
                    return None

        def __previousPricesSet(self):
            previousPrices = self.__previousDayB2bPricesSet()
            try:
                for region in previousPrices:
                    if (region.get('region', '') == self.__region):
                        return([region.get('petrol92', ''), region.get('petrol95', ''), region.get('diesel', ''), region.get('winter-diesel', '')])
            except Exception as e:
                return None        


        def __soupSetting(self):
            try:
                self.__driver.get(self.__url)                
                WebDriverWait(self.__driver, 10).until(EC.presence_of_element_located(("tag name", "body")))
                WebDriverWait(self.__driver, 10).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
                self.__sp = BeautifulSoup(self.__driver.page_source, 'lxml')                
                if (len(str(self.__sp)) > 1000):
                    logger.info(f"Connection to {self.__url} has been established successfully, soup parser is ready")      
                else:
                    logger.warning(f"Connection to {self.__url} has been established successfully, but BeautifulSoup is not ready")          
            except Exception as e:
                logger.error(f"{__name__} - {e}: can't to create connection to {self.__url}")

        def __priceParsing(self):
            try:
                pp = self.__sp.find("body")
                pp = pp.find(class_="wrapper")
                pp = pp.find(class_="middle")
                pp = pp.find(class_="container")
                pp = pp.find(class_="content")
                pp = pp.find(id = "tableindex")
                pp = pp.find(class_="tableindex")
                pp = pp.find("tbody")                
                rg = pp.find_all("tr")[0].text            
                self.__region = re.sub(r'\d+|\n', '', rg)
            except Exception as e:
                logger.error(f"{__name__} - {e}: Can't to define region")
            try:
                try:
                    pp = pp.find_all("tr")[2]
                    pp = pp.findChildren(recursive=False)                
                    pd = pp[2].findChildren(recursive=False)[1].text            
                    self.__petrol.append(int(pd.replace(" ", "")))
                except Exception as e:
                    logger.warning(f"For {self.__region} can't to find Petrol-92")
                    self.__petrol.append(0)
                try:
                    pd = pp[3].findChildren(recursive=False)[1].text
                    self.__petrol.append(int(pd.replace(" ", "")))
                except Exception as e:
                    logger.warning(f"For {self.__region} can't to find Petrol-95")
                    self.__petrol.append(0)
                try:
                    pd = pp[5].findChildren(recursive=False)[1].text
                    self.__petrol.append(int(pd.replace(" ", "")))
                except Exception as e:
                    logger.warning(f"For {self.__region} can't to find Diesel-summer")
                    self.__petrol.append(0)      
                try:
                    pd = pp[8].findChildren(recursive=False)[1].text
                    self.__petrol.append(int(pd.replace(" ", "")))
                except Exception as e:
                    logger.warning(f"For {self.__region} can't to find Diesel-winter")
                    self.__petrol.append(0)
                if self.__petrol != [0, 0, 0, 0]:     
                    logger.info(f"For {self.__region} prices are available: {self.__petrol}. Date is {self.__date}")
                else:         
                    logger.error(f"{__name__} - {e}: For {self.__region} prices aren't available {self.__date} =(")
            except Exception as e:
                logger.error(f"Cant to find prices for {self.__region}, filling it with zeroes")
                try:
                    if self.__previousB2bPrices != None: 
                        self.__petrol = self.__previousB2bPrices
                        logger.info(f"Prices for {self.__region} has been inserted from history")
                except Exception as e:
                    logger.error(f"Previous prices for {self.__region} has not been founded")
                    self.__petrol = [0, 0, 0, 0]
            
            
        def __previousPrisesSet(self):
            pass 

        def getParsingData(self):
            return [self.__region, self.__regionCodeChoise(), self.__petrol[0], self.__petrol[1], self.__petrol[2], self.__petrol[3]]
        
        def __regionCodeChoise(self):
            try:
                with open('b2b_regions.json', 'r', encoding='utf-8') as f:
                    regions_data = json.load(f) 
                    for region_item in regions_data:
                        if self.__region == region_item['region']:
                            return region_item['code']
                    return None  
            except Exception as e:
                logger.error(f"{__name__} {e}: cant to open b2b_regions.json")
                return None 
        
    class __toJson():
        __filename = None
        __parentsArray = None

        def __init__(self, parentsArray):
            self.__parentsArray = parentsArray
            self.__filename = f"{date.today()}_b2b.json"
            try:
                with open(self.__filename, "w", encoding='utf-8') as f:                    
                    data = []
                    for chain in self.__parentsArray:
                        data.append({
                            'region': chain[0],
                            'code' : chain[1],
                            'petrol92': chain[2],
                            'petrol95': chain[3],
                            'diesel': chain[4],
                            'winter-diesel': chain[5]
                        })
                    json.dump(data, f, ensure_ascii=False, indent=2)
                logger.info(f"Write to {self.__filename} {chain[0]}")
            except Exception as e:
                logger.error(f"{__name__} - {e}: cant to open {self.__filename}")
            


