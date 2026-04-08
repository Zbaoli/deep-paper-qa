# Content 低分题详细对比：工具输出 vs Agent 回答

共 17 道题，按质量分升序排列。

---

## Q24 [mixed] — overall=1.75

| accuracy | completeness | citation | clarity |
|----------|--------------|----------|---------|
| 1 | 1 | 1 | 4 |

**问题**: NeurIPS 2025 的多模态论文都用了哪些数据集？

**工具调用**: ['search_abstracts', 'search_abstracts', 'vector_search', 'search_abstracts']

**Judge 评语**: 回答结构清晰但内容完全虚构，所有具体信息均无法在提供的工具数据中找到依据。

### 工具输出

**调用 1: search_abstracts**

输入:
```
{'query': 'multimodal OR vision-language OR visual-language OR image-text OR video-text', 'where': "year=2025 AND conference='NeurIPS'", 'limit': 15}
```

输出:
```
[1] The Narrow Gate: Localized Image-Text Communication in Native Multimodal Models
    ID: neurips-2025-n0I0IvdfB3 | NeurIPS 2025 | 引用: 0 | 相关度: 0.0563
    摘要片段: 【vision】-【language】 models (VLMs) handle 【image】-understanding tasks, focusing on how 【visual】 information is processed and transferred to the textual

[2] Hallucination at a Glance: Controlled Visual Edits and Fine-Grained Multimodal Learning
    ID: neurips-2025-uS4Wmg7PmE | NeurIPS 2025 | 引用: 0 | 相关度: 0.0551
    摘要片段: 【Multimodal】 l
```

**调用 2: search_abstracts**

输入:
```
{'query': 'dataset OR datasets OR "COCO" OR "ImageNet" OR "LAION" OR "MS-COCO" OR "Flickr30k" OR "VQA" OR "Visual Genome" OR "Conceptual Captions"', 'where': "year=2025 AND conference='NeurIPS'", 'limit': 15}
```

输出:
```
[1] Rectified CFG++ for Flow Based Models
    ID: neurips-2025-NosdT1FHPv | NeurIPS 2025 | 引用: 0 | 相关度: 0.0253
    摘要片段: standard CFG on benchmark 【datasets】 such as 【MS】‑【COCO】, 【LAION】‑Aesthetic, and T2I‑CompBench. Project page: https://rectified-cfgpp.github.io/.

[2] DiCo: Revitalizing ConvNets for Scalable and Efficient Diffusion Modeling
    ID: neurips-2025-UnslcaZSnb | NeurIPS 2025 | 引用: 0 | 相关度: 0.0253
    摘要片段: experimental results on 【MS】-【COCO】 demonstrate that the purely convolution
```

**调用 3: vector_search**

输入:
```
{'query': 'What datasets are used in NeurIPS 2025 multimodal papers? List specific dataset names mentioned in the papers', 'where': "year=2025 AND conference='NeurIPS'", 'top_k': 10}
```

输出:
```
未找到相关论文。可以尝试使用 search_abstracts 进行关键词搜索。
```

**调用 4: search_abstracts**

输入:
```
{'query': '"benchmark dataset" OR "evaluation dataset" OR "training data" OR "test set"', 'where': "year=2025 AND conference='NeurIPS'", 'limit': 10}
```

输出:
```
[1] DreamPRM: Domain-reweighted Process Reward Model for Multimodal Reasoning
    ID: neurips-2025-ZyiBk1ZinG | NeurIPS 2025 | 引用: 0 | 相关度: 0.0760
    摘要片段: 【testing】 【sets】 is more severe, leading to greater generalization difficulty. 【Training】 a reliable multimodal PRM, therefore, demands large and diverse

[2] Dual Data Alignment Makes AI-Generated Image Detector Easier Generalizable
    ID: neurips-2025-C39ShJwtD5 | NeurIPS 2025 | 引用: 0 | 相关度: 0.0720
    摘要片段: 【training】 【data】, they result
```

### Agent 回答（前 200 字）

```
基于我的搜索结果，我现在可以为您总结 NeurIPS 2025 年多模态论文中使用的数据集。让我整理一下找到的信息：

## NeurIPS 2025 多模态论文使用的数据集

根据对 NeurIPS 2025 年多模态论文的搜索分析，以下是一些常见的数据集：

### 1. **图像-文本多模态数据集**
- **MS-COCO**：这是最常被提及的数据集，在多篇论文中用于评估和训练
  - 在
```

---

## Q55 [mixed] — overall=1.75

| accuracy | completeness | citation | clarity |
|----------|--------------|----------|---------|
| 1 | 1 | 1 | 4 |

**问题**: WWW 会议中引用最高的 3 篇推荐系统论文的方法有什么区别？

**工具调用**: ['execute_sql', 'search_abstracts', 'vector_search']

**Judge 评语**: 回答结构清晰但内容完全错误，基于编造的数据和论文进行回答，未能满足问题的任何要求。

### 工具输出

**调用 1: execute_sql**

输入:
```
{'sql': "SELECT title, year, citations, conference \nFROM papers \nWHERE conference = 'WWW' \n  AND to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,'')) \n      @@ to_tsquery('english', 'recommend:* | recommender')\nORDER BY citations DESC \nLIMIT 10"}
```

输出:
```
title | year | citations | conference
-------------------------------------
MetaSelector: Meta-Learning for Recommendation with User-Level Adaptive Model Selection | 2020 | 0 | WWW
Hierarchical Visual-aware Minimax Ranking Based on Co-purchase Data for Personalized Recommendation | 2020 | 0 | WWW
The Structure of Social Influence in Recommender Networks | 2020 | 0 | WWW
Evolution of a Web-Scale Near Duplicate Image Detection System | 2020 | 0 | WWW
Deep Rating Elicitation for New Users in Collab
```

**调用 2: search_abstracts**

输入:
```
{'query': 'recommendation system OR recommender system', 'where': "conference='WWW'", 'limit': 15}
```

输出:
```
[1] Practical Data Poisoning Attack against Next-Item Recommendation
    ID: www-2020-3366423.3379992 | WWW 2020 | 引用: 0 | 相关度: 0.0942
    摘要片段: 【recommendation】 【systems】, the cost of retraining 【recommendation】 models is high, and the interaction frequency between users and a 【recommendation】

[2] Linear-Time Graph Neural Networks for Scalable Recommendations
    ID: www-2024-3589334.3645486 | WWW 2024 | 引用: 0 | 相关度: 0.0918
    摘要片段: 【recommender】 【systems】 are vital tools to deliver personali
```

**调用 3: vector_search**

输入:
```
{'query': 'recommender system methods comparison graph neural networks fairness federated learning', 'where': "conference='WWW'", 'top_k': 8}
```

输出:
```
[1] Learning Fair Representations for Recommendation: A Graph-based Perspective
    ID: www-2021-3442381.3450015 | WWW 2021 | 引用: 0 | 相似度: 0.7096
    摘要: As a key application of artificial intelligence, recommender systems are among the most pervasive computer aided systems to help users find potential items of interests. Recently, researchers paid considerable attention to fairness issues for artificial intelligence applications. Most of these approaches assumed independence of instances, and d
```

### Agent 回答（前 200 字）

```
基于搜索结果，我选择3篇具有代表性方法差异的WWW推荐系统论文进行分析。虽然引用数据不完整，但我可以根据论文内容分析它们的方法区别：

## WWW会议中3篇代表性推荐系统论文的方法对比

### 1. **Learning Fair Representations for Recommendation: A Graph-based Perspective (WWW 2021)**
**核心方法*
```

---

## Q60 [content] — overall=1.75

| accuracy | completeness | citation | clarity |
|----------|--------------|----------|---------|
| 1 | 1 | 1 | 4 |

**问题**: Yann LeCun 关于 self-supervised learning 的论文有哪些？

**工具调用**: ['search_abstracts', 'execute_sql', 'vector_search']

**Judge 评语**: 回答结构清晰但内容完全虚构，未能基于提供的工具数据给出任何准确信息。

### 工具输出

**调用 1: search_abstracts**

输入:
```
{'query': 'self-supervised learning OR self supervised learning OR unsupervised representation learning', 'limit': 20}
```

输出:
```
[1] Self-Supervised Set Representation Learning for Unsupervised Meta-Learning
    ID: iclr-2023-kIAx30hYi_p | ICLR 2023 | 引用: 0 | 相关度: 0.0886
    摘要片段: 【self】-【supervised】 set 【representation】 【learning】 framework for targeting UML problem. Specifically, our Set-SimCLR 【learns】

[2] Self-supervised Learning from a Multi-view Perspective
    ID: iclr-2021--bdp_8Itjwp | ICLR 2021 | 引用: 12 | 相关度: 0.0864
    摘要片段: 【unsupervised】 【representation】 【learning】, 【self】-【supervised】 【representation】 【lea
```

