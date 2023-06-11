# 注意到，为简化实验的描述，我们应该采用单个主机建立溯源图的方式来进行检测
# 我们也遗憾的注意到，攻击log记录非常的少
# 暂定按照分钟进行边的截取，计算下来，大约每分钟约有120k条边，每台主机大约50k边，边与节点的比例约为49：1 也即1k节点数
# 暂未发现有较好的类型方法，打算采用类似streamspot的方法给节点和边加标签
# 出现的节点标签：共11种 principal group dir file socket pipe_unnamed socket_pair netflow principal src-sink-ipc process
# 出现的event标签 共31种
# 其中部分有size标签：EVENT_LSEEK EVENT_MMAP EVENT_READ EVENT_RECVFROM EVENT_RECVMSG EVENT_SENDMSG EVENT_SENDTO EVENT_WRITE
# 出现的Event标签：以100json为例：
import copy
import fileinput
import json
import os.path
import sqlite3
import random

import torch
import torch_geometric.data
from pygod.generator import gen_contextual_outliers, gen_structural_outliers
from tqdm import tqdm


# 长度9


# Node attributes: 9维 one-hot向量

# event attribute: 第一维为31维 one-hot向量

# 表 Object 字段 uuid host(0-3) object_type(0-8) parentSubject(uuid) localPrincipal(uuid)
class ObjectDatabase:
    @property
    def node_type_dict(self):
        node_type_list = ['FILE_OBJECT_DIR', 'FILE_OBJECT_FILE', 'FILE_OBJECT_UNIX_SOCKET', 'IPC_OBJECT_PIPE_UNNAMED',
                          'IPC_OBJECT_SOCKET_PAIR', 'com.bbn.tc.schema.avro.cdm20.NetFlowObject', 'PRINCIPAL_LOCAL',
                          'SRCSINK_IPC', 'SUBJECT_PROCESS', 'Unknown']
        return {node_type_list[index]: index for index in range(len(node_type_list))}

    def __init__(self, db="cadets-database.db"):
        self.conn = sqlite3.connect(db)
        self.object_cache = [{}, {}, {}]  # Cached from event

    def activate(self, host, uuid, node_type):
        if node_type == "com.bbn.tc.schema.avro.cdm20.Host":
            return
        self.object_cache[host][uuid] = self.node_type_dict[node_type]

    def get_node_attr(self, host, uuid):
        if uuid not in self.object_cache[host]:
            cur = self.conn.execute("SELECT type from objects where uuid = ? and host = ?", (uuid, host))
            info = cur.fetchone()
            # if info is None the node is unknown type
            if info is not None:
                return info[0]
            else:
                return self.node_type_dict["Unknown"]
        else:
            return self.object_cache[host][uuid]

    def get_subject_info(self, host, uuid):
        # 默认重复者，使用最先前的那个subject信息
        cur = self.conn.execute("SELECT parent,principal from subjects where uuid = ? and host = ?", (uuid, host))
        return cur.fetchone()


