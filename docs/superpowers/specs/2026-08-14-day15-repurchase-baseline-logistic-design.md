# Day 15 复购基线与 Logistic Regression 设计

## 目标

在时间安全的 90 天复购训练集上，将简单业务排序与 Logistic Regression 比较，评估有限营销触达名额下的客户排序质量。

## 候选方法

业务基线按首单商品金额由高到低排序，作为可解释的“优先触达高首单价值客户”规则。Logistic Regression 仅使用 Day 14 的首单可知特征，通过同一 Pipeline 完成缺失值填补、标准化和类别不平衡处理；不加入任何预测时点之后的信息。

## 评估

模型与基线共享同一按时间划分的训练、验证、测试数据。输出 PR-AUC、ROC-AUC、Brier score、Precision@K、Recall@K、Lift@K 与全体阳性率；Top-K 至少包含一位客户。Accuracy 仅可辅助查看，不作为选择依据。

## 训练与产物

训练使用 `class_weight="balanced"`。脚本读取 `marts.ml_customer_features` 的完整观察期客户，生成时间范围、样本量、阳性率和候选指标的 JSON 比较表。模型选择只使用验证集，最终测试集在 Day 16 的模型选择后只评估一次。

## 验收

- 完美排序的 Lift@20% 为 5，随机/常数排序没有虚假的提升。
- 空数组与单类别标签产生明确错误。
- Logistic Regression 的特征转换全部位于 Pipeline 内。
- 结果文件可追溯数据时间、样本量、阳性率和指标。
