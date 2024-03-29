from collections import Counter, OrderedDict, defaultdict
from dateutil import parser
import enum
import json
import time
import os
import pandas as pd
from DriverManager import DriverManager
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException

site_url = "https://cebcare.ceb.lk/Incognito/DemandMgmtSchedule"
data_url = "https://cebcare.ceb.lk/Incognito/GetLoadSheddingEvents"

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

class FormatMode(enum.Enum):
    ekata = 1
    extended = 2

# Main funtion to be called when importing this script 
def scrapeSchedules(timeMode, filterMode, filterValue, formatMode):
    print(f"Time mode is {timeMode.name}.")
    print(f"Filter mode is {filterMode.name}.")
    print()

    print("Prepare the driver")
    driverManager = DriverManager()
    driver = driverManager.get_driver()

    print("Loading today data")
    requestTodayData(driver)
    
    if (timeMode.value != TimeMode.today.value):
        print("Loading current month data")
        clickOnMonthButton(driver)
        if (timeMode.value == TimeMode.all.value):
            amountOfPastMonths = 6
            for x in range(amountOfPastMonths):
                print(f"Loading {x+1} months ago data")
                clickOnPreviousButton(driver)

    data = getSchedulesFromNetworRequests(driver)
    print(f"Schedules received: {len(data)}")

    driver.close()

    data = removeDuplicatedSchedules(data)
    print(f"Schedules uniques: {len(data)}")

    filteredData = applyFilter(data, filterMode, filterValue)
    filteredData = applySorting(filteredData)
    formatted_data = applyFormat(filteredData, formatMode)

    print()
    print(f"Schedules: {len(filteredData)}")
    if (formatMode.value == FormatMode.extended.value): analizeDates(formatted_data)
    analizeGroups(formatted_data)
    if (formatMode.value == FormatMode.extended.value): analizeDurations(formatted_data)
    print(f"--> Extracted schedules: {len(filteredData)}")
    return formatted_data

def requestTodayData(driver):
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

def clickOnMonthButton(driver):
    driver.find_element(by=By.CSS_SELECTOR, value="button.fc-dayGridMonth-button").click()
    time.sleep(4)

def clickOnPreviousButton(driver):
    driver.find_element(by=By.CSS_SELECTOR, value="button.fc-prev-button").click()
    time.sleep(4)

def process_browser_log_entry(entry):
    response = json.loads(entry['message'])['message']
    return response

def getSchedulesFromNetworRequests(driver):
    # Get browser events and select the one requesting schedules
    browser_log = driver.get_log('performance')
    browserEvents = [process_browser_log_entry(entry) for entry in browser_log]
    browserEvents = [event for event in browserEvents if 'Network.response' in event['method']]
    browserEventIndexes = []
    for (index, event) in enumerate(browserEvents):
        try:
            if(event["params"]["response"]["url"] == data_url):
                #print(f'Founded GetLoadSheddingEvents #{len(browserEventIndexes)+1}')

                # TODO: implement retries
                if (browserEvents[index]["params"]["response"]["status"] != 200):
                    if (browserEvents[index]["params"]["response"]["status"] != 429):
                        # On busy time we receive a status of 429: Too many requests received.
                        print("ERROR: CEB is busy, try again later")
                    else:
                        print("ERROR: wrong response from CEB, try again later")
                    driver.close()
                    exit()
                browserEventIndexes.append(index)
        except:
            pass
    print(f"Founded {len(browserEventIndexes)} browserEvents contaning schedules")

    if (len(browserEventIndexes) == 0):
        print("ERROR: No data found in network responses")
        driver.close()
        exit()

    # Retrieve data from selected browser events
    data = []
    for browserEventIndex in browserEventIndexes:
        networkResponse = driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': browserEvents[browserEventIndex]["params"]["requestId"]})
        dataInResponse = json.loads(networkResponse["body"])
        print(f"Parsed response with {len(dataInResponse)} schedules")
        data = data + dataInResponse
    return data

def removeDuplicatedSchedules(data):
    visited = set()
    data = [e for e in data
        if e['id'] not in visited
        and not visited.add(e['id'])]
    return data

def applyFilter(data, filterMode, filterValue):
    print(f"Filtering using {filterMode.name}{'' if filterMode.value == FilterMode.none.value else ': ' + filterValue}")
    if (filterMode.value == FilterMode.fixedDay.value):
        # Useful to manually identify the last inserted id.
        # Set dayFilterValue to the last date of our data and pick the id from the last element in output.json file. Then use FilterMode.lastId
        filteredData = filter(lambda item: filterValue in item['startTime'], data)
    elif (filterMode.value == FilterMode.fromDay.value):
        filteredData = filter(lambda item: deepSmallerThan(filterValue, item['startTime']), data)
    elif (filterMode.value == FilterMode.lastId.value):
        # Filtering data with id greather than lastIdFilterValue
        filteredData = filter(lambda item: item['id'] > filterValue, data)
    elif (filterMode.value == FilterMode.group.value):
        filteredData = filter(lambda item: (item['loadShedGroupId'] == filterValue), data)
    else:
        filteredData = data
    return filteredData

def applySorting(data):
    return sorted(data, key = lambda item: (int(item['id'])))
    #return sorted(data, key = lambda item: (item['loadShedGroupId'], item['startTime']))