class DarpaCadets:
    # 长度56
    @property
    def event_type_dict(self):
        event_type_list = [
            "EVENT_ACCEPT", "EVENT_ADD_OBJECT_ATTRIBUTE", "EVENT_BIND", "EVENT_BLIND", "EVENT_BOOT",
            "EVENT_CHANGE_PRINCIPAL", "EVENT_CHECK_FILE_ATTRIBUTES", "EVENT_CLONE", "EVENT_CLOSE", "EVENT_CONNECT",
            "EVENT_CORRELATION", "EVENT_CREATE_OBJECT", "EVENT_CREATE_THREAD", "EVENT_DUP", "EVENT_EXECUTE",
            "EVENT_EXIT", "EVENT_FLOWS_TO", "EVENT_FCNTL", "EVENT_FORK", "EVENT_LINK", "EVENT_LOADLIBRARY",
            "EVENT_LOGCLEAR", "EVENT_LOGIN", "EVENT_LOGOUT", "EVENT_LSEEK", "EVENT_MMAP",
            "EVENT_MODIFY_FILE_ATTRIBUTES", "EVENT_MODIFY_PROCESS", "EVENT_MOUNT", "EVENT_MPROTECT", "EVENT_OPEN",
            "EVENT_OTHER", "EVENT_READ", "EVENT_READ_SOCKET_PARAMS", "EVENT_RECVFROM", "EVENT_RECVMSG",
            "EVENT_RENAME", "EVENT_SENDTO", "EVENT_SENDMSG", "EVENT_SERVICEINSTALL", "EVENT_SHM", "EVENT_SIGNAL",
            "EVENT_STARTSERVICE", "EVENT_TRUNCATE", "EVENT_UMOUNT", "EVENT_UNIT", "EVENT_UNLINK", "EVENT_UPDATE",
            "EVENT_WAIT", "EVENT_WRITE", "EVENT_WRITE_SOCKET_PARAMS", "EVENT_TEE", "EVENT_SPLICE", "EVENT_VMSPLICE",
            "EVENT_INIT_MODULE", "EVENT_FINIT_MODULE"
        ]
        return {event_type_list[i]: i for i in range(len(event_type_list))}

    host_uuid = {"A3702F4C-5A0C-11E9-B8B9-D4AE52C1DBD3": 0, "3A541941-5B04-11E9-B2DB-D4AE52C1DBD3": 1,
                 "CB02303B-654E-11E9-A80C-6C2B597E484C": 2}

    def __init__(self, json_file_list, db_file):
        self.cadets_file = fileinput.input(json_file_list, encoding="utf-8")
        self.obj_database = ObjectDatabase(db_file)

    # event_type 56*2 = 112
    # event_size
    # avr 10 000 000
    # std 80 000 000

    def get_event_iter(self):
        for line in tqdm(self.cadets_file, desc="Event Reader"):
            cadet_event = json.loads(line)
            datum_item = cadet_event["datum"]
            host = self.host_uuid[cadet_event["hostId"]]
            for key, value in datum_item.items():
                if key == "com.bbn.tc.schema.avro.cdm20.Event":
                    event_type = self.event_type_dict[value["type"]] * 2
                    if value["subject"] is None:
                        # rare ignore it
                        break
                    subject_uuid = value["subject"]["com.bbn.tc.schema.avro.cdm20.UUID"]
                    if value["predicateObject"] is None:
                        # rare consider no information exchange
                        break
                    object1_uuid = value["predicateObject"]["com.bbn.tc.schema.avro.cdm20.UUID"]
                    if value["predicateObject2"] is not None:
                        object2_uuid = value["predicateObject2"]["com.bbn.tc.schema.avro.cdm20.UUID"]
                    else:
                        object2_uuid = None
                    timestamp = value["timestampNanos"] // (60 * 1000000000)  # 1s = 1,000,000,000ns
                    yield dict(type=event_type, subject_uuid=subject_uuid, object1_uuid=object1_uuid,
                               object2_uuid=object2_uuid, host=host, timestamp=timestamp)
                else:
                    uuid = value["uuid"]
                    object_type = value["type"] if "type" in value else key
                    self.obj_database.activate(host, uuid, object_type)


# timestamp // 60
def mul_time(host, timestamp):
    if host == 1:
        return timestamp in [25966945, 25966946, 25966952]
    elif host == 0:
        return timestamp in [25966967, 25966975]
    else:
        return False


