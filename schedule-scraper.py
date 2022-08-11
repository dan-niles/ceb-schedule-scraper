from collections import Counter
import json
import time
import os
from DriverManager import DriverManager
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException


site_url = "https://cebcare.ceb.lk/Incognito/DemandMgmtSchedule"
data_url = "https://cebcare.ceb.lk/Incognito/GetLoadSheddingEvents"

# Prepare driver, with or without proxy
driverManager = DriverManager()
driver = driverManager.get_driver()

# Use driver to request url
try:
    driver.get(site_url)
    #driverManager.print_request()
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

# Click 'Month' button to request more data
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

# On busy time we receive a status of 429: Too many requests recived. 
if (item_index == None or events[item_index]["params"]["response"]["status"] != 200):
    print("Data Not Found")
    driver.close()
    exit()

data = driver.execute_cdp_cmd('Network.getResponseBody', {
                              'requestId': events[item_index]["params"]["requestId"]})
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

# Manually identifying the last inserted id. 
# Uncomment this and comment the filter by lastScrapedId.
# Set lastScrapedDate to the last date of our data and pick the id from the last element in output.json file
#lastScrapedDate = "2022-08-01"
#data = filter(lambda item: (less(lastScrapedDate, item['startTime']) and item['loadShedGroupId'] == "S"), data)
#data = filter(lambda item: lastScrapedDate in item['startTime'], data)
#data = sorted(data, key = lambda item: (item['id']))

# Filtering data greather than last inserted id (lastScrapedId should be received by parameter)
lastScrapedId = "5688"
data = filter(lambda item: item['id'] > lastScrapedId, data)
data = sorted(data, key = lambda item: (item['id']))
#data = sorted(data, key = lambda item: (item['loadShedGroupId'], item['startTime']))


# Count schedules by group (not needed, just for logs and visual verification)
counted = Counter((item['loadShedGroupId']) for item in data)
output = [({'Group' : doctor}, k) for (doctor), k in counted.items()]
print(output)


final_data = list(map(remap_data, data))
print(f"Received schedules: {len(data)}")
print(f"Extracted schedules: {len(final_data)}")


with open(os.path.join('output', 'schedule', 'output.json'), 'w') as outfile:
    json.dump(final_data, outfile, indent=4)

print("Data saved in output.json")
driver.close()
