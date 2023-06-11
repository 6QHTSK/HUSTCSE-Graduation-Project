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
        self.liner_1 = torch.nn.Linear(embedding_dim * gnn_layers_cnt * 2, 16)
        self.liner_2 = torch.nn.Linear(16, 4)
        self.liner_3 = torch.nn.Linear(4, 1)
        self.activate = torch.nn.ReLU()
        self.sigmoid = torch.nn.Sigmoid()

    def forward(self, input_graph):
        # input_graph: x=[N个0-4] edge_index=[2,E] edge_type=[E个0-28] y=[1,1]
        # 1. X和edge_attr过Embedding
        x = self.node_embedding(input_graph.x.squeeze())
        edge_type = input_graph.edge_attr.squeeze()
        edge_index = input_graph.edge_index

        # 2. RGAT Convolution
        graph_attr = torch.tensor([]).to(x.device)
        for index in range(self.gnn_layers_cnt):
            node_attr = self.gnn_layers[index](x=x, edge_index=edge_index, edge_type=edge_type).relu()
            mean_node_attr = torch.squeeze(torch_geometric.nn.global_mean_pool(node_attr, batch=None))
            max_node_attr = torch.squeeze(torch_geometric.nn.global_max_pool(node_attr, batch=None))
            graph_attr = torch.cat([graph_attr, mean_node_attr, max_node_attr], dim=0)
            if index < len(self.pooling):
                x, edge_index, edge_type, _, _, _ = self.pooling[index](x, edge_index, edge_type)

        # 3. 线性二分类层
        graph_attr = self.liner_1(graph_attr)
        graph_attr = self.activate(graph_attr)
        graph_attr = self.liner_2(graph_attr)
        graph_attr = self.activate(graph_attr)
        graph_attr = self.liner_3(graph_attr)
        graph_attr = self.sigmoid(graph_attr)

        return graph_attr


class DetectModelGRUAdapt(torch.nn.Module):
    def __init__(self, embedding_dim=16, gnn_layers_cnt=3, num_relations=114, num_node_attr=10):
        self.gnn_layers_cnt = gnn_layers_cnt
        super(DetectModelGRUAdapt, self).__init__()
        self.node_embedding = torch.nn.Embedding(num_node_attr, embedding_dim)
        self.gnn_layers = torch.nn.ModuleList(torch_geometric.nn.RGATConv(in_channels=embedding_dim,
                                                                          out_channels=embedding_dim,
                                                                          num_relations=num_relations) for _ in
                                              range(gnn_layers_cnt))
        self.pooling = torch.nn.ModuleList(
            torch_geometric.nn.TopKPooling(in_channels=embedding_dim, ratio=0.8) for _ in range(gnn_layers_cnt - 1))
        self.liner_1 = torch.nn.Linear(embedding_dim * gnn_layers_cnt * 2, 16)
        self.liner_2 = torch.nn.Linear(16, 4)
        self.liner_3 = torch.nn.Linear(4, 1)
        self.activate = torch.nn.ReLU()
        self.sigmoid = torch.nn.Sigmoid()

    def forward(self, input_graph, device):
        # input_graph: x=[N个0-4] edge_index=[2,E] edge_type=[E个0-28] y=[1,1] 注意 Batch信息放在了seq里面
        # 1. X和edge_attr过Embedding
        input_graph.x = self.node_embedding(input_graph.x.squeeze())
        input_graph.edge_attr = input_graph.edge_attr.squeeze()
        input_graph.batch = input_graph.seq

        # 2. RGAT Convolution
        graph_attr = torch.tensor([]).to(device)
        for index in range(self.gnn_layers_cnt):
            input_graph.x = self.gnn_layers[index](x=input_graph.x,
                                                   edge_index=input_graph.edge_index,
                                                   edge_type=input_graph.edge_attr).relu()
            mean_node_attr = torch.squeeze(torch_geometric.nn.global_mean_pool(input_graph.x,
                                                                               batch=input_graph.batch))
            max_node_attr = torch.squeeze(torch_geometric.nn.global_max_pool(input_graph.x,
                                                                             batch=input_graph.batch))
            graph_attr = torch.cat([graph_attr, mean_node_attr, max_node_attr], dim=1)
            del mean_node_attr
            del max_node_attr
            if index < len(self.pooling):
                input_graph.x, input_graph.edge_index, input_graph.edge_attr, input_graph.batch, _, _ = \
                    self.pooling[index](x=input_graph.x,
                                        edge_index=input_graph.edge_index,
                                        edge_attr=input_graph.edge_attr,
                                        batch=input_graph.batch)

        # 3. 线性二分类层
        graph_attr = self.liner_1(graph_attr)
        graph_attr = self.activate(graph_attr)
        graph_attr = self.liner_2(graph_attr)
        graph_attr = self.activate(graph_attr)
        graph_attr = self.liner_3(graph_attr)
        graph_attr = self.sigmoid(graph_attr)

        return graph_attr