**调用 2: execute_sql**

输入:
```
{'sql': "SELECT title, year, conference, citations, authors\nFROM papers \nWHERE ('Yann LeCun' = ANY(authors) OR 'Yann L. LeCun' = ANY(authors) OR 'Yann' = ANY(authors))\nAND to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,''))\n@@ to_tsquery('english', 'self <-> supervised | self-supervised | unsupervised <-> representation')\nORDER BY year DESC, citations DESC\nLIMIT 20"}
```

输出:
```
title | year | conference | citations | authors
-----------------------------------------------
$\mathbb{X}$-Sample Contrastive Loss: Improving Contrastive Learning with Sample Similarity Graphs | 2025 | ICLR | 0 | ['Vlad Sobal', 'Mark Ibrahim', 'Randall Balestriero', 'Vivien Cabannes', 'Diane Bouchacourt', 'Pietro Astolfi', 'Kyunghyun Cho', 'Yann LeCun']
URLOST: Unsupervised Representation Learning without Stationarity or Topology | 2025 | ICLR | 0 | ['Zeyu Yun', 'Juexiao Zhang', 'Yann LeCun', 
```

**调用 3: vector_search**

输入:
```
{'query': 'Yann LeCun self-supervised learning representation learning contrastive learning', 'top_k': 10}
```

输出:
```
[1] Text Transformations in Contrastive Self-Supervised Learning: A Review
    ID: ijcai-2022-0757 | IJCAI 2022 | 引用: 16 | 相似度: 0.6940
    摘要: Contrastive self-supervised learning has become a prominent technique in representation learning. The main step in these methods is to contrast semantically similar and dissimilar pairs of samples. However, in the domain of Natural Language Processing (NLP), the augmentation methods used in creating similar pairs with regard to contrastive learning (CL) a
```

### Agent 回答（前 200 字）

```
基于我的搜索结果，我找到了 Yann LeCun 参与的多篇关于自监督学习的重要论文。以下是主要发现：

## Yann LeCun 关于自监督学习的主要论文

### 高影响力论文
1. **VICReg: Variance-Invariance-Covariance Regularization for Self-Supervised Learning** (ICLR 2022) - **28
```

---

## Q11 [content] — overall=2.0

| accuracy | completeness | citation | clarity |
|----------|--------------|----------|---------|
| 1 | 2 | 1 | 4 |

**问题**: RAG 的 chunking 策略有哪些改进方法？

**工具调用**: ['search_abstracts', 'search_abstracts', 'vector_search', 'search_abstracts']

**Judge 评语**: 回答结构清晰但内容完全失实，引用的论文均为虚构，未能基于工具数据提供有效信息。

### 工具输出

**调用 1: search_abstracts**

输入:
```
{'query': 'chunking OR chunk OR segmentation RAG OR retrieval-augmented OR retrieval augmented generation', 'limit': 15}
```

输出:
```
[1] HyperGraphRAG: Retrieval-Augmented Generation via Hypergraph-Structured Knowledge Representation
    ID: neurips-2025-ravS5h8MNg | NeurIPS 2025 | 引用: 0 | 相关度: 0.0682
    摘要片段: 【Retrieval】-【Augmented】 【Generation】 (【RAG】) relies on 【chunk】-based 【retrieval】, whereas GraphRAG advances this approach by graph

[2] LaRA: Benchmarking Retrieval-Augmented Generation and Long-Context LLMs – No Silver Bullet for LC or RAG Routing
    ID: icml-2025-li25dv | ICML 2025 | 引用: 1 | 相关度: 0.0667
    摘要片段: 【R
```

**调用 2: search_abstracts**

输入:
```
{'query': '"chunking strategy" OR "document segmentation" OR "text chunking" RAG', 'limit': 10}
```

输出:
```
[1] Context is Gold to find the Gold Passage: Evaluating and Training Contextual Document Embeddings
    ID: emnlp-2025-main-1150 | EMNLP 2025 | 引用: 0 | 相关度: 0.0499
    摘要片段: robust to suboptimal 【chunking】 【strategies】 and larger retrieval corpus sizes. We opensource all artifacts at https://github.com/ illuin-tech/contextual-embeddings.

[2] Fast and Accurate Factual Inconsistency Detection Over Long Documents
    ID: emnlp-2023-main-105 | EMNLP 2023 | 引用: 3 | 相关度: 0.0474
    摘要片段: 【chunking】 
```

**调用 3: vector_search**

输入:
```
{'query': 'improving chunking strategies in retrieval-augmented generation systems, adaptive chunking, semantic chunking, overlapping chunks', 'top_k': 10}
```

输出:
```
[1] Generation-Augmented Retrieval for Open-Domain Question Answering
    ID: acl-2021-long-316 | ACL 2021 | 引用: 134 | 相似度: 0.6349
    摘要: Yuning Mao, Pengcheng He, Xiaodong Liu, Yelong Shen, Jianfeng Gao, Jiawei Han, Weizhu Chen. Proceedings of the 59th Annual Meeting of the Association for Computational Linguistics and the 11th International Joint Conference on Natural Language Processing (Volume 1: Long Papers). 2021.

[2] Graph Neural Network Enhanced Retrieval for Question Answering of Larg
```

**调用 4: search_abstracts**

输入:
```
{'query': '"adaptive chunking" OR "semantic chunking" OR "overlapping chunks" OR "chunk size optimization"', 'limit': 10}
```

输出:
```
[1] Speech-MLP: a simple MLP architecture for speech processing
    ID: iclr-2022--u8EliRNW8k | ICLR 2022 | 引用: 0 | 相关度: 0.0448
    摘要片段: 【overlapped】 【chunks】 and processes each 【chunk】 individually. The processed 【chunks】 are then

[2] Generative Trajectory Stitching through Diffusion Composition
    ID: neurips-2025-VCTt5DXiBe | NeurIPS 2025 | 引用: 0 | 相关度: 0.0329
    摘要片段: 【overlapping】 【chunks】 and learning their conditional relationships through a single bidirectional diffusion model. This 
```

### Agent 回答（前 200 字）

```
基于我的搜索结果，我找到了关于RAG中chunking策略改进方法的相关研究。让我为您总结：

## RAG中Chunking策略的改进方法

根据相关研究，RAG系统中的chunking策略改进主要集中在以下几个方面：

### 1. **自适应chunking策略**
- **Improving Generative Behavior Cloning via Self-Guidance and
```

---

## Q15 [content] — overall=2.0

| accuracy | completeness | citation | clarity |
|----------|--------------|----------|---------|
| 1 | 2 | 1 | 4 |

**问题**: 长文本处理中的 attention 优化方法有哪些？

**工具调用**: ['vector_search', 'search_abstracts', 'search_abstracts', 'search_abstracts']

**Judge 评语**: 回答结构清晰，但核心内容严重失实，编造了大量未在工具返回数据中出现的方法和引用，导致准确性和引用维度完全失败。

### 工具输出

**调用 1: vector_search**

输入:
```
{'query': 'long text processing attention optimization methods', 'top_k': 10}
```

输出:
```
[1] Curse of High Dimensionality Issue in Transformer for Long Context Modeling
    ID: icml-2025-zhang25cr | ICML 2025 | 引用: 0 | 相似度: 0.6631
    摘要: Transformer-based large language models (LLMs) excel in natural language processing tasks by capturing long-range dependencies through self-attention mechanisms. However, long-context modeling faces significant computational inefficiencies due to \textit{redundant} attention computations: while attention weights are often \textit{sparse}, all token
```

**调用 2: search_abstracts**

输入:
```
{'query': 'long context attention optimization OR efficient attention OR sparse attention', 'limit': 15}
```

输出:
```
[1] MInference 1.0: Accelerating Pre-filling for Long-Context LLMs via Dynamic Sparse Attention
    ID: neurips-2024-5dfbe6f5671e82c7 | NeurIPS 2024 | 引用: 3 | 相关度: 0.0857
    摘要片段: 【sparse】 calculation method designed to accelerate pre-filling of 【long】-sequence processing. Specifically, we identify three unique patterns in 【long】-【context】 【attention】

[2] SCBench: A KV Cache-Centric Analysis of Long-Context Methods
    ID: iclr-2025-gkUyYcY1W9 | ICLR 2025 | 引用: 0 | 相关度: 0.0803
    摘要片段: 【Atten
```

**调用 3: search_abstracts**

输入:
```
{'query': '"linear attention" OR "sliding window attention" OR "local attention" OR "hierarchical attention"', 'limit': 10}
```

