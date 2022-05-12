import json
import time
import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

site_url = "https://cebcare.ceb.lk/Incognito/DemandMgmtSchedule"

option = webdriver.ChromeOptions()
# option.add_argument('headless')

driver = webdriver.Chrome(options=option)
driver.get(site_url)
time.sleep(2)

table_length_select = Select(driver.find_element(
    by=By.CSS_SELECTOR, value=".dataTables_length select"))
table_length_select.select_by_value('-1')
time.sleep(2)

group_names = []
for group in driver.find_elements(
        by=By.CSS_SELECTOR, value=".fc-time-grid-event .fc-title h2 span"):
    group_names.append(group.text)


time_slot_list = driver.find_elements(
    by=By.CSS_SELECTOR, value=".fc-time-grid-event")

for idx, time_slot in enumerate(time_slot_list):
    group = group_names[idx]
    time.sleep(2)
    time_slot.click()

time.sleep(4)

print("Execution Complete")
driver.close()
