import os
import random
import tarfile
import bz2

import pandas as pd
import torch
from pygod.generator import gen_contextual_outliers, gen_structural_outliers
from torch_geometric.data import Dataset, Data
from torch_geometric.data.data import BaseData


class _StreamSpotEdge:
    def __init__(self, departure_node, departure_node_attr, destination_node, destination_node_attr, edge_attr,
                 graph_num):
        self.departure_node = departure_node
        self.departure_node_attr = departure_node_attr
        self.destination_node = destination_node
        self.destination_node_attr = destination_node_attr
        self.edge_attr = edge_attr
        self.graph_num = graph_num


edge_type = list(range(ord('f'), ord('z') + 1)) + list(range(ord('A'), ord('H') + 1))


def expand_tensor(t: torch.Tensor, edge_cnt: int) -> torch.Tensor:
    assert t.dim() == 2 and t.shape[1] == 1, "t must be a 2D tensor with only 1 column"
    assert edge_cnt >= t.shape[0], "E must be greater than or equal to the number of rows in t"
    padding = torch.tensor([[random.choice(edge_type)] for _ in range(edge_cnt - t.shape[0])])
    return torch.cat((t, padding), dim=0)


# Node Type 5 Edge Type 29
def convert_to_type(char):
    if 'a' <= char <= 'e':
        return ord(char) - ord('a')
    elif 'f' <= char <= 'z':
        return ord(char) - ord('f')
    elif 'A' <= char <= 'H':
        return ord(char) - ord('A') + 26
    else:
        return None


# pytorch_geometric Data
# x.shape() == [num_nodes, num_node_features]
# edge_index == [2, num_edges]
# edge_attr == [num_edges, num_edge_features]

class StreamSpotDataset(Dataset):
    def __init__(self, root, transform=None, pre_transform=None, pre_filter=None, only_no_mul=False, only_mul=False,
                 database_tar="all.tar.gz"):
        self.database_tar = database_tar
        super().__init__(root, transform, pre_transform, pre_filter)
        self.only_no_mul = only_no_mul
        self.only_mul = only_mul
        assert not (only_no_mul and only_mul)

    @property
    def raw_file_names(self):
        return [self.tsv_file]

    @property
    def processed_file_names(self):
        return [f'graph_{idx}.pt' for idx in range(0, 1800)]

    def _tsv_reader(self):
        with tarfile.open(os.path.join(self.root, self.database_tar)) as tar:
            with tar.extractfile("all.tsv") as f:
                tsv_iter = pd.read_csv(f, sep='\t', chunksize=500000, header=None)
                for chunk in tsv_iter:
                    for row in chunk.itertuples():
                        yield _StreamSpotEdge(int(row[1]), ord(str(row[2])), int(row[3]), ord(str(row[4])),
                                              ord(str(row[5])),
                                              int(row[6]))

    # 生成Tensor
    def _save_tensor(self, data, current_map):
        torch.save(data, os.path.join(self.processed_dir, f'graph_{current_map}.pt'))
        print("Generated graph %d" % current_map)

    def _create_tensor(self, node_attr, edge_list, edge_attr, current_map):
        tensor_x = torch.tensor(node_attr, dtype=torch.long)
        tensor_edge_index = torch.tensor(edge_list, dtype=torch.long).t()
        tensor_edge_attr = torch.tensor(edge_attr, dtype=torch.long)
        tensor_y = torch.tensor([1] if current_map // 100 == 3 else [0])  # 300-399 为Attack数据集
        data = Data(x=tensor_x, edge_index=tensor_edge_index, edge_attr=tensor_edge_attr, y=tensor_y)

        if self.pre_filter is not None and not self.pre_filter(data):
            return

        if self.pre_transform is not None:
            data = self.pre_transform(data)

        self._save_tensor(data, current_map)

    def process(self):
        node_id_convert_dict = {}  # 将传入GNN网络的网络节点ID转化为节点ID
        node_attr = []  # 节点性质，为ASCII码
        edge_list = []  # data.edge_index 的转置列表
        edge_attr = []  # 边性质，为ASCII码

        current_map = 0
        node_cnt = 0

        for edge in self._tsv_reader():
            if current_map != edge.graph_num:
                self._create_tensor(node_attr, edge_list, edge_attr, current_map)
                # 清理工作
                current_map = edge.graph_num
                node_id_convert_dict.clear()
                node_attr.clear()
                edge_list.clear()
                edge_attr.clear()
                node_cnt = 0

            # 检查起始节点是否在记录中
            if edge.departure_node not in node_id_convert_dict:
                node_id_convert_dict[edge.departure_node] = node_cnt
                node_attr.append([edge.departure_node_attr])
                depart_id = node_cnt
                node_cnt = node_cnt + 1
            else:
                depart_id = node_id_convert_dict[edge.departure_node]
            # 检查终止节点是否在记录中
            if edge.destination_node not in node_id_convert_dict:
                node_id_convert_dict[edge.destination_node] = node_cnt
                node_attr.append([edge.destination_node_attr])
                dest_id = node_cnt
                node_cnt = node_cnt + 1
            else:
                dest_id = node_id_convert_dict[edge.destination_node]
            edge_list.append((depart_id, dest_id))
            edge_attr.append([edge.edge_attr])

        self._create_tensor(node_attr, edge_list, edge_attr, current_map)
        # 构造异常图 id:600~1199 语义异常图 id:1200~1799 结构异常图
        for idx in range(current_map + 1):
            graph = self._get_graph(idx)
            graph.x = graph.x.float()
            graph.y = torch.zeros([graph.x.size(dim=0), 1])  # Create Fake y
            graph, _ = gen_contextual_outliers(graph, n=100, k=50)
            graph.x = graph.x.long()
            graph.y = torch.tensor([1])
            self._save_tensor(graph, idx + 600)
        for idx in range(current_map + 1):
            graph = self._get_graph(idx)
            graph.x = graph.x.float()
            graph.y = torch.zeros([graph.x.size(dim=0), 1])  # Create Fake y
            graph, _ = gen_structural_outliers(graph, m=10, n=10)
            graph.x = graph.x.long()
            graph.y = torch.tensor([1])
            # 补齐边
            graph.edge_attr = expand_tensor(graph.edge_attr, graph.edge_index.shape[1])
            self._save_tensor(graph, idx + 1200)

    def len(self) -> int:
        if self.only_no_mul:
            return 500 * 3
        elif self.only_mul:
            return 100 * 3
        else:
            return 600 * 3

    def _get_graph(self, idx: int):
        return torch.load(os.path.join(self.processed_dir, f'graph_{idx}.pt'))

    def get(self, idx: int) -> BaseData:
        if self.only_no_mul:
            if idx >= 300:
                idx += 100
            if idx >= 900:
                idx += 100
            if idx >= 1200:
                idx += 100
        if self.only_mul:
            if 0 <= idx < 100:
                idx = idx + 300
            elif 100 <= idx < 200:
                idx = idx + 900
            elif 200 <= idx < 300:
                idx = idx + 1500
        return self._get_graph(idx)