输出:
```
[1] Fast Video Generation with Sliding Tile Attention
    ID: icml-2025-zhang25m | ICML 2025 | 引用: 0 | 相关度: 0.0578
    摘要片段: 【sliding】 【window】 【attention】 (SWA), STA operates tile-by-tile with a novel hardware-aware 【sliding】 【window】 design

[2] Rethinking Transformer for Long Contextual Histopathology Whole Slide Image Analysis
    ID: neurips-2024-b7eecb72574b043a | NeurIPS 2024 | 引用: 3 | 相关度: 0.0555
    摘要片段: 【local】 【attention】 mask. Our analysis shows that the 【local】 mask aligns with the
```

**调用 4: search_abstracts**

输入:
```
{'query': '"KV cache" optimization OR "key-value cache" compression OR "attention cache" efficiency', 'limit': 10}
```

输出:
```
[1] Cache Me If You Must: Adaptive Key-Value Quantization for Large Language Models
    ID: icml-2025-shutova25a | ICML 2025 | 引用: 0 | 相关度: 0.0749
    摘要片段: 【Key】-【Value】 【caches】 that relies on compact adapters to exploit existing dependencies between 【Keys】 and 【Values】, and aims to "【optimally】" 【compress】

[2] Ada-KV: Optimizing KV Cache Eviction by Adaptive Budget Allocation for Efficient LLM Inference
    ID: neurips-2025-tcisuhGsQZ | NeurIPS 2025 | 引用: 0 | 相关度: 0.0738
    摘要片段: 【KV】 【cach
```

### Agent 回答（前 200 字）

```
基于我的搜索结果，我可以为您总结长文本处理中的 attention 优化方法。以下是从相关论文中整理出的主要方法：

## 长文本处理中的 Attention 优化方法

### 1. **稀疏注意力（Sparse Attention）**
- **Star Attention** (ICML 2025)：两阶段块稀疏近似，通过跨多个主机分片注意力来减少计算开销
- **FlexPrefill**
```

---

## Q33 [mixed] — overall=2.0

| accuracy | completeness | citation | clarity |
|----------|--------------|----------|---------|
| 1 | 2 | 1 | 4 |

**问题**: AAAI 2024 关于数据增强的论文都用了什么方法？

**工具调用**: ['execute_sql', 'search_abstracts', 'search_abstracts']

**Judge 评语**: 回答结构清晰但内容严重失实，大量编造了不存在的论文和方法，未能基于工具返回的数据进行有效回答。

### 工具输出

**调用 1: execute_sql**

输入:
```
{'sql': "SELECT COUNT(*) as paper_count \nFROM papers \nWHERE year = 2024 AND conference = 'AAAI'\nAND to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,'')) \n@@ to_tsquery('english', 'data <-> augment:* | synthetic <-> data | augment:* <-> data')"}
```

输出:
```
86
```

**调用 2: search_abstracts**

输入:
```
{'query': 'data augmentation OR synthetic data OR data synthesis', 'limit': 15, 'where': "year=2024 AND conference='AAAI'"}
```

输出:
```
[1] Semantic-Aware Data Augmentation for Text-to-Image Synthesis
    ID: aaai-2024-28315 | AAAI 2024 | 引用: 6 | 相关度: 0.0638
    摘要片段: 【Data】 【Augmentation】 (SADA) framework dedicated to T2Isyn. In particular, we propose to 【augment】 texts in the semantic space

[2] Collaborative Synthesis of Patient Records through Multi-Visit Health State Inference
    ID: aaai-2024-29871 | AAAI 2024 | 引用: 3 | 相关度: 0.0613
    摘要片段: 【Synthetic】 EHR generation provides an additional perspective to compensate for t
```

**调用 3: search_abstracts**

输入:
```
{'query': '"mixup" OR "cutmix" OR "cutout" OR "random erasing" OR "label smoothing"', 'limit': 10, 'where': "year=2024 AND conference='AAAI'"}
```

输出:
```
[1] NodeMixup: Tackling Under-Reaching for Graph Neural Networks
    ID: aaai-2024-29328 | AAAI 2024 | 引用: 17 | 相关度: 0.0248
    摘要片段: 【mixup】, and (3) use neighbor 【label】 distribution similarity incorporating node degrees to determine sampling weights for node 【mixup】. Extensive experiments

[2] Curriculum-Enhanced Residual Soft An-Isotropic Normalization for Over-Smoothness in Deep GNNs
    ID: aaai-2024-29256 | AAAI 2024 | 引用: 2 | 相关度: 0.0238
    摘要片段: 【label】-【smoothing】-based learning frame
```

### Agent 回答（前 200 字）

```
基于搜索结果，我为您总结AAAI 2024中关于数据增强的论文使用的主要方法：

## AAAI 2024 数据增强方法总结

### 1. **传统数据增强方法**
- **Mixup及其变体**：多篇论文使用Mixup方法
  - **NodeMixup** (AAAI 2024, 引用17)：用于图神经网络，通过邻居标签分布相似性确定节点混合权重
  - **PL-Mix** (AAAI 2
```

---

## Q40 [mixed] — overall=2.0

| accuracy | completeness | citation | clarity |
|----------|--------------|----------|---------|
| 1 | 2 | 1 | 4 |

**问题**: KDD 2024 高引论文的摘要都在讲什么主题？

**工具调用**: ['execute_sql', 'search_abstracts', 'execute_sql', 'execute_sql', 'execute_sql', 'execute_sql']

**Judge 评语**: 回答结构清晰但内容严重失实，基于编造的数据构建了虚假的论文主题分布，不符合准确性要求。

### 工具输出

**调用 1: execute_sql**

输入:
```
{'sql': "SELECT title, citations, abstract \nFROM papers \nWHERE conference = 'KDD' AND year = 2024 \nORDER BY citations DESC \nLIMIT 20"}
```

输出:
```
title | citations | abstract
----------------------------
Recent and Upcoming Developments in Randomized Numerical Linear Algebra for Machine Learning | 0 | Large matrices arise in many machine learning and data analysis applications, including as representations of datasets, graphs, model weights, and first and second-order derivatives. Randomized Numerical Linear Algebra (RandNLA) is an area which uses randomness to develop improved algorithms for ubiquitous matrix problems. The area has reach
```

**调用 2: search_abstracts**

输入:
```
{'query': 'KDD 2024', 'limit': 15, 'where': "year=2024 AND conference='KDD'"}
```

输出:
```
未找到与 'KDD 2024' 相关的论文。可以尝试换用英文关键词或更宽泛的搜索词。
```

**调用 3: execute_sql**

输入:
```
{'sql': "SELECT COUNT(*) as total_papers FROM papers WHERE conference = 'KDD' AND year = 2024"}
```

输出:
```
151
```

**调用 4: execute_sql**

输入:
```
{'sql': "SELECT \n    CASE \n        WHEN to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,'')) @@ to_tsquery('english', 'recommend:* | recommender') THEN '推荐系统'\n        WHEN to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,'')) @@ to_tsquery('english', 'fraud | anomaly | detect:*') THEN '欺诈检测与异常检测'\n        WHEN to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,'')) @@ to_tsquery('english', 'graph | network') THEN '图数据与网络分析'\n      
```

输出:
```
topic_category | paper_count
----------------------------
图数据与网络分析 | 58
推荐系统 | 35
欺诈检测与异常检测 | 17
其他 | 16
预测与预报 | 12
大语言模型 | 9
多模态学习 | 2
综述与调研 | 2
```

**调用 5: execute_sql**

输入:
```
{'sql': "SELECT title, abstract \nFROM papers \nWHERE conference = 'KDD' AND year = 2024 \nAND to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,'')) @@ to_tsquery('english', 'recommend:* | recommender')\nORDER BY citations DESC \nLIMIT 5"}
```

输出:
```
title | abstract
----------------
Future Impact Decomposition in Request-level Recommendations | In recommender systems, reinforcement learning solutions have shown promising results in optimizing the interaction sequence between users and the system over the long-term performance. For practical reasons, the policy's actions are typically designed as recommending a list of items to handle users' frequent and continuous browsing requests more efficiently. In this list-wise recommendation scenario
```

**调用 6: execute_sql**

输入:
```
{'sql': "SELECT title, abstract \nFROM papers \nWHERE conference = 'KDD' AND year = 2024 \nAND to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,'')) @@ to_tsquery('english', 'graph | network')\nORDER BY citations DESC \nLIMIT 5"}
```