def applyFormat(data, formatMode):
    if (formatMode.value == FormatMode.ekata.value):
        return list(map(remapForEkata, data))
    elif (formatMode.value == FormatMode.extended.value):
        return list(map(remapForExtended, data))

def format_date_time(date_time):
    # Replace middle T by a space and remove last 3 character for seconds. 
    # Sample: from "2022-05-20T05:00:00" to "2022-05-20 05:00"
    return date_time.replace("T", " ")[:-3]

def remapForEkata(item): 
    obj = {
        "group": item['loadShedGroupId'],
        "starting_period": format_date_time(item['startTime']),
        "ending_period": format_date_time(item['endTime'])
    }
    return obj

def remapForExtended(item):
    date = format_date_time(item['startTime']).split(" ")[0]
    fromDatetime = parser.parse(item['startTime'])
    toDatetime = parser.parse(item['endTime'])
    durationSeconds = (toDatetime - fromDatetime).total_seconds()
    durationDecimal = durationSeconds / 3600
    durationHours = int(divmod(durationSeconds, 3600)[0])
    durationMinutes = int(divmod(durationSeconds, 600)[0])
    obj = {
        "ceb_id": item['id'],
        "group": item['loadShedGroupId'],
        "starting_period": format_date_time(item['startTime']),
        "ending_period": format_date_time(item['endTime']),
        "date": date,
        "date_year": date.split("-")[0],
        "date_month": date.split("-")[1],
        "date_day": date.split("-")[2],
        "time_from": format_date_time(item['startTime']).split(" ")[1],
        "time_to": format_date_time(item['endTime']).split(" ")[1],
        "duration": durationDecimal,
        "duration_hours": durationHours,
        "duration_minutes": durationMinutes,
        "ceb_noOfFeeders": item['noOfFeeders'],
        "ceb_timeStamp": item['timeStamp'],
    }
    return obj

def analizeGroups(data):
    # Count schedules by group (not needed, just for logs and visual verification)
    counted = Counter((item['group']) for item in data)
    print(f'Groups: {len(counted.keys())}')
    output = defaultdict(list)
    for (groupName, count) in counted.items():
        output[count].append(groupName)
    output = OrderedDict(sorted(output.items(), reverse=True))
    print(f'No. of schedules by groups:')
    print(output)

def analizeDurations(data):
    # Count schedules by group (not needed, just for logs and visual verification)
    countedGroups = Counter((item['group']) for item in data)
    allAverages = defaultdict(int)
    affectedDays = defaultdict(list)
    for (groupName, count) in countedGroups.items():
        groupData = filter(lambda item: groupName in item['group'], data)
        countedDates = Counter((item['date']) for item in groupData)
        affectedDays[len(countedDates.keys())].append(groupName)
        currentGroupDurations = []
        for (date, count) in countedDates.items():
            currentDayData = filter(lambda item: date in item['date'], data)
            currentDayDurations = []
            for dayData in currentDayData:
                currentDayDurations.append(dayData['duration'])
            currentDaySum = sum(currentDayDurations) / len(currentDayDurations)
            currentGroupDurations.append(currentDaySum)
        currentGroupAverage = sum(currentGroupDurations) / len(currentGroupDurations)
        allAverages[groupName] = currentGroupAverage
    output = OrderedDict(sorted(affectedDays.items(), reverse=True))
    print(f'No. of affected days by groups:')
    print(output)
    output = defaultdict(list)
    for (groupName, average) in allAverages.items():
        output[average].append(groupName)
    output = OrderedDict(sorted(output.items(), reverse=True))
    print(f'Average hours without light on affected days by groups:')
    print(output)

def analizeDates(data):
    sortedByDate = sorted(data, key = lambda item: (item['date']))
    fromDate = sortedByDate[0]["date"]
    toDate = sortedByDate[-1]["date"]
    elapsedDays = (parser.parse(toDate) - parser.parse(fromDate)).days
    print(f'Date range: {elapsedDays} days (from {fromDate} to {toDate})')

def deepSmallerThan(string1, string2):
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

def saveOutputAsJsonFile(data):
    filePath = os.path.join('output', 'schedule', 'output.json')
    with open(filePath, 'w') as outfile:
        json.dump(data, outfile, indent=4)
    print("Data saved in output.json")

def saveOutputAsCsvFile(data):
    formattedData = []
    for item in data:
        formattedData.append(item)
    filePath = os.path.join('output', 'schedule', 'output.csv')
    df = pd.DataFrame(formattedData)
    df.to_csv (filePath, index = None)
    print("Data saved in output.csv")

def readSavedOutput():
    print("Reading schedules...")
    filePath = os.path.join('output', 'schedule', 'output.json')
    with open(filePath) as f:
        schedule_data = json.load(f)
    return schedule_data

# Main condition, will be called when running this script directly 
if __name__ == "__main__":

    # Edit following vars to define how this script will run
    lastIdFilterValue = "5688"
    dayFilterValue = "2022-02-21"
    groupFilterValue = "S"
    currentFilterValue = dayFilterValue
    currentTimeMode = TimeMode.all
    currentFilterMode = FilterMode.fromDay
    currentFormatMode = FormatMode.extended
    saveAsJson = True
    saveAsCsv = True

    # Call the main function
    schedules = scrapeSchedules(currentTimeMode, currentFilterMode, currentFilterValue, currentFormatMode)

    if (saveAsJson): saveOutputAsJsonFile(schedules)
    if (saveAsCsv): saveOutputAsCsvFile(schedules)

