# 表 Objects 字段 uuid* host(0-3) object_type(0-8)
# 表 Subjects 字段 uuid* parentSubject(uuid) localPrincipal(uuid)
import json
import sqlite3

from tqdm import tqdm

conn = sqlite3.connect("cadets-database.db")
cur = conn.cursor()

conn.execute(""" CREATE TABLE IF NOT EXISTS objects
(
    uuid CHAR(36) NOT NULL,
    host TINYINT NOT NULL,
    type TINYINT NOT NULL
)
""")

conn.execute(""" CREATE TABLE IF NOT EXISTS subjects
(
    uuid CHAR(36) NOT NULL,
    host TINYINT NOT NULL,
    parent CHAR(36),
    principal CHAR(36)
)
""")

conn.execute("""CREATE INDEX IF NOT EXISTS uuid_objects ON objects (uuid)""")
conn.execute("""CREATE INDEX IF NOT EXISTS uuid_subjects ON subjects (uuid)""")
conn.execute("PRAGMA synchronous = NORMAL")

host_uuid = {"A3702F4C-5A0C-11E9-B8B9-D4AE52C1DBD3": 0, "3A541941-5B04-11E9-B2DB-D4AE52C1DBD3": 1,
             "CB02303B-654E-11E9-A80C-6C2B597E484C": 2}

node_type_list = ['FILE_OBJECT_DIR', 'FILE_OBJECT_FILE', 'FILE_OBJECT_UNIX_SOCKET', 'IPC_OBJECT_PIPE_UNNAMED',
                  'IPC_OBJECT_SOCKET_PAIR', 'com.bbn.tc.schema.avro.cdm20.NetFlowObject', 'PRINCIPAL_LOCAL',
                  'SRCSINK_IPC', 'SUBJECT_PROCESS']
node_type_dict = {node_type_list[index]: index for index in range(len(node_type_list))}
i = 1

with open("darpa-tc-cadets-object.json", encoding="utf-8") as f:
    for line in tqdm(f):
        cadets_object = json.loads(line)

        host = host_uuid[cadets_object["hostId"]]
        for key, value in cadets_object["datum"].items():
            uuid = value["uuid"]
            if key == 'com.bbn.tc.schema.avro.cdm20.Host':
                break
            object_type = node_type_dict[value["type"] if "type" in value else key]
            cur.execute("INSERT INTO objects VALUES(?,?,?)", (uuid, host, object_type))
            if key == "com.bbn.tc.schema.avro.cdm20.Subject":
                if value["parentSubject"] is not None:
                    parent = value["parentSubject"]["com.bbn.tc.schema.avro.cdm20.UUID"]
                else:
                    parent = None
                if value["localPrincipal"] is not None:
                    principal = value["localPrincipal"]["com.bbn.tc.schema.avro.cdm20.UUID"]
                cur.execute("INSERT INTO subjects VALUES(?,?,?,?)", (uuid, host, parent, principal))
            break
        if i % 10000 == 0:
            conn.commit()
            cur.close()
            cur = conn.cursor()

    conn.commit()
    cur.close()