输出:
```
title | abstract
----------------
Recent and Upcoming Developments in Randomized Numerical Linear Algebra for Machine Learning | Large matrices arise in many machine learning and data analysis applications, including as representations of datasets, graphs, model weights, and first and second-order derivatives. Randomized Numerical Linear Algebra (RandNLA) is an area which uses randomness to develop improved algorithms for ubiquitous matrix problems. The area has reached a certain level of maturi
```

### Agent 回答（前 200 字）

```
基于我对KDD 2024论文的分析，以下是主要主题的总结：

## KDD 2024 论文主题分析

KDD 2024共有151篇论文，由于会议刚刚结束，所有论文的引用数目前都是0。以下是主要研究主题分布：

### 1. **图数据与网络分析（58篇，38.4%）**
这是最热门的研究方向，包括：
- **图神经网络（GNNs）**：用于链接预测、节点分类等任务
- **大语言模型与图学习结合*
```

---

## Q43 [content] — overall=2.0

| accuracy | completeness | citation | clarity |
|----------|--------------|----------|---------|
| 1 | 2 | 1 | 4 |

**问题**: 关于 graph neural network 的研究，但不要综述类论文

**工具调用**: ['execute_sql', 'search_abstracts', 'search_abstracts']

**Judge 评语**: 回答结构清晰，但内容严重脱离工具提供的真实数据，编造了大量论文信息，因此准确性和引用有效性极差。

### 工具输出

**调用 1: execute_sql**

输入:
```
{'sql': "SELECT year, conference, COUNT(*) as cnt \nFROM papers \nWHERE to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,'')) \n      @@ to_tsquery('english', 'graph <-> neural <-> network:* | GNN | graph <-> convolut:*')\n  AND year BETWEEN 2020 AND 2025\n  AND NOT to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,'')) \n      @@ to_tsquery('english', 'survey | review | overview | tutorial')\nGROUP BY year, conference \nORDER BY year DESC, cnt DESC"}
```

输出:
```
year | conference | cnt
-----------------------
2025 | AAAI | 169
2025 | NeurIPS | 129
2025 | ICLR | 117
2025 | IJCAI | 80
2025 | ICML | 75
2025 | WWW | 6
2025 | ACL | 5
2025 | EMNLP | 3
2025 | NAACL | 2
2025 | KDD | 1
2024 | AAAI | 144
2024 | ICLR | 93
2024 | NeurIPS | 89
2024 | ICML | 74
2024 | IJCAI | 64
2024 | WWW | 32
2024 | KDD | 28
2023 | ICLR | 205
2023 | NeurIPS | 113
2023 | AAAI | 95

（共 53 条结果，仅显示前 20 条）
```

**调用 2: search_abstracts**

输入:
```
{'query': '"graph neural network" OR GNN OR "graph convolutional" -survey -review -overview -tutorial', 'limit': 15, 'where': 'year >= 2023'}
```

输出:
```
[1] Graph Neural Networks for Databases: A Survey
    ID: ijcai-2025-1172 | IJCAI 2025 | 引用: 0 | 相关度: 0.0574
    摘要片段: 【Graph】 【neural】 【networks】 (GNNs) are powerful deep learning models for 【graph】-structured data, demonstrating remarkable success across diverse

[2] Generalizing CNNs to graphs with learnable neighborhood quantization
    ID: neurips-2024-95ddc8f24ad9698e | NeurIPS 2024 | 引用: 0 | 相关度: 0.0464
    摘要片段: 【Graph】 【Convolution】 【Networks】 (QGCNs), the first framework for GNNs that 
```

**调用 3: search_abstracts**

输入:
```
{'query': '"graph neural network" OR GNN OR "graph convolutional" -survey', 'limit': 15, 'where': 'year >= 2023 AND citations >= 5'}
```

输出:
```
[1] Learnable Graph Convolutional Attention Networks
    ID: iclr-2023-WsUMeHPo-2 | ICLR 2023 | 引用: 6 | 相关度: 0.0676
    摘要片段: 【graph】 【convolutional】 attention 【network】 (L-CAT): a 【GNN】 architecture that automatically interpolates between GCN, GAT and CAT in each

[2] Non-convolutional graph neural networks.
    ID: neurips-2024-397271e11322fae8 | NeurIPS 2024 | 引用: 5 | 相关度: 0.0672
    摘要片段: 【GNN】) -- they characteristically suffer from limited expressiveness, over-smoothing, and over-squashing
```

### Agent 回答（前 200 字）

```
基于搜索结果，我为您整理了近年来关于图神经网络（GNN）的高质量研究论文（非综述类）：

## 图神经网络研究论文精选（2023-2025）

### 1. **高引用量论文**

**Spatio-Temporal Pivotal Graph Neural Networks for Traffic Flow Forecasting** (AAAI 2024, 60次引用)
- 提出时空关键图神经
```

---

## Q25 [mixed] — overall=2.25

| accuracy | completeness | citation | clarity |
|----------|--------------|----------|---------|
| 1 | 2 | 1 | 5 |

**问题**: 最近三年 attention 优化方向的代表性工作有哪些进展？

**工具调用**: ['execute_sql', 'search_abstracts', 'search_abstracts', 'vector_search']

**Judge 评语**: 回答结构清晰，但内容几乎完全虚构，与工具返回的真实数据严重脱节，信息不可信。

### 工具输出

**调用 1: execute_sql**

输入:
```
{'sql': "SELECT year, COUNT(*) as paper_count \nFROM papers \nWHERE to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,'')) \n      @@ to_tsquery('english', 'attention & (optimiz:* | efficient:* | improv:* | enhanc:* | mechanism)')\n  AND year BETWEEN 2023 AND 2025\nGROUP BY year ORDER BY year"}
```

输出:
```
year | paper_count
------------------
2023 | 900
2024 | 980
2025 | 1544
```

**调用 2: search_abstracts**

输入:
```
{'query': '"attention mechanism" optimization OR efficient attention OR attention improvement OR attention enhancement', 'limit': 15, 'where': 'year BETWEEN 2023 AND 2025'}
```

输出:
```
[1] Enhancing Zero-Shot Black-Box Optimization via Pretrained Models with Efficient Population Modeling, Interaction, and Stable Gradient Approximation
    ID: neurips-2025-vLLYlSK6qJ | NeurIPS 2025 | 引用: 0 | 相关度: 0.0750
    摘要片段: 【enhanced】 framework for pre-trained 【optimization】. EPOM enriches task representations using a cross-【attention】-based tokenizer, 【improves】

[2] FlexPrefill: A Context-Aware Sparse Attention Mechanism for Efficient Long-Sequence Inference
    ID: iclr-2025-OfjIlbelrT
```

**调用 3: search_abstracts**

输入:
```
{'query': 'sparse attention OR linear attention OR flash attention OR memory efficient attention', 'limit': 15, 'where': 'year BETWEEN 2023 AND 2025'}
```

输出:
```
[1] Tiled Flash Linear Attention: More Efficient Linear RNN and xLSTM Kernels
    ID: neurips-2025-b6H64u6TqI | NeurIPS 2025 | 引用: 0 | 相关度: 0.0737
    摘要片段: 【Flash】 【Attention】 kernels (Dao, 2024). Leveraging the chunkwise-parallel formulation of 【linear】 RNNs, 【Flash】 【Linear】 【Attention】

[2] Sparse Modular Activation for Efficient Sequence Modeling
    ID: neurips-2023-3f0739410e1c9c5d | NeurIPS 2023 | 引用: 2 | 相关度: 0.0677
    摘要片段: 【attention】 modules statically and uniformly to all elements 
```

**调用 4: vector_search**

输入:
```
{'query': '最近三年注意力机制的理论分析、改进和优化方法，包括稀疏注意力、线性注意力、内存效率优化等', 'top_k': 10, 'where': 'year BETWEEN 2023 AND 2025'}
```

输出:
```
[1] Cognitive Fluctuations Enhanced Attention Network for Knowledge Tracing
    ID: aaai-2025-33562 | AAAI 2025 | 引用: 4 | 相似度: 0.6147
    摘要: Knowledge tracing (KT) involves using the historical records of student-learning interactions to anticipate their performance on forthcoming questions. Central to this process is the modeling of human cognition to gain deeper insights into how knowledge is acquired and retained. Human cognition is characterized by two key features: long-term cognitive tren
```

### Agent 回答（前 200 字）

```
基于我的搜索结果，我为您梳理了最近三年（2023-2025年）在注意力优化方向上的代表性工作进展：

## 主要进展方向

### 1. **高效注意力计算优化**
- **FlashAttention系列**：FlashAttention-3 (NeurIPS 2024) 通过异步计算、低精度量化和硬件优化，在H100 GPU上显著提升注意力计算效率
- **线性注意力**：Tiled Flas
```

---

## Q48 [content] — overall=2.25

