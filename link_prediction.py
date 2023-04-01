# -*- coding: utf-8 -*-
"""Link_Prediction.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1-DxbYUU-igmGT2G78Tk8jZXfWvUUFTuc
"""

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import networkx as nx
from tqdm import tqdm

dataset = pd.read_csv('data_train_edge.csv')
test_set = pd.read_csv('predict.csv')
x = dataset.iloc[:, 0].values
y = dataset.iloc[:, 1].values
ans500 = pd.read_csv('ans500_ground_truth.csv')
y_test = ans500.iloc[:,1]

independent_nodes = []
for i in range(1005):
  if i not in x and i not in y:
    independent_nodes.append(i)

matrix = np.zeros((1005,1005))

for i in range(len(x)):
  row = x[i]
  col = y[i]
  matrix[row][col] = 1

# create graph
G = nx.from_pandas_edgelist(dataset, "node1", "node2", create_using=nx.DiGraph())
independent_nodes_counts = len(independent_nodes)
for i in range(independent_nodes_counts):
  G.add_node(independent_nodes[i])
# plot graph
"""
plt.figure(figsize=(10,10))
pos = nx.random_layout(G, seed=23)
nx.draw(G, with_labels=True,  pos = pos, node_size = 40, alpha = 0.6, width = 0.7)
plt.show()
"""

# get unconnected node-pairs
all_unconnected_pairs = []

# traverse adjacency matrix
for i in range(matrix.shape[0]):
  for j in range(matrix.shape[1]):
    if matrix[i,j] == 0:
      all_unconnected_pairs.append([i,j])

print(len(all_unconnected_pairs))

node_1_unlinked = [i[0] for i in all_unconnected_pairs]
node_2_unlinked = [i[1] for i in all_unconnected_pairs]

data = pd.DataFrame({'node1':node_1_unlinked, 
                     'node2':node_2_unlinked})

# add target variable 'link'
data['link'] = 0

initial_node_count = len(G.nodes)
initial_number_connected_components = nx.number_weakly_connected_components(G)
dataset_temp = dataset.copy()

# empty list to store removable links
omissible_links_index = []
# print(dataset_temp)

for i in tqdm(dataset.index.values):
  # remove a node pair and build a new graph
  test = dataset_temp.drop(index = i)
  G_temp = nx.from_pandas_edgelist(test, "node1", "node2", create_using=nx.DiGraph())
  for n in range(independent_nodes_counts):
    G_temp.add_node(independent_nodes[n])
  # check there is no spliting of graph and number of nodes is same
  if (nx.number_weakly_connected_components(G_temp) == initial_number_connected_components) and (len(G_temp.nodes) == initial_node_count):
    omissible_links_index.append(i)
    dataset_temp = dataset_temp.drop(index = i)

len(omissible_links_index)

# create dataframe of removable edges
dataset_removable = dataset.loc[omissible_links_index]

# add the target variable 'link'
dataset_removable['link'] = 1

data = data.append(dataset_removable[['node1', 'node2', 'link']], ignore_index=True)

print(data['link'].value_counts())

# drop removable edges
dataset_partial = dataset.drop(index=dataset_removable.index.values)

# build graph
G_data = nx.from_pandas_edgelist(dataset_partial, "node1", "node2", create_using=nx.Graph())
for n in range(independent_nodes_counts):
    G_data.add_node(independent_nodes[n])

print(dataset_partial['node1'].shape)

# Commented out IPython magic to ensure Python compatibility.
# %pip install node2vec

from node2vec import Node2Vec

# Generate walks
node2vec = Node2Vec(G_data, dimensions=128, walk_length=200, num_walks=100)

# train node2vec model
n2w_model = node2vec.fit(window=7, min_count=1)

X_train = [(n2w_model[str(i)]+n2w_model[str(j)]) for i,j in zip(data['node1'], data['node2'])]
y_train = data['link']

X_test = [(n2w_model[str(i)]+n2w_model[str(j)]) for i,j in zip(test_set['node1'], test_set['node2'])]

# Feature Scaling
from sklearn.preprocessing import StandardScaler
sc = StandardScaler()
X_train = sc.fit_transform(X_train)
X_test = sc.transform(X_test)

# light gbm
import lightgbm as lgb
from sklearn.metrics import accuracy_score
lgbclf = lgb.LGBMClassifier(max_depth=9, num_leaves=511, learning_rate=0.04, n_estimators=1000, early_stop_round=50, min_child_sample=2500, objective='binary', feature_fraction=0.5, bagging_fraction = 0.5, bagging_freq = 20, num_threads = 2, seed=76, is_unbalance=True)
lgbclf.fit(X_train,y_train)
lgb_predictions = lgbclf.predict(X_test)
print(len(lgb_predictions))
print("Accuracy:", accuracy_score(y_test, lgb_predictions[0:500]))

from sklearn.metrics import confusion_matrix
cm = confusion_matrix(y_test, lgb_predictions[0:500])
print('Confusion matrix\n\n', cm)
print('\nTrue Positives(TP) = ', cm[0,0])
print('\nTrue Negatives(TN) = ', cm[1,1])
print('\nFalse Positives(FP) = ', cm[0,1])
print('\nFalse Negatives(FN) = ', cm[1,0])

import csv
with open('lgb_predict_result15_0.934.csv', 'w', newline='') as csvfile:
  # 建立 CSV 檔寫入器
  writer = csv.writer(csvfile)

  # 寫入一列資料
  writer.writerow(['predict_nodepair_id', 'ans'])
  for i in range(len(lgb_predictions)):
    writer.writerow([i, lgb_predictions[i]])

