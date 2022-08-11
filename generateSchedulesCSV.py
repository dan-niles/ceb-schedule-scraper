import json
import pandas as pd

def read_schedules():
    print("Reading schedules...")
    output_schedule = "./output/schedule/output.json"
    with open(output_schedule) as f:
        schedule_data = json.load(f)
    return schedule_data

        
def export_to_CSV(json_schedules):

    print("Reformating schedules...")
    data = []
    for schedule in json_schedules:
        row = {"group": schedule["group"], "starting_period": schedule["starting_period"], "ending_period": schedule["ending_period"]}
        data.append(row)
    df = pd.DataFrame(data)
    print("Saving schedules...")
    csvPath = "./output/schedule/output.csv"
    df.to_csv (csvPath, index = None)


data = read_schedules()
export_to_CSV(data)