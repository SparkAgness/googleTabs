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
from datetime import datetime
import json
import lxml
import requests
import logging
import time
import random
from fake_useragent import UserAgent
import re
from stem.control import Controller
from stem import Signal
import subprocess
import sys
import ctypes

logging.basicConfig(
level=logging.INFO,
format='%(asctime)s - %(levelname)s - %(message)s', 
handlers=[
        logging.FileHandler('parser.log', encoding='utf-8'),
        logging.StreamHandler() 
    ]
)
logger = logging.getLogger(__name__)

class privatePetrolTor():
    __portControl = None
    __sockPort = None
    __torPath = "C:\\tor\Tor Browser\Browser\\firefox.exe"
    __bridges = None

    def __init__(self):
        self.__portControl = 9051
        self.__sockPort = 9050
        self.__bridges = "meek_lite 192.0.2.20:80 url=https://1603026938.rsc.cdn77.org front=www.phpmyadmin.net utls=HelloRandomizedALPN"
        try:
            with open('torrc', 'w') as f:
                    f.write(self.__bridges)
            logger.info(f"{self.__bridges} has been setted up and using now")
        except Exception as e:
            logger.error(f"{self.__bridges} cant be used...")
        try:
            process = subprocess.Popen(
                    [self.__torPath, '-f', 'torrc'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            logger.info("Ожидаем запуск Tor (125 секунд)...")
            time.sleep(125)            
            self.__check_socks_port()
            self.__test_socks_connection()
            self.__test_tor_connection()
        #     if self.__is_tor_running():
        #         logger.info("Tor успешно запущен")
        #     else:
        #         logger.error("Tor запущен, но не отвечает")
        # except Exception as e:
        #     logger.error(f"Ошибка запуска Tor: {e}")
        # try:
        #     with Controller as controller:
        #         controller.authenticate()
        #         logger.info(f"Successfull Tor connection! Your ip is {controller.get_info('address')}")
        except Exception as e:
            logger.error(f"{e}: cant to connect to Tor")


    def __is_tor_running(self):
        """Проверяет, запущен ли Tor и отвечает на SOCKS порту"""
        try:
            response = requests.get(
                'https://httpbin.org/ip', 
                proxies=self.proxies, 
                timeout=45
            )
            logger.info(f"Tor уже запущен. IP: {response.json().get('origin')}")
            return True
        except Exception:
            return False

    def __check_socks_port(self):        
        try:
            proxies = {'http': f'socks5://127.0.0.1:{self.__sockPort}'}
            response = requests.get(
                'https://httpbin.org/ip', 
                proxies=proxies, 
                timeout=45
            )
            ip = response.json().get('origin', '')
            if ip and ip != '127.0.0.1':
                logger.info(f"🌐 SOCKS порт работает. Внешний IP: {ip}")
        except requests.exceptions.ConnectTimeout:
            logger.debug("❌ SOCKS порт: таймаут подключения")
        except requests.exceptions.ConnectionError:
            logger.debug("❌ SOCKS порт: ошибка подключения")
        except Exception as e:
            logger.debug(f"❌ SOCKS порт: {e}")

    def __test_tor_connection(self):
        try:
            proxies = {'http': f'socks5://127.0.0.1:{self.__sockPort}'}
            response = requests.get('https://check.torproject.org', proxies=proxies, timeout=60)
            
            if "Congratulations" in response.text:
                logger.info("✅ Tor работает корректно! Анонимность обеспечена.")
            else:
                logger.warning("⚠️ Tor работает, но анонимность не подтверждена")
                
        except Exception as e:
            logger.error(f"❌ Ошибка тестирования Tor: {e}")

    def __test_socks_connection(self):
        """Тестирует SOCKS соединение"""
        try:
            proxies = {'http': f'socks5://127.0.0.1:{self.socks_port}'}
            response = requests.get(
                'https://httpbin.org/ip', 
                proxies=proxies, 
                timeout=60
            )
            ip = response.json().get('origin')
            if ip and ip != '127.0.0.1':
                logger.info("socks are ready")
        except:
            logger.error("socks are not ready")