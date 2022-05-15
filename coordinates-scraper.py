import json
import time
import os
from DriverManager import DriverManager
from selenium.webdriver.common.by import By

site_url = "https://cebcare.ceb.lk/Incognito/DemandMgmtSchedule"

driverManager = DriverManager()
driver = driverManager.get_driver()

driver.get(site_url)
driverManager.print_request()
time.sleep(2)

def process_browser_log_entry(entry):
    response = json.loads(entry['message'])['message']
    return response

def remap_data(item):
    obj = [item['Lat'], item['Lon']]
    return obj

group_names = []
for group in driver.find_elements(
        by=By.CSS_SELECTOR, value=".fc-time-grid-event .fc-title h2 span"):
    group_names.append(group.text)


time_slot_list = driver.find_elements(
    by=By.CSS_SELECTOR, value=".fc-time-grid-event")

scrapped_groups = [] # Keep track of scraped groups to avoid multiple passes 
final_data = [] # Store final output
for idx, time_slot in enumerate(time_slot_list):
    group = group_names[idx]
    if(group in scrapped_groups):
        continue
    data_url = f"https://cebcare.ceb.lk/Incognito/GetDemandMgmtClusters?LoadShedGroupId={group}"
    print('---- scraping group', group)
    time_slot.click()
    time.sleep(4)

    browser_log = driver.get_log('performance')

    events = [process_browser_log_entry(entry) for entry in browser_log]
    events = [event for event in events if 'Network.response' in event['method']]

    item_index = None
    for (index, event) in enumerate(events):
        try:
            if(data_url in event["params"]["response"]["url"]):
                item_index = index
        except:
            pass

    if (item_index == None):
        print("Data Not Found")
        driver.close()
        exit()

    data = driver.execute_cdp_cmd('Network.getResponseBody', {
                                'requestId': events[item_index]["params"]["requestId"]})

    json_data = data["body"].replace('\\', '').strip('\"')
    data_obj = json.loads(json_data)

    remapped_data = []
    for obj in data_obj:
        zone_data = list(map(remap_data, obj["Points"]))
        remapped_data.append(zone_data)

    final_data.append({"group_name": group, "no_of_customers": data_obj[0]["NumberOfCustomers"], "zones": remapped_data})
    scrapped_groups.append(group)


with open(os.path.join('output', 'coordinates', 'output.json'), 'w') as outfile:
    json.dump(final_data, outfile, sort_keys=True)

print("Execution Complete")
driver.close()