| accuracy | completeness | citation | clarity |
|----------|--------------|----------|---------|
| 1 | 3 | 1 | 4 |

**问题**: NeurIPS 2025 引用超过 10 的语义搜索相关论文

**工具调用**: ['execute_sql', 'execute_sql', 'execute_sql', 'search_abstracts', 'vector_search', 'search_abstracts', 'execute_sql', 'execute_sql']

**Judge 评语**: 回答结构清晰，但核心事实严重错误，编造了多篇不存在的论文及其细节。

### 工具输出

**调用 1: execute_sql**

输入:
```
{'sql': "SELECT title, conference, year, citations, authors\nFROM papers \nWHERE conference = 'NeurIPS' \n  AND year = 2025 \n  AND citations > 10\n  AND to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,'')) \n      @@ to_tsquery('english', '(semantic <-> search:*) | (semantic <-> retrieval) | (semantic <-> similarity) | (semantic <-> match:*)')\nORDER BY citations DESC\nLIMIT 20"}
```

输出:
```
查询成功，但未找到匹配结果。
```

**调用 2: execute_sql**

输入:
```
{'sql': "SELECT title, conference, year, citations, authors\nFROM papers \nWHERE conference = 'NeurIPS' \n  AND year = 2025 \n  AND citations > 10\n  AND to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,'')) \n      @@ to_tsquery('english', '(semantic <-> search:*) | (vector <-> search:*) | (embedding <-> retrieval) | (dense <-> retrieval) | (semantic <-> match:*) | (neural <-> retrieval)')\nORDER BY citations DESC\nLIMIT 20"}
```

输出:
```
查询成功，但未找到匹配结果。
```

**调用 3: execute_sql**

输入:
```
{'sql': "SELECT title, conference, year, citations, authors\nFROM papers \nWHERE conference = 'NeurIPS' \n  AND year = 2025 \n  AND citations > 10\nORDER BY citations DESC\nLIMIT 20"}
```

输出:
```
title | conference | year | citations | authors
-----------------------------------------------
YOLOv12: Attention-Centric Real-Time Object Detectors | NeurIPS | 2025 | 175 | ['Yunjie Tian', 'Qixiang Ye', 'David Doermann']
Simple and Efficient Heterogeneous Temporal Graph Neural Network | NeurIPS | 2025 | 171 | ['YiliWang', 'Tairan Huang', 'Changlong He', 'Qiutong Li', 'Jianliang Gao']
Attention on the Sphere | NeurIPS | 2025 | 39 | ['Boris Bonev', 'Max Rietmann', 'Andrea Paris', 'Alberto Carpen
```

**调用 4: search_abstracts**

输入:
```
{'query': 'semantic search OR vector search OR embedding retrieval', 'where': "conference='NeurIPS' AND year=2025 AND citations > 10", 'limit': 10}
```

输出:
```
未找到与 'semantic search OR vector search OR embedding retrieval' 相关的论文。可以尝试换用英文关键词或更宽泛的搜索词。
```

**调用 5: vector_search**

输入:
```
{'query': 'semantic search neural information retrieval dense retrieval methods', 'where': "conference='NeurIPS' AND year=2025 AND citations > 10", 'top_k': 10}
```

输出:
```
[1] YOLOv12: Attention-Centric Real-Time Object Detectors
    ID: neurips-2025-gCvByDI4FN | NeurIPS 2025 | 引用: 175 | 相似度: 0.4391
    摘要: Enhancing the network architecture of the YOLO framework has been crucial for a long time. Still, it has focused on CNN-based improvements despite the proven superiority of attention mechanisms in modeling capabilities. This is because attention-based models cannot match the speed of CNN-based models. This paper proposes an attention-centric YOLO framework, nam
```

**调用 6: search_abstracts**

输入:
```
{'query': 'retrieval OR information retrieval OR search methods', 'where': "conference='NeurIPS' AND year=2025 AND citations > 10", 'limit': 10}
```

输出:
```
未找到与 'retrieval OR information retrieval OR search methods' 相关的论文。可以尝试换用英文关键词或更宽泛的搜索词。
```

**调用 7: execute_sql**

输入:
```
{'sql': "SELECT title, conference, year, citations, authors\nFROM papers \nWHERE conference = 'NeurIPS' \n  AND year = 2025\n  AND to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,'')) \n      @@ to_tsquery('english', '(semantic <-> search:*) | (vector <-> search:*) | (embedding <-> retrieval) | (dense <-> retrieval) | (retrieval <-> augment:*) | (information <-> retrieval)')\nORDER BY citations DESC\nLIMIT 20"}
```

输出:
```
title | conference | year | citations | authors
-----------------------------------------------
AgentNet: Decentralized Evolutionary Coordination for LLM-based Multi-Agent Systems | NeurIPS | 2025 | 5 | ['Yingxuan Yang', 'Huacan Chai', 'Shuai Shao', 'Yuanyi Song', 'Siyuan Qi', 'Renting Rui', 'Weinan Zhang']
Chain-of-Retrieval Augmented Generation | NeurIPS | 2025 | 3 | ['Liang Wang', 'Haonan Chen', 'Nan Yang', 'Xiaolong Huang', 'Zhicheng Dou', 'Furu Wei']
Improving Retrieval-Augmented Generation
```

**调用 8: execute_sql**

输入:
```
{'sql': "SELECT title, conference, year, citations, authors\nFROM papers \nWHERE conference = 'NeurIPS' \n  AND year = 2025\n  AND citations > 10\n  AND (\n    title ILIKE '%retrieval%' OR \n    title ILIKE '%search%' OR\n    abstract ILIKE '%retrieval%' OR\n    abstract ILIKE '%search%'\n  )\nORDER BY citations DESC\nLIMIT 20"}
```

输出:
```
查询成功，但未找到匹配结果。
```

### Agent 回答（前 200 字）

```
基于我的搜索结果，我发现了以下情况：

## 查询结果总结

**NeurIPS 2025 年引用超过10的语义搜索相关论文：**

**很遗憾，目前没有找到 NeurIPS 2025 年引用数超过10的语义搜索相关论文。**

### 发现的相关论文（但引用数低于10）：

1. **Chain-of-Retrieval Augmented Generation** (NeurIPS 2025)
```

---

## Q31 [content] — overall=2.5

| accuracy | completeness | citation | clarity |
|----------|--------------|----------|---------|
| 1 | 3 | 1 | 5 |

**问题**: 有哪些关于 prompt engineering 的研究？

**工具调用**: ['search_abstracts', 'vector_search', 'execute_sql', 'execute_sql']

**Judge 评语**: 回答结构清晰，但内容严重偏离工具数据，包含大量编造的事实和引用，准确性极低。

### 工具输出

**调用 1: search_abstracts**

输入:
```
{'query': 'prompt engineering OR prompt tuning OR prompt learning', 'limit': 15}
```

输出:
```
[1] DP-OPT: Make Large Language Model Your Privacy-Preserving Prompt Engineer
    ID: iclr-2024-Ifz3IgsEPX | ICLR 2024 | 引用: 5 | 相关度: 0.0801
    摘要片段: 【prompt】 【tuning】. Nevertheless, concerns surrounding data privacy present obstacles due to the 【tuned】 【prompts】' dependency on sensitive

[2] COMMA: Co-articulated Multi-Modal Learning
    ID: aaai-2024-27997 | AAAI 2024 | 引用: 4 | 相关度: 0.0800
    摘要片段: 【prompt】 templates to achieve satisfactory performance. Recently, various methods have been pr
```

**调用 2: vector_search**

输入:
```
{'query': 'prompt engineering techniques and methods for large language models', 'top_k': 10}
```

输出:
```
[1] LLMLingua: Compressing Prompts for Accelerated Inference of Large Language Models
    ID: emnlp-2023-main-825 | EMNLP 2023 | 引用: 78 | 相似度: 0.6991
    摘要: Large language models (LLMs) have been applied in various applications due to their astonishing capabilities. With advancements in technologies such as chain-of-thought (CoT) prompting and in-context learning (ICL), the prompts fed to LLMs are becoming increasingly lengthy, even exceeding tens of thousands of tokens. To accelerate model inf
```

**调用 3: execute_sql**

输入:
```
{'sql': "SELECT year, COUNT(*) as paper_count\nFROM papers\nWHERE to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,''))\n      @@ to_tsquery('english', 'prompt & (engineer:* | tun:* | learn:*)')\n  AND year BETWEEN 2020 AND 2025\nGROUP BY year\nORDER BY year DESC"}
```

输出:
```
year | paper_count
------------------
2025 | 895
2024 | 596
2023 | 426
2022 | 153
2021 | 30
2020 | 9
```

**调用 4: execute_sql**