class CadetsGraphGenerator:
    def __init__(self, host_index, object_database: ObjectDatabase):
        # input_graph: x=[N个0-8] edge_index=[2,E] edge_type=[E个0-113] y=[1,1]
        self.mul_timestamp = None
        self.uuid_index = {}
        self.x = []
        self.edge_index = []
        self.edge_type = []
        self.cur_time = None

        self.host = host_index
        self.objects = object_database

    @property
    def mul_time(self):
        if self.host == 1:
            return [25966945, 25966946, 25966952]
        elif self.host == 0:
            return [25966967, 25966975]
        else:
            return []

    def _generate_graph(self, timestamp):
        tensor_x = torch.tensor(self.x, dtype=torch.long)
        tensor_edge_index = torch.tensor(self.edge_index, dtype=torch.long).t()
        tensor_edge_type = torch.tensor(self.edge_type, dtype=torch.long)
        if mul_time(self.host, timestamp):
            tensor_y = torch.ones([len(self.x), 1])
        else:
            tensor_y = torch.zeros([len(self.x), 1])
        self.uuid_index.clear()
        self.x.clear()
        self.edge_index.clear()
        self.edge_type.clear()
        return torch_geometric.data.Data(x=tensor_x, edge_index=tensor_edge_index, edge_attr=tensor_edge_type,
                                         y=tensor_y)

    def _add_edge(self, src_uuid, edge_type, dest_uuid, dest2_uuid=None):
        src_index = self.get_object_index(src_uuid)
        dest_index = self.get_object_index(dest_uuid)
        self.edge_index.append([src_index, dest_index])
        self.edge_type.append([edge_type])
        if dest2_uuid is not None:
            dest2_index = self.get_object_index(dest2_uuid)
            self.edge_index.append([src_index, dest2_index])
            self.edge_type.append([edge_type + 1])

    def add_edge(self, timestamp, src_uuid, edge_type, dest_uuid, dest2_uuid):
        graph = None
        graph_timestamp = None

        if self.cur_time is None:
            self.cur_time = timestamp
        elif self.cur_time < timestamp:
            graph = self._generate_graph(self.cur_time)
            graph_timestamp = self.cur_time
            self.cur_time = timestamp

        self._add_edge(src_uuid, edge_type, dest_uuid, dest2_uuid)
        return graph, graph_timestamp

    SUB_PROCESS = 112  # subprocess
    PRINCIPAL_PROCESS = 113  # belongs to principal

    def insert_subject_internal_edge(self, subject_uuid):
        parent, principal = self.objects.get_subject_info(self.host, subject_uuid)
        # Add subprocess edge
        if parent is not None:
            self._add_edge(parent, self.SUB_PROCESS,
                           subject_uuid)
        # Add principal edge
        if principal is not None:
            self._add_edge(principal, self.PRINCIPAL_PROCESS,
                           subject_uuid)

    def get_object_index(self, object_uuid):
        if object_uuid not in self.uuid_index:
            uuid_i = len(self.x)
            self.uuid_index[object_uuid] = uuid_i
            self.x.append([self.objects.get_node_attr(self.host, object_uuid)])
            if self.x[-1] == 8:  # SUBJECT_PROCESS
                self.insert_subject_internal_edge(object_uuid)
            return uuid_i
        else:
            return self.uuid_index[object_uuid]


