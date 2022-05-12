import json
import time
import os

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.by import By

site_url = "https://cebcare.ceb.lk/Incognito/DemandMgmtSchedule"
data_url = "https://cebcare.ceb.lk/Incognito/GetLoadSheddingEvents"

caps = DesiredCapabilities.CHROME
caps['goog:loggingPrefs'] = {'performance': 'ALL'}

option = webdriver.ChromeOptions()
option.add_argument('headless')

driver = webdriver.Chrome(desired_capabilities=caps, options=option)
driver.get(site_url)

time.sleep(4)
driver.find_element(by=By.CSS_SELECTOR,
                    value="button.fc-dayGridMonth-button").click()
time.sleep(4)


def process_browser_log_entry(entry):
    response = json.loads(entry['message'])['message']
    return response


browser_log = driver.get_log('performance')

events = [process_browser_log_entry(entry) for entry in browser_log]
events = [event for event in events if 'Network.response' in event['method']]

item_index = None
for (index, event) in enumerate(events):
    try:
        if(event["params"]["response"]["url"] == data_url):
            item_index = index
    except:
        pass

if (item_index == None):
    print("Data Not Found")
    driver.close()
    exit()

data = driver.execute_cdp_cmd('Network.getResponseBody', {
                              'requestId': events[item_index]["params"]["requestId"]})
data = json.loads(data["body"])


def remap_data(item):
    obj = {
        "id": item['id'],
        "group_name": item['loadShedGroupId'],
        "starting_period": item['startTime'] + ".000Z",
        "ending_period": item['endTime'] + ".000Z",
    }
    return obj


final_data = list(map(remap_data, data))

with open(os.path.join('output', 'schedule', 'output.json'), 'w') as outfile:
    json.dump(final_data, outfile)

print("Data saved in output.json")
driver.close()
