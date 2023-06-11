import json
import math
from collections import defaultdict

import numpy
import tqdm
import os
import gzip
import shutil
from datetime import datetime

total_datum_reader = defaultdict(int)
total_cnt = 0
total_start_from = math.inf
total_end_at = 0


def convert_timestamp(timestamp):
    dt_object = datetime.fromtimestamp(timestamp // 1000000000)
    formatted_time = dt_object.strftime('%Y-%m-%d %H:%M:%S')
    return formatted_time


def info_print_helper(filename, cnt, start_from, end_at, cnt_dict):
    log_md_file = open("darpa-tc-cadets-info.md", "a")
    generate_speed = cnt / (end_at - start_from) * 1000000000.0
    log_md_file.write(f"#### {filename} Infomation:\n")
    log_md_file.write(f"- Length: {cnt}\n")
    log_md_file.write(f"- Start: {convert_timestamp(start_from)}\n")
    log_md_file.write(f"- End: {convert_timestamp(end_at)}\n")
    log_md_file.write(f"- Speed: {generate_speed:.2f} events/s\n")
    log_md_file.write("\n")
    log_md_file.write("| Event Name | Count |\n")
    log_md_file.write("| :--------: | :---: |\n")
    for key in sorted(cnt_dict.keys()):
        log_md_file.write(f"| {key} | {cnt_dict[key]} |\n")
    log_md_file.close()


def store_object_to_file(object_fd, object):
    object_fd.write(json.dumps(object) + "\n")


def read_json(json_file):
    global total_cnt, total_datum_reader, total_start_from, total_end_at
    object_log_file = open("darpa-tc-cadets-object.json", "a")
    datum_reader = defaultdict(int)
    datum_cnt = 0
    start_time = math.inf
    end_time = 0
    with open(json_file, encoding="utf-8") as f:
        for line in tqdm.tqdm(f, total=5000000, leave=True):
            cadet_event = json.loads(line)
            datum_item = cadet_event["datum"]
            for key, value in datum_item.items():
                datum_reader[key] = datum_reader[key] + 1
                total_datum_reader[key] = total_datum_reader[key] + 1
                datum_cnt = datum_cnt + 1
                total_cnt = total_cnt + 1
                if "timestampNanos" in value:
                    start_time = min(start_time, value["timestampNanos"])
                    end_time = max(end_time, value["timestampNanos"])
                if key != "com.bbn.tc.schema.avro.cdm20.Event":  # Is an object
                    store_object_to_file(object_log_file, cadet_event)

    total_start_from = min(total_start_from, start_time)
    total_end_at = max(total_end_at, end_time)
    info_print_helper(json_file, datum_cnt, start_time, end_time, datum_reader)
    object_log_file.close()


hostname = {
    "A3702F4C-5A0C-11E9-B8B9-D4AE52C1DBD3": "cadets-1",
    "3A541941-5B04-11E9-B2DB-D4AE52C1DBD3": "cadets-2",
    "CB02303B-654E-11E9-A80C-6C2B597E484C": "cadets-3"
}


def read_object_json(json_file):
    datum_reader = {}
    event_dict = {}
    host_cnt = defaultdict(int)
    with open(json_file, encoding="utf-8") as f:
        for line in tqdm.tqdm(f):
            cadet_event = json.loads(line)
            host_cnt[cadet_event["hostId"]] += 1
            datum_item = cadet_event["datum"]
            for key, value in datum_item.items():
                if key not in datum_reader:
                    datum_reader[key] = 0
                    event_dict[key] = defaultdict(int)
                datum_reader[key] += 1
                if "type" in value:
                    event_dict[key][value["type"]] += 1
                else:
                    event_dict[key][key] += 1

    for key in hostname.keys():
        print(f"{hostname[key]} node cnt: {host_cnt[key]}")

    for key in sorted(datum_reader.keys()):
        print(f"{key} Information")
        print(f"Total Cnt: {datum_reader[key]}")
        print("Types:")
        for key2 in sorted(event_dict[key]):
            print(f"    {key2} : {event_dict[key][key2]}")


def read_event_json(json_file):
    type_dict = defaultdict(int)
    host_cnt = defaultdict(int)
    has_size = defaultdict(int)
    size_list = []
    with open(json_file, encoding="utf-8") as f:
        for line in tqdm.tqdm(f):
            cadet_event = json.loads(line)
            datum_item = cadet_event["datum"]
            for key, value in datum_item.items():
                if key == "com.bbn.tc.schema.avro.cdm20.Event":
                    host_cnt[cadet_event["hostId"]] += 1
                    type_dict[value["type"]] += 1
                    if "size" in value and value["size"] is not None:
                        has_size[value["type"]] += 1
                        size_list.append(value["size"]["long"])

    for key in hostname.keys():
        print(f"{hostname[key]} node cnt: {host_cnt[key]}")

    for key in sorted(type_dict):
        print(f"{key} : {type_dict[key]} , has size : {has_size[key]}")

    return size_list


size_list = read_event_json("ta1-cadets-1-e5-official-2.bin.120.json")

print(numpy.mean(size_list))
print(numpy.std(size_list))

# read_object_json("darpa-tc-cadets-object.json")
#
#
# gz_dir = r"/home/csepsk/cadets"
#
# for i in range(122):
#     if i == 0:
#         filename = "ta1-cadets-1-e5-official-2.bin.gz"
#     else:
#         filename = f"ta1-cadets-1-e5-official-2.bin.{i}.gz"
#     gz_path = os.path.join(gz_dir, filename)
#     with gzip.open(gz_path, 'rb') as f_in:
#         with open(gz_path[:-3], 'wb') as f_out:
#             shutil.copyfileobj(f_in, f_out)
#     os.system(f"./json_consumer.sh {os.path.abspath(gz_path[:-3])}")
#     for j in range(3):
#         json_file = filename[:-3] + ".json"
#         if j != 0:
#             json_file = json_file + f".{j}"
#         if os.path.exists(json_file):
#             if os.path.getsize(json_file) != 0:
#                 read_json(json_file)
#             os.remove(json_file)
#     os.remove(gz_path[:-3])
# info_print_helper("Total", total_cnt, total_start_from, total_end_at, total_datum_reader)
