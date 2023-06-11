# 这是一个示例 Python 脚本。
import math
import random
import time

from sklearn import metrics
# 按 Shift+F10 执行或将其替换为您的代码。
# 按 双击 Shift 在所有地方搜索类、文件、工具窗口、操作和设置。

from torch_geometric.loader import DataLoader
from torch.utils.data import random_split
from torch import nn
from pygod.metrics import eval_roc_auc, eval_average_precision
import torch
import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm
from sklearn.metrics import RocCurveDisplay

import main
from data.darpa_cadets_RGAT_GRU import DarpaCadetsSeqDataset
from model.model_RGAT_GRU import DetectModel
from model.model_RGAT import DetectModelGRUAdapt


def seed_everything(seed):
    if seed >= 10000:
        raise ValueError("seed number should be less than 10000")
    if torch.distributed.is_initialized():
        rank = torch.distributed.get_rank()
    else:
        rank = 0
    seed = (rank * 100000) + seed

    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)


def train_model(train_loader, scheduler, device, total_cnt):
    total_loss = 0
    with tqdm(train_loader, desc="Train", leave=True, total=total_cnt) as t:
        for i, graph in enumerate(t, 1):
            graph = graph.to(device)
            output = classifier(graph, device=device).squeeze()
            target = graph.y
            loss = criterion(output, target)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            t.set_postfix(loss=total_loss / i)
    scheduler.step(total_loss)
    return total_loss / i, classifier


def find_best_threshold(precision, recall, thresholds):
    f1_scores = []
    for p, r in zip(precision, recall):
        if p + r == 0:
            f1_scores.append(0)
        else:
            f1_scores.append(2 * p * r / (p + r))
    best_index = np.argmax(f1_scores)
    best_threshold = thresholds[best_index]
    best_f1 = f1_scores[best_index]
    return best_threshold, precision[best_index], recall[best_index], best_f1


def test_model(test_loader, device, epoch, total_cnt):
    y_score_list = []
    y_true_list = []
    with torch.no_grad():
        with tqdm(test_loader, desc="Test", leave=True, total=total_cnt) as t:
            for i, graph in enumerate(t, 1):
                graph = graph.to(device)
                y_score = classifier(graph, device=device).squeeze().cpu()
                y_score = y_score.tolist()
                y_true = graph.y.tolist()
                y_score_list.extend(y_score)
                y_true_list.extend(y_true)

    y_true_list = np.array(y_true_list)
    y_score_list = np.array(y_score_list)
    fpr_list, tpr_list, threshold_roc = metrics.roc_curve(y_true_list, y_score_list)
    precision_list, recall_list, threshold_prc = metrics.precision_recall_curve(y_true_list, y_score_list)
    best_threshold, best_precision, best_recall, best_f1 = find_best_threshold(precision_list, recall_list,
                                                                               threshold_prc)

    average_precision = metrics.average_precision_score(y_true_list, y_score_list)
    metrics.PrecisionRecallDisplay(precision=precision_list, recall=recall_list,
                                   average_precision=average_precision).plot()
    plt.scatter(best_recall, best_precision)
    plt.annotate(f"Best Threshold:{best_threshold:.4f}\n ({best_recall:.3f},{best_precision:.3f})\n F1:{best_f1:.3f}",
                 xy=(best_recall, best_precision),
                 xytext=(0.5, 0.5))
    plt.show()

    auc_score = metrics.roc_auc_score(y_true_list, y_score_list)
    metrics.RocCurveDisplay(fpr=fpr_list, tpr=tpr_list, roc_auc=auc_score).plot()
    roc_index = np.argmin(np.abs(threshold_roc - best_threshold))
    best_fpr, best_tpr = fpr_list[roc_index], tpr_list[roc_index]
    plt.scatter(best_fpr, best_tpr)
    plt.annotate(f"Best Threshold:{best_threshold:.4f}\n ({best_fpr:.3f},{best_tpr:.3f})",
                 xy=(best_fpr, best_tpr),
                 xytext=(0.5, 0.5))
    plt.show()

    print("Test set: AUC: {:.4f} AP: {:.4f}".format(auc_score, average_precision))
    return auc_score, average_precision


def draw_plt(list, ylabel):
    epoch = np.arange(1, len(list) + 1, 1)
    list = np.array(list)
    plt.plot(epoch, list)
    plt.xlabel('Epoch')
    plt.ylabel(ylabel)
    plt.grid()
    plt.show()


# 按间距中的绿色按钮以运行脚本。
if __name__ == '__main__':
    seed_everything(2023)
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    # device = "cpu"
    train_cnt = 70
    test_cnt = 30
    dataset = DarpaCadetsSeqDataset(r"E:\AnAPTDetector\data\darpa-tc-cadets")
    train_set, test_set = random_split(dataset, [train_cnt, test_cnt])
    use_GRU = False
    if use_GRU:
        classifier = DetectModel(num_relations=114, num_node_attr=10).to(device)
    else:
        classifier = DetectModelGRUAdapt(num_relations=114, num_node_attr=10).to(device)

    train_loader = DataLoader(train_set, batch_size=1, shuffle=True)
    test_loader = DataLoader(dataset=test_set, batch_size=1)

    criterion = nn.BCELoss().to(device)
    optimizer = torch.optim.Adam(classifier.parameters(), lr=0.0001)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.1,
                                                           patience=10, verbose=False, threshold=1e-6,
                                                           threshold_mode='rel',
                                                           cooldown=0,
                                                           min_lr=0, eps=1e-08)

    auc_list = []
    ap_list = []
    loss_list = []
    for epoch in range(1, 50):
        print(f"Epoch {epoch}")
        time.sleep(1)
        loss, model = train_model(train_loader, scheduler, device, total_cnt=train_cnt)
        auc, ap = test_model(test_loader, device, epoch, total_cnt=test_cnt)
        loss_list.append(loss)
        auc_list.append(auc)
        ap_list.append(ap)

    draw_plt(loss_list, "Loss")
    draw_plt(auc_list, "AUC")
    draw_plt(ap_list, "Average Precision")

# 访问 https://www.jetbrains.com/help/pycharm/ 获取 PyCharm 帮助
