import json
import os

f = open('output/group/output.json')
data = json.load(f)

final_dict = {};
for item in data:
    group_name = item["group_name"]

    for gss in item["data"]:
        gss_name = gss["gss_name"]
        feeder_name = gss["feeder_name"]
        feeding_area = gss["feeding_area"]

        if feeding_area == "N/A":
            continue

        if gss_name not in final_dict:
            final_dict[gss_name] = dict()

        for area in feeding_area:
            if area == "":
                continue
            if area not in final_dict[gss_name]:
                final_dict[gss_name][area] = dict()
            if "groups" not in final_dict[gss_name][area]:
                final_dict[gss_name][area]["groups"] = list()
            if "feeders" not in final_dict[gss_name][area]:
                final_dict[gss_name][area]["feeders"] = list()

            final_dict[gss_name][area]["groups"].append(group_name)
            final_dict[gss_name][area]["feeders"].append(feeder_name)



with open(os.path.join('output', 'group', 'test.json'), 'w') as outfile:
    json.dump(final_dict, outfile)

# print(final_dict)
    