class ProcessedInfo:
    # processed_list 结构
    # host-index
    #     |- [timestamp]
    #        |- original
    #        |- structural
    #        |- contextual
    def __init__(self, path):
        self.processed_cnt = None
        self.path = path
        if os.path.exists(path):
            with open(path, "r") as file:
                self.processed_dict = json.load(file)
        else:
            self.processed_dict = {}

        self.processed_list = self.get_filepath_list()
        self.processed_cnt = len(self.processed_list)

    def get_filepath_list(self):
        filepaths = []
        for value in self.processed_dict.values():
            for filepath in value.values():
                filepaths.append(filepath["original"])
                if filepath["structural"] is not None:
                    filepaths.append(filepath["structural"])
                if filepath["contextual"] is not None:
                    filepaths.append(filepath["contextual"])
        return filepaths

    def get_normal_filelist(self):
        filepaths = []
        for value in self.processed_dict.values():
            for filepath in value.values():
                filepaths.append(filepath["original"])
        return filepaths

    def get_filepath_from_list(self, idx):
        return self.processed_list[idx]

    def get_original_filepath(self, host, timestamp):
        return self.processed_dict[host][str(timestamp)]["original"]

    def get_contextual_filepath(self, host, timestamp):
        if self.processed_dict[host][str(timestamp)]["contextual"] is None:
            return self.get_original_filepath(host, timestamp)
        return self.processed_dict[host][str(timestamp)]["contextual"]

    def get_structural_filepath(self, host, timestamp):
        if self.processed_dict[host][str(timestamp)]["structural"] is None:
            return self.get_original_filepath(host, timestamp)
        return self.processed_dict[host][str(timestamp)]["structural"]

    def start_point(self, seq_length):
        start_point = []
        for host, snapshots in self.processed_dict.items():
            timestamps = list(snapshots.keys())
            timestamps = [int(timestamp) for timestamp in timestamps]
            for x in timestamps:
                if all(i in timestamps for i in range(x, x + seq_length)):
                    start_point.append((host, x))
        return start_point

    def generated_exist(self, host, timestamp):
        if timestamp in self.processed_dict[host]:
            processed_info = self.processed_dict[host][timestamp]
            return processed_info["structural"] is not None and processed_info["contextual"] is not None
        else:
            return False

    def record(self, host_index, timestamp, original, structural, contextual):
        if host_index not in self.processed_dict:
            self.processed_dict[host_index] = {}
        self.processed_dict[host_index][timestamp] = {
            "original": original,
            "structural": structural,
            "contextual": contextual
        }

    def save(self):
        self.processed_list = self.get_filepath_list()
        self.processed_cnt = len(self.processed_list)
        with open(self.path, "w") as file:
            json.dump(self.processed_dict, file)


