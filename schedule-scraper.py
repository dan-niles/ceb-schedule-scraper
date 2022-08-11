from collections import Counter
import enum
import json
import time
import os
from DriverManager import DriverManager
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException

class TimeMode(enum.Enum):
    today = 1
    month = 2
    all = 3

class FilterMode(enum.Enum):
    none = 0
    lastId = 1
    fixedDay = 2
    fromDay = 3
    group = 4

# Define the mode to use when running and the filter value
currentTimeMode = TimeMode.month
currentFilterMode = FilterMode.fixedDay
lastIdFilterValue = "5688"
dayFilterValue = "2022-08-01"
groupFilterValue = "S"

print(f"Time mode is {currentTimeMode.name}.")
print(f"Filter mode is {currentFilterMode.name}.")
print()

# External urls to use
site_url = "https://cebcare.ceb.lk/Incognito/DemandMgmtSchedule"
data_url = "https://cebcare.ceb.lk/Incognito/GetLoadSheddingEvents"

# Prepare driver, with or without proxy
driverManager = DriverManager()
driver = driverManager.get_driver()

# Use driver to request url
try:
    driver.get(site_url)
    #driverManager.print_request()
    time.sleep(4)
except WebDriverException as e:
    if ("ERR_TUNNEL_CONNECTION_FAILED" in e.msg):
        print("Error running the scrapper: the proxy is down")
    else:
        print(e)
        print("Error running the scrapper: there is a problem with the proxy")
    exit()
except Exception as e: 
    print(e)
    print("Error running the scrapper: see the logs")
    exit()


if (currentTimeMode.value == TimeMode.today.value):
    # Click 'Month' button to request more data
    driver.find_element(by=By.CSS_SELECTOR,
                        value="button.fc-dayGridMonth-button").click()
    time.sleep(4)


def process_browser_log_entry(entry):
    response = json.loads(entry['message'])['message']
    return response


browser_log = driver.get_log('performance')

browserEvents = [process_browser_log_entry(entry) for entry in browser_log]
browserEvents = [event for event in browserEvents if 'Network.response' in event['method']]

item_index = None
for (index, event) in enumerate(browserEvents):
    try:
        if(event["params"]["response"]["url"] == data_url):
            print(f'GetLoadSheddingEvents founded')
            item_index = index
    except:
        pass

# On busy time we receive a status of 429: Too many requests received.
# TODO: implement retries
if (browserEvents[item_index]["params"]["response"]["status"] != 200):
    if (browserEvents[item_index]["params"]["response"]["status"] != 429):
        print("WARNING: CEB is busy, try again later")
    else:
        print("ERROR: wrong response from CEB, try again later")
    driver.close()
    exit()

if (item_index == None):
    print("WARNING: No data found")
    driver.close()
    exit()

data = driver.execute_cdp_cmd('Network.getResponseBody', {
                              'requestId': browserEvents[item_index]["params"]["requestId"]})
data = json.loads(data["body"])


def remap_data(item):
    obj = {
        "id": item['id'],
        "group": item['loadShedGroupId'],
        "starting_period": format_date_time(item['startTime']),
        "ending_period": format_date_time(item['endTime']),
    }
    return obj

def format_date_time(date_time):
    # Replace middle T by a space and remove last 3 character for seconds. 
    # Sample: from "2022-05-20T05:00:00" to "2022-05-20 05:00"
    return date_time.replace("T", " ")[:-3]

def less(string1, string2):
    # Compare character by character
    for idx in range(min(len(string1), len(string2))):
        # Get the "value" of the character
        ordinal1, ordinal2 = ord(string1[idx]), ord(string2[idx])
        # If the "value" is identical check the next characters
        if ordinal1 == ordinal2:
            continue
        # It's not equal so we're finished at this index and can evaluate which is smaller.
        else:
            return ordinal1 < ordinal2
    # We're out of characters and all were equal, so the result depends on the length
    # of the strings.
    return len(string1) < len(string2)

if (currentTimeMode.value == FilterMode.fixedDay.value):
    # Useful to manually identify the last inserted id.
    # Set dayFilterValue to the last date of our data and pick the id from the last element in output.json file. Then use FilterMode.lastId
    print(f"Filtering by fixedDay: {dayFilterValue}")
    filteredData = filter(lambda item: dayFilterValue in item['startTime'], data)

elif (currentTimeMode.value == FilterMode.fromDay.value):
    print(f"Filtering by fromDay: {dayFilterValue}")
    filteredData = filter(lambda item: less(dayFilterValue, item['startTime']), data)

elif (currentTimeMode.value == FilterMode.lastId.value):
    # Filtering data with id greather than lastIdFilterValue
    print(f"Filtering by lastId: {lastIdFilterValue}")
    filteredData = filter(lambda item: item['id'] > lastIdFilterValue, data)

elif (currentTimeMode.value == FilterMode.group.value):
    print(f"Filtering by group: {groupFilterValue}")
    filteredData = filter(lambda item: (item['loadShedGroupId'] == groupFilterValue), data)

else:
    filteredData = data
    
# Sort data
filteredData = sorted(filteredData, key = lambda item: (item['id']))
#filteredData = sorted(filteredData, key = lambda item: (item['loadShedGroupId'], item['startTime']))

# Count schedules by group (not needed, just for logs and visual verification)
counted = Counter((item['loadShedGroupId']) for item in filteredData)
output = [({'Group' : doctor}, k) for (doctor), k in counted.items()]
print(output)

print(f"Received schedules: {len(data)}")
print(f"Extracted schedules: {len(filteredData)}")

final_data = list(map(remap_data, filteredData))

with open(os.path.join('output', 'schedule', 'output.json'), 'w') as outfile:
    json.dump(final_data, outfile, indent=4)

print("Data saved in output.json")
driver.close()