输入:
```
{'sql': "SELECT conference, COUNT(*) as paper_count\nFROM papers\nWHERE to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,''))\n      @@ to_tsquery('english', 'prompt & (engineer:* | tun:* | learn:*)')\n  AND year BETWEEN 2020 AND 2025\n  AND conference IS NOT NULL\nGROUP BY conference\nORDER BY paper_count DESC\nLIMIT 10"}
```

输出:
```
conference | paper_count
------------------------
NeurIPS | 525
ICLR | 459
AAAI | 388
ICML | 238
EMNLP | 182
IJCAI | 127
ACL | 113
NAACL | 39
WWW | 27
KDD | 11
```

### Agent 回答（前 200 字）

```
基于我的搜索结果，以下是关于 prompt engineering 研究的主要发现：

## 研究概况

从2020年到2025年，prompt engineering 相关研究呈现爆炸式增长：
- **2020年**：9篇 → **2025年**：895篇（增长近100倍）
- 主要发表会议：NeurIPS（525篇）、ICLR（459篇）、AAAI（388篇）

## 主要研究方向

### 
```

---

## Q39 [content] — overall=2.5

| accuracy | completeness | citation | clarity |
|----------|--------------|----------|---------|
| 1 | 2 | 2 | 5 |

**问题**: 有没有关于 neurosymbolic AI 的论文？

**工具调用**: ['search_abstracts', 'vector_search', 'execute_sql', 'execute_sql', 'execute_sql']

**Judge 评语**: 回答结构清晰但内容严重失实，编造了大量未在工具数据中出现的统计和论文信息，不符合基于证据回答的要求。

### 工具输出

**调用 1: search_abstracts**

输入:
```
{'query': 'neurosymbolic OR neuro-symbolic OR "neural symbolic" OR "symbolic reasoning" neural', 'limit': 15}
```

输出:
```
[1] Learning where and when to reason in neuro-symbolic inference
    ID: iclr-2023-en9V5F8PR- | ICLR 2023 | 引用: 0 | 相关度: 0.0717
    摘要片段: 【neuro】-【symbolic】 perspective. Our pipeline enhances a conventional 【neural】 predictor with (1) a 【symbolic】 【reasoning】

[2] Abstract Visual Reasoning by Self-supervised Contrastive Learning
    ID: iclr-2023-AvSIqjCWVId | ICLR 2023 | 引用: 0 | 相关度: 0.0700
    摘要片段: 【Neuro】-【symbolic】 models of artificial intelligence (AI) have been recently developed to perf
```

**调用 2: vector_search**

输入:
```
{'query': 'neurosymbolic artificial intelligence combining neural networks with symbolic reasoning', 'top_k': 10}
```

输出:
```
[1] From Statistical Relational to Neuro-Symbolic Artificial Intelligence
    ID: aaai-2024-30294 | AAAI 2024 | 引用: 100 | 相似度: 0.7689
    摘要: Neuro-symbolic and statistical relational artificial intelligence both integrate frameworks for learning with logical reasoning. This survey identifies several parallels across seven different dimensions between these two fields. These cannot only be used to characterize and position neuro-symbolic artificial intelligence approaches but also to identify a 
```

**调用 3: execute_sql**

输入:
```
{'sql': 'SELECT year, COUNT(*) as count\nFROM papers\nWHERE to_tsvector(\'english\', COALESCE(title,\'\') || \' \' || COALESCE(abstract,\'\'))\n      @@ to_tsquery(\'english\', \'neurosymbolic | neuro-symbolic | "neural symbolic"\')\nGROUP BY year\nORDER BY year DESC'}
```

输出:
```
SQL 语法错误: syntax error in tsquery: "neurosymbolic | neuro-symbolic | "neural symbolic""。请检查 SQL 语法后重试。
```

**调用 4: execute_sql**

输入:
```
{'sql': "SELECT year, COUNT(*) as count\nFROM papers\nWHERE to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,''))\n      @@ to_tsquery('english', 'neurosymbolic | neuro-symbolic | neural & symbolic')\nGROUP BY year\nORDER BY year DESC"}
```

输出:
```
year | count
------------
2025 | 124
2024 | 73
2023 | 95
2022 | 65
2021 | 84
2020 | 48
```

**调用 5: execute_sql**

输入:
```
{'sql': "SELECT title, year, conference, citations\nFROM papers\nWHERE to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,''))\n      @@ to_tsquery('english', 'neurosymbolic | neuro-symbolic | neural & symbolic')\nORDER BY citations DESC\nLIMIT 10"}
```

输出:
```
title | year | conference | citations
-------------------------------------
Least-to-Most Prompting Enables Complex Reasoning in Large Language Models | 2023 | ICLR | 317
Discovering Symbolic Models from Deep Learning with Inductive Biases | 2020 | NeurIPS | 269
Symbolic Discovery of Optimization Algorithms | 2023 | NeurIPS | 165
Efficient Verification of ReLU-Based Neural Networks via Dependency Analysis | 2020 | AAAI | 105
NeurASP: Embracing Neural Networks into Answer Set Programming | 2020 |
```

### Agent 回答（前 200 字）

```
基于我的搜索结果，我为您找到了关于神经符号人工智能（Neuro-Symbolic AI）的丰富论文资源。以下是主要发现：

## 📊 神经符号AI论文概览

**年度分布（2020-2025）：**
- 2025年：124篇（最新）
- 2024年：73篇
- 2023年：95篇
- 2022年：65篇
- 2021年：84篇
- 2020年：48篇

## 🔝 高引用论文

1. **"Leas
```

---

## Q14 [content] — overall=2.75

| accuracy | completeness | citation | clarity |
|----------|--------------|----------|---------|
| 1 | 4 | 1 | 5 |

**问题**: 多模态大模型的视觉编码器通常怎么设计？

**工具调用**: ['vector_search', 'search_abstracts', 'search_abstracts', 'search_abstracts', 'execute_sql']

**Judge 评语**: 回答结构清晰、内容看似全面，但引用了大量工具数据中不存在的论文，导致事实准确性严重失实，不符合基于给定数据回答的要求。

### 工具输出

**调用 1: vector_search**

输入:
```
{'query': '多模态大模型视觉编码器设计 architecture design of visual encoders in multimodal large language models', 'top_k': 10}
```

输出:
```
[1] Words Over Pixels? Rethinking Vision in Multimodal Large Language Models
    ID: ijcai-2025-1164 | IJCAI 2025 | 引用: 0 | 相似度: 0.6497
    摘要: Multimodal Large Language Models (MLLMs) promise seamless integration of vision and language understanding. However, despite their strong performance, recent studies reveal that MLLMs often fail to effectively utilize visual information, frequently relying on textual cues instead. This survey provides a comprehensive analysis of the vision component in M
```

**调用 2: search_abstracts**

输入:
```
{'query': 'visual encoder architecture design multimodal large language model', 'limit': 10}
```

输出:
```
[1] Eagle: Exploring The Design Space for Multimodal LLMs with Mixture of Encoders
    ID: iclr-2025-Y2RW9EVwhT | ICLR 2025 | 引用: 1 | 相关度: 0.8788
    摘要片段: 【multimodal】 【large】 【language】 【models】 (MLLMs). Recent work indicates that enhanced 【visual】 perception significantly reduces hallucinations and improves performance on resolution-sensitive tasks, such as optical character recognition and document analysis. A number of recent MLLMs achieve this goal using a mixture of vision 【encoders】. Des
```

**调用 3: search_abstracts**

输入:
```
{'query': '"vision encoder" OR "visual encoder" multimodal transformer ViT CLIP', 'limit': 10}
```

输出:
```
[1] Connecting Giants: Synergistic Knowledge Transfer of Large Multimodal Models for Few-Shot Learning
    ID: ijcai-2025-0693 | IJCAI 2025 | 引用: 1 | 相关度: 0.0642
    摘要片段: 【vision】 【encoder】 as a weak student, distilling semantic-aligned 【visual】 knowledge via an unsupervised proxy task. Subsequently, a training

[2] FeatSharp: Your Vision Model Features, Sharper
    ID: icml-2025-ranzinger25a | ICML 2025 | 引用: 0 | 相关度: 0.0631
    摘要片段: 【vision】 【encoders】 are fundamental to myriad modern AI tas
```

**调用 4: search_abstracts**

输入:
```
{'query': 'survey review vision encoder design multimodal large language models', 'limit': 8}
```

输出:
```
未找到与 'survey review vision encoder design multimodal large language models' 相关的论文。可以尝试换用英文关键词或更宽泛的搜索词。
```

**调用 5: execute_sql**

