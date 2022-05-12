import json
import time
import os

from selenium import webdriver

site_url = "https://cebcare.ceb.lk/Incognito/DemandMgmtSchedule"
data_url = "https://cebcare.ceb.lk/Incognito/GetLoadSheddingEvents"

option = webdriver.ChromeOptions()
# option.add_argument('headless')

driver = webdriver.Chrome(options=option)
driver.get(site_url)

time.sleep(4)

print("Execution Complete")
driver.close()