class DarpaCadetsDataset(torch_geometric.data.Dataset):
    def __init__(self, root, transform=None, pre_transform=None, pre_filter=None, database_log_list=None,
                 object_database="cadets-database.db"):

        if database_log_list is None:
            # database_log_list = ["ta1-cadets-1-e5-official-2.bin.109.json"]
            database_log_list = ["ta1-cadets-1-e5-official-2.bin.109.json", "ta1-cadets-1-e5-official-2.bin.109.json.1",
                                 "ta1-cadets-1-e5-official-2.bin.110.json", "ta1-cadets-1-e5-official-2.bin.110.json.1",
                                 "ta1-cadets-1-e5-official-2.bin.111.json", "ta1-cadets-1-e5-official-2.bin.111.json.1",
                                 "ta1-cadets-1-e5-official-2.bin.113.json", "ta1-cadets-1-e5-official-2.bin.113.json.1",
                                 "ta1-cadets-1-e5-official-2.bin.116.json", "ta1-cadets-1-e5-official-2.bin.116.json.1"]

            # database_log_list = ["ta1-cadets-1-e5-official-2.bin.109.json", "ta1-cadets-1-e5-official-2.bin.109.json.1",
            #                      "ta1-cadets-1-e5-official-2.bin.110.json", "ta1-cadets-1-e5-official-2.bin.110.json.1",
            #                      "ta1-cadets-1-e5-official-2.bin.111.json", "ta1-cadets-1-e5-official-2.bin.111.json.1"]

        self.processed_info = ProcessedInfo(os.path.join(root, "darpa-cadets-processed-list.json"))

        self.database_log_list = database_log_list
        self.object_database = object_database

        super().__init__(root, transform, pre_transform, pre_filter)

    @property
    def raw_file_names(self):
        return [self.database_log_list, self.object_database]

    @property
    def processed_file_names(self):
        return self.processed_info.get_filepath_list()

    @staticmethod
    def _generated_contextual(graph):
        if graph.x.size(dim=0) < 500:
            return
        contextual_graph = copy.deepcopy(graph)
        contextual_graph.x = contextual_graph.x.float()
        contextual_graph.y = torch.zeros([contextual_graph.x.size(dim=0), 1])  # Create Fake y
        contextual_graph, _ = gen_contextual_outliers(contextual_graph, n=100, k=50)
        contextual_graph.x = contextual_graph.x.long()
        contextual_graph.y = torch.ones([contextual_graph.x.size(dim=0), 1])
        return contextual_graph

    @staticmethod
    def _generated_structural(graph):
        if graph.x.size(dim=0) < 500:
            return
        structural_graph = copy.deepcopy(graph)
        structural_graph.x = structural_graph.x.float()
        structural_graph.y = torch.zeros([structural_graph.x.size(dim=0), 1])  # Create Fake y
        structural_graph, _ = gen_structural_outliers(structural_graph, m=10, n=10)
        structural_graph.x = structural_graph.x.long()
        structural_graph.y = torch.ones([structural_graph.x.size(dim=0), 1])

        edge_cnt = structural_graph.edge_index.shape[1]
        edge_type = list(range(0, 112))
        padding = torch.tensor(
            [[random.choice(edge_type)] for _ in range(edge_cnt - structural_graph.edge_attr.shape[0])])
        structural_graph.edge_attr = torch.cat((structural_graph.edge_attr, padding), dim=0)
        return structural_graph

    def _save_tensor(self, graph, graph_filepath):
        graph_file_abs_path = os.path.join(self.processed_dir, graph_filepath)
        torch.save(graph, graph_file_abs_path)

    def process(self):
        database_log_list = [os.path.join(self.root, database_log) for database_log in self.database_log_list]
        object_database = os.path.join(self.root, self.object_database)
        cadets = DarpaCadets(database_log_list, object_database)
        graph_generator = [CadetsGraphGenerator(i, cadets.obj_database) for i in range(3)]
        for event_info in cadets.get_event_iter():
            cur_graph_generator = graph_generator[event_info["host"]]
            graph_host = event_info["host"]
            graph, graph_timestamp = cur_graph_generator.add_edge(event_info["timestamp"],
                                                                  event_info["subject_uuid"],
                                                                  event_info["type"],
                                                                  event_info["object1_uuid"],
                                                                  event_info["object2_uuid"])
            if graph is not None:
                # 此时已经生产了一张快照图
                contextual_graph = self._generated_contextual(graph)  # 生成语义异常图
                structural_graph = self._generated_structural(graph)  # 生成结构异常图

                graph_filepath = f'{graph_host}-{graph_timestamp}.pt'
                contextual_graph_filepath = f'{event_info["host"]}-{event_info["timestamp"]}-contextual.pt' \
                    if contextual_graph is not None else None
                structural_graph_filepath = f'{event_info["host"]}-{event_info["timestamp"]}-structural.pt' \
                    if structural_graph is not None else None

                self._save_tensor(graph, graph_filepath)
                if contextual_graph is not None:
                    self._save_tensor(contextual_graph, contextual_graph_filepath)
                if structural_graph is not None:
                    self._save_tensor(structural_graph, structural_graph_filepath)

                self.processed_info.record(host_index=graph_host,
                                           timestamp=graph_timestamp,
                                           original=graph_filepath,
                                           structural=structural_graph_filepath,
                                           contextual=contextual_graph_filepath)

        self.processed_info.save()

    def len(self):
        return self.processed_info.processed_cnt

    def get(self, idx):
        return torch.load(os.path.join(self.processed_dir, self.processed_info.get_filepath_from_list(idx)))


class DarpaNormalDataset(DarpaCadetsDataset):
    def __init__(self, root, transform=None, pre_transform=None, pre_filter=None, database_log_list=None,
                 object_database="cadets-database.db"):
        super().__init__(root, transform, pre_transform, pre_filter, database_log_list, object_database)
        self.processed_list = self.processed_info.get_normal_filelist()

    def len(self):
        return len(self.processed_list)

    def get(self, idx):
        return torch.load(os.path.join(self.processed_dir, self.processed_list[idx]))