输入:
```
{'sql': "SELECT title, year, conference, citations \nFROM papers \nWHERE to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,'')) \n      @@ to_tsquery('english', '(vision <-> encoder) | (visual <-> encoder) | (multimodal <-> model) & (design | architecture)')\nORDER BY citations DESC \nLIMIT 15"}
```

输出:
```
title | year | conference | citations
-------------------------------------
Visual Instruction Tuning | 2023 | NeurIPS | 667
MiniGPT-4: Enhancing Vision-Language Understanding with Advanced Large Language Models | 2024 | ICLR | 470
HorNet: Efficient High-Order Spatial Interactions with Recursive Gated Convolutions | 2022 | NeurIPS | 185
How Much Can CLIP Benefit Vision-and-Language Tasks? | 2022 | ICLR | 152
Multimodal Few-Shot Learning with Frozen Language Models | 2021 | NeurIPS | 86
OmniVL: O
```

### Agent 回答（前 200 字）

```
基于我找到的相关论文，我来为您总结多模态大模型中视觉编码器的设计方法：

## 多模态大模型视觉编码器设计方法

### 1. **主流架构选择**
根据最新研究，多模态大模型（MLLMs）的视觉编码器主要有以下几种设计：

**a) 预训练视觉编码器 + 适配器架构**
- **Eagle: Exploring The Design Space for Multimodal LLMs with 
```

---

## Q16 [content] — overall=2.75

| accuracy | completeness | citation | clarity |
|----------|--------------|----------|---------|
| 1 | 4 | 1 | 5 |

**问题**: 知识蒸馏在大模型压缩中的应用效果如何？

**工具调用**: ['search_abstracts', 'search_abstracts', 'vector_search']

**Judge 评语**: 回答结构清晰、内容全面，但严重偏离了工具返回的数据，编造了大量论文和具体数据，事实准确性极差。

### 工具输出

**调用 1: search_abstracts**

输入:
```
{'query': 'knowledge distillation large model compression OR model compression large language models', 'limit': 15}
```

输出:
```
[1] Adversarial Data Augmentation for Task-Specific Knowledge Distillation of Pre-trained Transformers
    ID: aaai-2022-21423 | AAAI 2022 | 引用: 9 | 相关度: 0.0861
    摘要片段: 【knowledge】 transfer when 【compressing】 【large】 pre-trained transformer 【models】. Different from prior methods, AD^2 performs 【distillation】

[2] Unified Knowledge Maintenance Pruning and Progressive Recovery with Weight Recalling for Large Vision-Language Models
    ID: aaai-2025-32923 | AAAI 2025 | 引用: 1 | 相关度: 0.0819
    摘要片
```

**调用 2: search_abstracts**

输入:
```
{'query': '"knowledge distillation" LLM compression effectiveness OR performance evaluation', 'limit': 10}
```

输出:
```
[1] TAID: Temporally Adaptive Interpolated Distillation for Efficient Knowledge Transfer in Language Models
    ID: iclr-2025-cqsw28DuMW | ICLR 2025 | 引用: 0 | 相关度: 0.0642
    摘要片段: 【compression】.
A significant remaining issue lies in the major differences between teacher and student models, namely the substantial capacity gap, mode averaging, and mode collapse, which pose barriers during 【distillation】.
To address these issues, we introduce $\textit{Temporally Adaptive Interpolated 【Distillation
```

**调用 3: vector_search**

输入:
```
{'query': 'What are the effectiveness and challenges of knowledge distillation for compressing large language models? How well does it preserve model performance while reducing size?', 'top_k': 8}
```

输出:
```
[1] Distilling Linguistic Context for Language Model Compression
    ID: emnlp-2021-main-30 | EMNLP 2021 | 引用: 24 | 相似度: 0.7441
    摘要: A computationally expensive and memory intensive neural network lies behind the recent success of language representation learning. Knowledge distillation, a major technique for deploying such a vast language model in resource-scarce environments, transfers the knowledge on individual word representations learned without restrictions. In this paper, inspired by 
```

### Agent 回答（前 200 字）

```
基于我搜索到的论文，我来为您分析知识蒸馏在大模型压缩中的应用效果：

## 知识蒸馏在大模型压缩中的应用效果分析

### 1. **主要应用效果**

**压缩效果显著：**
- **参数减少**：知识蒸馏可以将大模型压缩到原大小的1/12.7到1/29.3倍（AdaBERT, IJCAI 2020）
- **推理加速**：压缩后模型推理速度提升12.7x到29.3x（AdaBERT, IJCA
```

---

## Q19 [content] — overall=2.75

| accuracy | completeness | citation | clarity |
|----------|--------------|----------|---------|
| 1 | 4 | 1 | 5 |

**问题**: 向量数据库在 RAG 中的索引方式有哪些？

**工具调用**: ['search_abstracts', 'search_abstracts', 'vector_search', 'search_abstracts', 'search_abstracts', 'vector_search']

**Judge 评语**: 回答结构清晰、内容看似全面，但绝大部分事实和引用是编造的，与工具返回数据严重不符，准确性极差。

### 工具输出

**调用 1: search_abstracts**

输入:
```
{'query': 'vector database indexing RAG retrieval-augmented generation', 'limit': 10}
```

输出:
```
未找到与 'vector database indexing RAG retrieval-augmented generation' 相关的论文。可以尝试换用英文关键词或更宽泛的搜索词。
```

**调用 2: search_abstracts**

输入:
```
{'query': 'vector index OR embedding index retrieval augmented generation', 'limit': 10}
```

输出:
```
[1] ColPali: Efficient Document Retrieval with Vision Language Models
    ID: iclr-2025-ogjBpZ8uSi | ICLR 2025 | 引用: 4 | 相关度: 0.0688
    摘要片段: 【index】 documents -often through lengthy and brittle processes-, they struggle to exploit key visual cues efficiently. This limits their capabilities in many practical document 【retrieval】 applications such as 【Retrieval】 【Augmented】 【Generation】 (RAG).
To benchmark current systems on visually rich document 【retrieval】, we introduce the Visual Document 【R
```

**调用 3: vector_search**

输入:
```
{'query': 'vector database indexing methods for retrieval augmented generation RAG systems', 'top_k': 10}
```

输出:
```
[1] Retrieval-Augmented Visual Question Answering via Built-in Autoregressive Search Engines
    ID: aaai-2025-34653 | AAAI 2025 | 引用: 3 | 相似度: 0.6767
    摘要: Retrieval-augmented generation (RAG) has emerged to address the knowledge-intensive visual question answering (VQA) task. Current methods mainly employ separate retrieval and generation modules to acquire external knowledge and generate answers, respectively. We propose ReAuSE, an alternative to the previous RAG model for the knowledge-bas
```

**调用 4: search_abstracts**

输入:
```
{'query': '"approximate nearest neighbor" OR ANN OR HNSW OR IVF index vector retrieval', 'limit': 10}
```

输出:
```
[1] AdANNS: A Framework for Adaptive Semantic Search
    ID: neurips-2023-f062da1973ac9ac6 | NeurIPS 2023 | 引用: 0 | 相关度: 0.0574
    摘要片段: 【ANNS】 building blocks like search data structures (AdANNS-【IVF】) and quantization (AdANNS-OPQ). For example on ImageNet 【retrieval】, AdANNS-【IVF】

[2] RetrievalAttention: Accelerating Long-Context LLM Inference via Vector Retrieval
    ID: neurips-2025-8z3cOVER4z | NeurIPS 2025 | 引用: 1 | 相关度: 0.0562
    摘要片段: 【ANNS】) 【indexes】 into attention computation. We o
```

**调用 5: search_abstracts**

输入:
```
{'query': 'product quantization OR PQ OR scalar quantization vector index', 'limit': 10}
```

输出:
```
[1] Learning Discrete Representations via Constrained Clustering for Effective and Efficient Dense Retrieval (Extended Abstract)
    ID: ijcai-2023-0728 | IJCAI 2023 | 引用: 0 | 相关度: 0.0569
    摘要片段: 【Product】 【Quantization】~(【PQ】) method to learn discrete document representations and enables fast approximate NNS with compact 【indexes】. It models

[2] Learning Discrete Representations via Constrained Clustering for Effective and Efficient Dense Retrieval (Extended Abstract)
    ID: ijcai-2022-0754
```

**调用 6: vector_search**

输入:
```
{'query': 'vector indexing architecture for retrieval augmented generation systems design patterns', 'top_k': 8}
```

输出:
```
[1] Retrieval-Augmented Visual Question Answering via Built-in Autoregressive Search Engines
    ID: aaai-2025-34653 | AAAI 2025 | 引用: 3 | 相似度: 0.6444
    摘要: Retrieval-augmented generation (RAG) has emerged to address the knowledge-intensive visual question answering (VQA) task. Current methods mainly employ separate retrieval and generation modules to acquire external knowledge and generate answers, respectively. We propose ReAuSE, an alternative to the previous RAG model for the knowledge-bas
```

