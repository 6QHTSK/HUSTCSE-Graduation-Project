# 这是一个示例 Python 脚本。
import random
import time

# 按 Shift+F10 执行或将其替换为您的代码。
# 按 双击 Shift 在所有地方搜索类、文件、工具窗口、操作和设置。

from torch_geometric.loader import DataLoader
from torch.utils.data import random_split, ConcatDataset, Subset
from torch import nn
from pygod.metrics import eval_roc_auc, eval_average_precision
import torch
import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm
from sklearn import metrics

import data.streamspot_RGAT as streamspot_dataset
from model.model_RGAT import DetectModel

from data.darpa_cadets_RGAT import DarpaCadetsDataset, DarpaNormalDataset


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
            output = classifier(graph)
            target = graph.y.squeeze()[0:1].float()
            loss = criterion(output, target)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            if i % 10 == 0:
                t.set_postfix(loss=total_loss / i)
    scheduler.step(total_loss)
    return total_loss / i, classifier


def find_best_threshold(precision, recall, thresholds):
    f1_scores = [2 * p * r / (p + r) for p, r in zip(precision, recall)]
    best_index = np.argmax(f1_scores)
    best_threshold = thresholds[best_index]
    best_f1 = f1_scores[best_index]
    return best_threshold, precision[best_index], recall[best_index], best_f1


def test_model(test_loader, normal_loader, device, epoch, test_total_cnt, normal_total_cnt):
    y_score_list = []
    y_true_list = []
    with torch.no_grad():
        with tqdm(test_loader, desc="Test", leave=True, total=test_total_cnt) as t:
            for i, graph in enumerate(t, 1):
                graph = graph.to(device)
                y_score = classifier(graph).cpu().item()
                y_true = graph.y.squeeze()[0:1].item()
                y_score_list.append(y_score)
                y_true_list.append(y_true)

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

    fpr = test_fp_rate(normal_loader, best_threshold, device, normal_total_cnt)

    print("Test set: AUC: {:.4f} AP: {:.4f} FPR:{:.4f}".format(auc_score, average_precision,fpr))
    return auc_score, average_precision


def test_fp_rate(normal_loader, threshold, device, total_cnt):
    y_false_positive = 0
    j = 1
    y_item_false_positive = 0
    with torch.no_grad():
        with tqdm(normal_loader, desc="Test", leave=True, total=total_cnt) as t:
            for i, graph in enumerate(t, 1):
                graph = graph.to(device)
                y_score = classifier(graph).cpu().item()
                if y_score >= threshold:
                    y_false_positive += 1
                    y_item_false_positive += 1
                # if j % 100 == 0:
                #     print(f"Section {j // 100}: fp_cnt:{y_item_false_positive}")
                #     y_item_false_positive = 0
                # j = i + 1
    return y_false_positive / total_cnt


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
    only_train_generated_mul = True
    dataset = "darpa"
    # dataset = "streamspot"
    # Datasets
    if dataset == "streamspot":
        streamspot_dataset_dir = r"E:\AnAPTDetector\data\streamspot"
        # total_available 1600 train_set 1400 test_set 200
        if only_train_generated_mul:
            # train_set normal 400 generated 1000
            # test_set  100 malicious 100 normal
            train_cnt = 1400
            test_cnt = 200
            normal_cnt = 500
            normal_dataset = streamspot_dataset.NormalStreamSpotDataset(streamspot_dataset_dir)  # 500
            malicious_dataset = streamspot_dataset.MaliciousStreamSpotDataset(streamspot_dataset_dir)  # 100
            generated_dataset = streamspot_dataset.GeneratedStreamSpotDataset(streamspot_dataset_dir)  # 1000
            train_set_normal, test_set_normal = random_split(normal_dataset, [400, 100])
            train_set = ConcatDataset([train_set_normal, generated_dataset])
            test_set = ConcatDataset([test_set_normal, malicious_dataset])

        else:
            # train_set:test_set 1400 200
            train_cnt = 1400
            test_cnt = 200
            original_dataset = streamspot_dataset.OriginalStreamSpotDataset(r"E:\AnAPTDetector\data\streamspot")  # 600
            generated_dataset = streamspot_dataset.GeneratedStreamSpotDataset(streamspot_dataset_dir)  # 1000
            dataset = ConcatDataset([original_dataset, generated_dataset])
            train_set, test_set = random_split(dataset, [1400, 200])
        classifier = DetectModel(num_relations=29, num_node_attr=5).to(device)
    elif dataset == "darpa":
        dataset = DarpaCadetsDataset(r"E:\AnAPTDetector\data\darpa-tc-cadets")
        normal_dataset = DarpaNormalDataset(r"E:\AnAPTDetector\data\darpa-tc-cadets")
        train_cnt = int(len(dataset) * 0.7)
        test_cnt = len(dataset) - int(len(dataset) * 0.7)
        normal_cnt = len(normal_dataset)
        train_set, test_set = random_split(dataset, [train_cnt, test_cnt])
        classifier = DetectModel(num_relations=114, num_node_attr=10).to(device)
    else:
        raise "Wrong Dataset"

    train_loader = DataLoader(train_set, batch_size=1, shuffle=True)
    test_loader = DataLoader(dataset=test_set, batch_size=1)
    normal_loader = DataLoader(dataset=normal_dataset, batch_size=1)

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
    for epoch in range(1, 20):
        print(f"Epoch {epoch}")
        time.sleep(1)
        loss, model = train_model(train_loader, scheduler, device, total_cnt=train_cnt)
        auc, ap = test_model(test_loader, normal_loader, device, epoch, test_total_cnt=test_cnt, normal_total_cnt=normal_cnt)
        loss_list.append(loss)
        auc_list.append(auc)
        ap_list.append(ap)

    draw_plt(loss_list, "Loss")
    draw_plt(auc_list, "AUC")
    draw_plt(ap_list, "Average Precision")

# 访问 https://www.jetbrains.com/help/pycharm/ 获取 PyCharm 帮助
