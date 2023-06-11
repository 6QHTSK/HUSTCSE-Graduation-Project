import gc

import torch
import torch_geometric


# SAGEConv GatedGraphConv ResGatedGraphConv FusedGATConv AGNNConv GINConv MFConv EdgeConv FeaStConv ClusterGCNConv PANConv WLConv EGConv GPSConv: x, edge_index
# GCNConv ChebConv GraphConv TAGConv ARMAConv SGConv SSGConv APPNP LEConv GCN2Conv WLConvContinuous FAConv LGConv AntiSymmetricConv: x,edge_index, 1D - edge_weights
# GATConv GATv2Conv TransformerConv GINEConv GMMConv SplineConv NNConv CGCConv PNAConv GENConv PDNConv GeneralConv: x, edge_index, nD - edge_attr
# RGCNConv FastRGCNConv RGATConv FiLMConv HEATConv: Special need new input include edge_type & node_type

class DetectModel(torch.nn.Module):
    def __init__(self, embedding_dim=16, gnn_layers_cnt=3, num_relations=114, num_node_attr=10):
        self.gnn_layers_cnt = gnn_layers_cnt
        super(DetectModel, self).__init__()
        self.node_embedding = torch.nn.Embedding(num_node_attr, embedding_dim)
        self.gnn_layers = torch.nn.ModuleList(torch_geometric.nn.RGATConv(in_channels=embedding_dim,
                                                                          out_channels=embedding_dim,
                                                                          num_relations=num_relations) for _ in
                                              range(gnn_layers_cnt))
        self.pooling = torch.nn.ModuleList(
            torch_geometric.nn.TopKPooling(in_channels=embedding_dim, ratio=0.8) for _ in range(gnn_layers_cnt - 1))
        input_size = embedding_dim * gnn_layers_cnt * 2
        self.rnn = torch.nn.GRU(input_size=input_size, hidden_size=16)
        self.liner_1 = torch.nn.Linear(16, 4)
        self.liner_2 = torch.nn.Linear(4, 1)
        self.activate = torch.nn.ReLU()
        self.sigmoid = torch.nn.Sigmoid()

    def forward(self, input_graph, device):
        # input_graph: x=[m个图所含的所有N个0-4] edge_index=[2,m个图所含的所有的E] edge_type=[m个图所含的所有的E个0-28,1] y=[m,1] batch=[0,
        # B-1]^(m个图的N) 注意：此处的input_graph 传入的是拼接起来的图，假设拼起来的图个数为m
        # 1. X和edge_attr过Embedding
        gc.collect()
        if device != "cpu":
            torch.cuda.empty_cache()

        input_graph.x = self.node_embedding(input_graph.x.squeeze())
        input_graph.edge_type = input_graph.edge_attr.squeeze()
        input_graph.batch = input_graph.seq

        # 2. RGAT Convolution
        graph_attr = torch.tensor([]).to(device)
        for index in range(self.gnn_layers_cnt):
            input_graph.x = self.gnn_layers[index](x=input_graph.x,
                                                   edge_index=input_graph.edge_index,
                                                   edge_type=input_graph.edge_type).relu()

            mean_node_attr = torch.squeeze(torch_geometric.nn.global_mean_pool(input_graph.x,
                                                                               batch=input_graph.batch))
            max_node_attr = torch.squeeze(torch_geometric.nn.global_max_pool(input_graph.x,
                                                                             batch=input_graph.batch))
            graph_attr = torch.cat([graph_attr, mean_node_attr, max_node_attr], dim=1)  # m行
            del mean_node_attr
            del max_node_attr
            if index < len(self.pooling):
                input_graph.x, input_graph.edge_index, input_graph.edge_type, input_graph.batch, _, _ = \
                    self.pooling[index](x=input_graph.x,
                                        edge_index=input_graph.edge_index,
                                        edge_attr=input_graph.edge_type,
                                        batch=input_graph.batch)

        # graph_attr (seq_len*input_size)
        # 3. RNN 循环神经网络 由于目前暂时1batch就一个向量
        # 传入格式：(seq_len,batch_size=1,input_size)

        graph_attr = graph_attr.unsqueeze(1)
        graph_attr, _ = self.rnn(graph_attr)

        # 4. 线性层
        graph_attr = graph_attr.squeeze()
        graph_attr = self.liner_1(graph_attr)
        graph_attr = self.activate(graph_attr)
        graph_attr = self.liner_2(graph_attr)
        graph_attr = self.activate(graph_attr)

        # 输出为 malicious_possibility（seq_len,1)
        return graph_attr