### Agent 回答（前 200 字）

```
基于我的搜索结果，我可以为您总结向量数据库在RAG系统中的主要索引方式：

## 向量数据库在RAG中的索引方式

根据相关研究论文，向量数据库在检索增强生成（RAG）系统中主要采用以下几种索引方式：

### 1. **近似最近邻搜索（ANN）索引**
这是RAG系统中最常用的索引方式，用于高效检索高维向量空间中的相似文档：

- **HNSW（Hierarchical Navigable Sm
```

---

## Q20 [content] — overall=2.75

| accuracy | completeness | citation | clarity |
|----------|--------------|----------|---------|
| 1 | 4 | 1 | 5 |

**问题**: LLM 幻觉问题的主要缓解策略有哪些？

**工具调用**: ['vector_search', 'search_abstracts', 'search_abstracts', 'search_abstracts']

**Judge 评语**: 回答结构清晰、内容全面，但核心信息和引用严重偏离了工具提供的证据，存在大量事实性错误和编造。

### 工具输出

**调用 1: vector_search**

输入:
```
{'query': 'LLM hallucination mitigation strategies techniques to reduce large language model hallucinations', 'top_k': 10}
```

输出:
```
[1] Alleviating Hallucinations in Large Vision-Language Models through Hallucination-Induced Optimization
    ID: neurips-2024-dde040998d82553c | NeurIPS 2024 | 引用: 1 | 相似度: 0.7209
    摘要: Although Large Visual Language Models (LVLMs) have demonstrated exceptional abilities in understanding multimodal data, they invariably suffer from hallucinations, leading to a disconnect between the generated text and the corresponding images. Almost all current visual contrastive decoding methods attempt to 
```

**调用 2: search_abstracts**

输入:
```
{'query': '"LLM hallucination" mitigation OR "reduce hallucinations" large language model', 'limit': 10}
```

输出:
```
[1] Mitigating Hallucination in VideoLLMs via Temporal-Aware Activation Engineering
    ID: neurips-2025-7mTECPRtll | NeurIPS 2025 | 引用: 0 | 相关度: 0.0772
    摘要片段: 【language】 【models】 (MLLMs) have achieved remarkable progress in video understanding. However, 【hallucination】, where the 【model】 generates plausible yet incorrect outputs, persists as a significant and under-addressed challenge in the video domain. Among existing solutions, activation engineering has proven successful in 【mitigating】 
```

**调用 3: search_abstracts**

输入:
```
{'query': '"retrieval-augmented generation" hallucination OR "knowledge graph" hallucination OR "contrastive decoding" hallucination', 'limit': 10}
```

输出:
```
[1] G-Retriever: Retrieval-Augmented Generation for Textual Graph Understanding and Question Answering
    ID: neurips-2024-efaf1c9726648c8b | NeurIPS 2024 | 引用: 22 | 相关度: 0.0680
    摘要片段: 【retrieval】-【augmented】 【generation】 (RAG) approach for general textual 【graphs】, which can be fine-tuned to enhance 【graph】 understanding via soft prompting. To resist 【hallucination】

[2] RealRAG: Retrieval-augmented Realistic Image Generation via Self-reflective Contrastive Learning
    ID: icml-2025-lyu25c
```

**调用 4: search_abstracts**

输入:
```
{'query': '"hallucination detection" OR "hallucination evaluation" large language model', 'limit': 10}
```

输出:
```
[1] Detecting and Preventing Hallucinations in Large Vision Language Models
    ID: aaai-2024-29771 | AAAI 2024 | 引用: 94 | 相关度: 0.0843
    摘要片段: 【Hallucination】 【Detection】 Dataset that can be used to train and benchmark 【models】 for 【hallucination】 【detection】 and prevention. M-HalDetect

[2] K-HALU: Multiple Answer Korean Hallucination Benchmark for Large Language Models
    ID: iclr-2025-VnLhUogHYE | ICLR 2025 | 引用: 0 | 相关度: 0.0836
    摘要片段: 【hallucination】 【detection】 capabilities of LLMs is
```

### Agent 回答（前 200 字）

```
基于我找到的研究论文，以下是关于LLM幻觉问题的主要缓解策略：

## LLM幻觉问题的主要缓解策略

### 1. **检索增强生成（Retrieval-Augmented Generation, RAG）**
- **原理**：通过检索外部知识库来增强LLM的生成过程，减少对参数化知识的依赖
- **代表工作**：
  - **GE-Chat** (IJCAI 2025)：知识图谱增强的RAG
```

---

## Q42 [content] — overall=2.75

| accuracy | completeness | citation | clarity |
|----------|--------------|----------|---------|
| 2 | 3 | 2 | 4 |

**问题**: 2024 年高引的 self-supervised learning 论文有哪些？

**工具调用**: ['execute_sql', 'search_abstracts', 'execute_sql']

**Judge 评语**: 回答结构清晰，但核心事实存在严重错误，编造了多篇论文并错误归类，导致准确性和引用可信度极低。

### 工具输出

**调用 1: execute_sql**

输入:
```
{'sql': "SELECT title, conference, year, citations, authors\nFROM papers \nWHERE year = 2024 \nAND citations > 0\nAND (\n    to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,'')) \n    @@ to_tsquery('english', 'self-supervised | self <-> supervised | unsupervised <-> pre-train:* | contrastive <-> learn:* | pretext <-> task')\n)\nORDER BY citations DESC \nLIMIT 20"}
```

输出:
```
title | conference | year | citations | authors
-----------------------------------------------
Large Language Model Based Multi-agents: A Survey of Progress and Challenges | IJCAI | 2024 | 179 | ['Taicheng Guo', 'Xiuying Chen', 'Yaqi Wang', 'Ruidi Chang', 'Shichao Pei', 'Nitesh V. Chawla', 'Olaf Wiest', 'Xiangliang Zhang']
Incomplete Contrastive Multi-View Clustering with High-Confidence Guiding | AAAI | 2024 | 75 | ['Guoqing Chao', 'Yi Jiang', 'Dianhui Chu']
TimesURL: Self-Supervised Contrasti
```

**调用 2: search_abstracts**

输入:
```
{'query': '"self-supervised learning" OR "self supervised" OR contrastive learning OR pretext task', 'where': 'year=2024 AND citations >= 10', 'limit': 15}
```

输出:
```
[1] TimesURL: Self-Supervised Contrastive Learning for Universal Time Series Representation Learning
    ID: aaai-2024-29299 | AAAI 2024 | 引用: 66 | 相关度: 0.0730
    摘要片段: 【self】-【supervised】 【contrastive】 【learning】 (SSCL) in Computer Vision(CV) and Natural Language Processing(NLP) to tackle time

[2] MM-Point: Multi-View Information-Enhanced Multi-Modal Self-Supervised 3D Point Cloud Understanding
    ID: aaai-2024-28501 | AAAI 2024 | 引用: 11 | 相关度: 0.0674
    摘要片段: 【self】-【supervised】 signals fo
```

**调用 3: execute_sql**

输入:
```
{'sql': "SELECT title, conference, year, citations, authors\nFROM papers \nWHERE year = 2024 \nAND citations >= 20\nAND conference IN ('ICLR', 'NeurIPS', 'ICML')\nAND (\n    to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,'')) \n    @@ to_tsquery('english', 'self-supervised | self <-> supervised | contrastive <-> learn:* | pretext <-> task')\n)\nORDER BY citations DESC \nLIMIT 15"}
```

输出:
```
title | conference | year | citations | authors
-----------------------------------------------
Vision Transformers Need Registers | ICLR | 2024 | 47 | ['Timothée Darcet', 'Maxime Oquab', 'Julien Mairal', 'Piotr Bojanowski']
BrainLM: A foundation model for brain activity recordings | ICLR | 2024 | 35 | ['Josue Ortega Caro', 'Antonio Henrique de Oliveira Fonseca', 'Syed A Rizvi', 'Matteo Rosati', 'Christopher Averill', 'James L Cross', 'Prateek Mittal', 'Emanuele Zappala', 'Rahul Madhav Dhodapkar
```

### Agent 回答（前 200 字）

```
基于搜索结果，我为您整理了2024年高引用的自监督学习论文。以下是引用量较高的代表性论文：

## 2024年高引用自监督学习论文

### 高引用论文（引用量≥40）

1. **Large Language Model Based Multi-agents: A Survey of Progress and Challenges** (IJCAI 2024) - **179次引用**
   -
```
