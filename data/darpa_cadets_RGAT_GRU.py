import os
import random
import numpy.random
import torch
import torch_geometric.data

import data.darpa_cadets_RGAT


class DarpaCadetsSeqDataset(data.darpa_cadets_RGAT.DarpaCadetsDataset):
    def __init__(self, root, transform=None, pre_transform=None, pre_filter=None, database_log_list=None,
                 object_database="cadets-database.db", normal_rate=0.6, seq_length=20, dataset_size=100):
        super().__init__(root, transform, pre_transform, pre_filter, database_log_list, object_database)
        malicious_rate = 1 - normal_rate
        self.random_matrix = numpy.random.choice([0, 1, 2], size=(dataset_size, seq_length),
                                                 p=[normal_rate, malicious_rate / 2, malicious_rate / 2])
        start_point_list = self.processed_info.start_point(seq_length)
        self.start_time = [random.choice(start_point_list) for _ in range(dataset_size)]
        self.size = dataset_size
        self.seq_length = seq_length

    def len(self):
        return self.size

    def get(self, idx):
        host, start_time = self.start_time[idx]
        seq_list = []
        y_list = []
        for j in range(0, self.seq_length):
            if self.random_matrix[idx][j] == 0:
                graph_filepath = self.processed_info.get_original_filepath(host, start_time + j)
            elif self.random_matrix[idx][j] == 1:
                graph_filepath = self.processed_info.get_contextual_filepath(host, start_time + j)
            elif self.random_matrix[idx][j] == 2:
                graph_filepath = self.processed_info.get_structural_filepath(host, start_time + j)
            else:
                raise "random_error"

            graph = torch.load(os.path.join(self.processed_dir, graph_filepath))
            y_list.append(graph.y.squeeze()[0].item())
            seq_list.append(graph)

        torch_seq = torch_geometric.data.Batch.from_data_list(seq_list)
        torch_seq.seq = torch_seq.batch
        torch_seq.batch = None
        torch_seq.y = torch.tensor(y_list)
        return torch_seq
