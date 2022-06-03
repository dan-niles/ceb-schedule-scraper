from collections import Counter
import json
import time
import os
from DriverManager import DriverManager
from selenium.webdriver.common.by import By


site_url = "https://cebcare.ceb.lk/Incognito/DemandMgmtSchedule"
data_url = "https://cebcare.ceb.lk/Incognito/GetLoadSheddingEvents"

driverManager = DriverManager()
driver = driverManager.get_driver()

driver.get(site_url)
driverManager.print_request()

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
        #"id": item['id'],
        "group_name": item['loadShedGroupId'],
        "starting_period": format_date_time(item['startTime']),
        "ending_period": format_date_time(item['endTime']),
    }
    return obj

def format_date_time(date_time):
    # Replace middle T by a space and remove last 3 character for seconds. 
    # Sample: from "2022-05-20T05:00:00" to "2022-05-20 05:00"
    return date_time.replace("T", " ")[:-3]

#TODO: Receive last inserted id and filter by id
#data = filter(lambda item: item['startTime']>"2022-05-22", data)

data = sorted(data, key = lambda item: (item['loadShedGroupId'], item['startTime']))

# Count schedules by group
counted = Counter((item['loadShedGroupId']) for item in data)
output = [({'Group' : doctor}, k) for (doctor), k in counted.items()]
print(output)


final_data = list(map(remap_data, data))


with open(os.path.join('output', 'schedule', 'output.json'), 'w') as outfile:
    json.dump(final_data, outfile)

print("Data saved in output.json")
driver.close()
