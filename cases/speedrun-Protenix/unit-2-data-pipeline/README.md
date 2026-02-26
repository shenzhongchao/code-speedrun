# Unit 2: 数据管线 — 从序列到特征

## 通俗理解

把数据管线想象成一位"翻译官"：它的工作是把人类可读的蛋白质序列（一串氨基酸字母，如 `MKFLILLFNILCLFPVLAADNH...`）翻译成机器可读的数字矩阵。就像把一本外语书翻译成计算机能处理的数据表格——原始文字对模型毫无意义，只有转换成张量之后，神经网络才能开始"阅读"。

整个管线可以概括为一句话：

> **字母串 → Token数组 → 特征张量 → 模型输入**

---

## 背景知识

- **氨基酸**：自然界中有 20 种标准氨基酸，每种拥有不同的化学性质（大小、电荷、疏水性等）。蛋白质就是由这 20 种"积木"按特定顺序拼接而成的长链。
- **蛋白质一级结构**：氨基酸的线性排列顺序，用单字母代码表示，例如 `A`=丙氨酸、`G`=甘氨酸。
- **主链与侧链**：每个氨基酸都有相同的主链骨架（N-CA-C 三个原子），区别在于侧链（R 基团）。侧链原子数从 0（甘氨酸）到 10+（色氨酸）不等。
- **One-hot 编码**：将类别变量转为二进制向量。例如 20 种氨基酸中的第 3 种 → `[0,0,1,0,...,0]`。
- **MSA（多序列比对）的生物学意义**：通过搜索序列数据库找到进化上的"亲戚"序列。进化保守的位置（所有亲戚都一样的列）往往在结构和功能上至关重要。
- **模板**：已知三维结构的同源蛋白质，为模型提供"参考答案"。如果数据库中有一个结构已解析的近亲蛋白，模型可以借鉴它的骨架构型。

---

## 关键术语

| 术语 | 含义 |
|------|------|
| **Residue（残基）** | 蛋白质链中的一个氨基酸单元，是序列层面的基本单位 |
| **Token** | Protenix 中的基本处理单位。对蛋白质来说，一个 token = 一个残基；对核酸等其他分子可能不同 |
| **TokenArray** | 存储所有 token 信息的核心数据结构，包含残基类型、原子坐标、键连接等 |
| **Featurizer** | 将 TokenArray 转换为模型输入张量的处理器，是管线的核心环节 |
| **restype** | 残基类型的 one-hot 编码，形状 `[N_token, 32]`（32 维包含 20 种标准氨基酸 + 非标准类型 + padding） |
| **ref_pos** | 参考原子坐标，形状 `[N_atom, 3]`，表示理想化几何构型下每个原子的三维位置 |
| **atom_to_token_idx** | 原子到 token 的映射索引，形状 `[N_atom]`，告诉模型每个原子属于哪个残基 |
| **ref_element** | 原子元素类型的 one-hot 编码，形状 `[N_atom, 128]`，区分 C/N/O/S 等元素 |
| **token_bonds** | token 之间的共价键连接矩阵，形状 `[N_token, N_token]` |
| **MSA** | 多序列比对矩阵，形状 `[N_seq, N_token]`，每个元素是氨基酸类型索引 |

---

## 本单元做什么

本单元通过一个自包含的 Python 脚本，模拟 Protenix 数据管线的五个阶段：

1. **序列解析**：将氨基酸字母串转换为残基类型索引
2. **Tokenization**：为每个残基生成原子级信息（坐标、键连接、原子-token 映射）
3. **Featurization**：将 token 信息编码为模型可消费的特征张量（one-hot、参考坐标等）
4. **MSA 特征生成**：模拟多序列比对，生成进化信息特征
5. **模板特征生成**：模拟结构模板，生成三维参考特征

运行后你将看到每个阶段产出的张量形状，直观理解数据如何从"字母"变成"矩阵"。

---

## 关键代码走读

### Protenix 源码中的对应模块

| 本单元阶段 | Protenix 源文件 | 核心类/函数 |
|-----------|----------------|------------|
| 序列解析 + Tokenization | `protenix/data/tokenizer.py` | `AtomArrayTokenizer` — 将原始分子数据转为 `TokenArray` |
| Featurization | `protenix/data/core/featurizer.py` | `Featurizer` — 将 `TokenArray` 转为特征字典 |
| MSA 特征 | `protenix/data/msa/` | MSA 搜索与特征提取管线 |
| 模板特征 | `protenix/data/template/` | 模板搜索与结构特征提取 |

### 核心数据流

```
原始序列 "FVNQHLCGSHLVEALY"
    │
    ▼  parse_sequence()
残基索引 [5, 18, 12, 13, 7, 10, 1, 6, 16, 7, 10, 18, 4, 0, 10, 19]
    │
    ▼  tokenize()
TokenArray:
  - atom_to_token_idx: [0,0,0, 1,1,1, 2,2,2, ...]  (每3个原子属于1个token)
  - ref_pos: [[0,0,0], [1.5,0,0], [2.4,1.2,0], ...]  (理想化主链坐标)
    │
    ▼  featurize()
特征字典:
  - restype:           [16, 32]   残基类型 one-hot
  - ref_pos:           [48, 3]    参考原子坐标
  - ref_element:       [48, 128]  原子元素 one-hot
  - atom_to_token_idx: [48]       原子→token 映射
  - token_bonds:       [16, 16]   token 间共价键
    │
    ▼  generate_msa_features() + generate_template_features()
追加特征:
  - msa:                        [16, 16]      多序列比对
  - template_distogram:         [4, 16, 16, 39]  模板距离直方图
  - ...
    │
    ▼
模型输入 → InputFeatureEmbedder (Unit 3)
```

### 关键设计思想

1. **两级粒度**：Protenix 同时维护 token 级（残基）和 atom 级（原子）两套表示。`atom_to_token_idx` 是连接两者的桥梁。
2. **固定维度编码**：`restype` 用 32 维而非 20 维，预留了非标准氨基酸和 padding 的空间，保证了灵活性。
3. **参考构型**：`ref_pos` 提供理想化的原子坐标，作为模型预测真实坐标的起点。

---

## 运行方式

```bash
# 确保在项目根目录
cd /root/key_projects/learn-codebase/speedrun-Protenix/unit-2-data-pipeline

# 运行脚本（仅依赖 PyTorch）
python main.py
```

依赖：仅需 `torch`（已在 `requirements.txt` 中列出）。

---

## 预期输出

```
🧬 Protenix 数据管线 — 从序列到特征
   输入序列: FVNQHLCGSHLVEALY
   序列长度: 16 个氨基酸

============================================================
阶段 1: 序列解析
============================================================
  残基索引: [5, 18, 12, 13, 7, 10, 1, 6, 16, 7, 10, 18, 4, 0, 10, 19]

============================================================
阶段 2: Tokenization (序列 → Token)
============================================================
  Token数量: 16
  原子数量: 48
  atom_to_token_idx: torch.Size([48])
  ref_pos: torch.Size([48, 3])

============================================================
阶段 3: Featurization (Token → 特征张量)
============================================================
  restype_onehot: torch.Size([16, 32])
  ref_element: torch.Size([48, 128])
  token_bonds: torch.Size([16, 16])

============================================================
阶段 4: MSA 特征生成
============================================================
  MSA矩阵: torch.Size([16, 16]) (序列数×token数)
  查询序列(前10): [5, 18, 12, 13, 7, 10, 1, 6, 16, 7]
  同源序列1(前10): [5, 18, 12, ...]  (部分位置发生突变)
  序列保守性(前10): [...]  (1.0=完全保守, 0.0=完全不保守)

============================================================
阶段 5: 模板特征生成
============================================================
  模板数量: 4
  template_distogram: torch.Size([4, 16, 16, 39])
  template_unit_vector: torch.Size([4, 16, 16, 3])

============================================================
特征字典总结
============================================================
  restype                        torch.Size([16, 32])  dtype=torch.float32
  ref_pos                        torch.Size([48, 3])   dtype=torch.float32
  ref_element                    torch.Size([48, 128])  dtype=torch.float32
  atom_to_token_idx              torch.Size([48])       dtype=torch.int64
  token_bonds                    torch.Size([16, 16])   dtype=torch.float32
  msa                            torch.Size([16, 16])   dtype=torch.int64
  has_deletion                   torch.Size([16, 16])   dtype=torch.float32
  deletion_value                 torch.Size([16, 16])   dtype=torch.float32
  template_pseudo_beta_mask      torch.Size([4, 16])    dtype=torch.float32
  template_backbone_frame_mask   torch.Size([4, 16])    dtype=torch.float32
  template_distogram             torch.Size([4, 16, 16, 39]) dtype=torch.float32
  template_unit_vector           torch.Size([4, 16, 16, 3])  dtype=torch.float32

  ✓ 数据管线完成！这些特征将传入 InputFeatureEmbedder (→ Unit 3)
```

（注：MSA 中的同源序列含随机突变，每次运行的具体数值可能略有不同，但形状一致。）

---

## 练习

### 练习 1：添加新氨基酸类型
修改 `AMINO_ACIDS` 常量，添加一种非标准氨基酸（如硒代半胱氨酸 `U`），观察：
- `restype_onehot` 的维度是否需要变化？
- 当前 32 维的设计如何容纳新类型？

### 练习 2：追踪 N_tokens 与 N_atoms 的关系
修改输入序列长度（试试 50、100、200 个残基），记录：
- `N_tokens` 和 `N_atoms` 的比值是否恒定？
- 在真实 Protenix 中，不同残基的原子数不同，这个比值会怎样变化？

### 练习 3：费曼练习
用自己的话回答以下问题（建议写在注释或笔记中）：

> **为什么需要 `atom_to_token_idx` 映射？直接用 token 级别的特征不行吗？**

提示：想想以下场景——
- 模型最终需要预测每个原子的三维坐标，而不仅仅是每个残基的位置
- 不同残基拥有不同数量的原子（甘氨酸只有 4 个重原子，色氨酸有 14 个）
- 模型内部在 token 级别做注意力计算（效率高），但输出时需要映射回原子级别（精度高）
- `atom_to_token_idx` 就是这座桥梁：它让模型能在两个粒度之间自由切换

---

## 调试指南

### 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `ModuleNotFoundError: No module named 'torch'` | 未安装 PyTorch | `pip install torch` |
| 张量形状不匹配 | 修改序列后未同步更新相关变量 | 检查 `N_tokens` 和 `N_atoms` 是否一致 |
| MSA 结果每次不同 | 同源序列中的突变是随机生成的 | 这是正常行为；设置 `torch.manual_seed(42)` 可复现 |

### 调试技巧

1. **打印张量形状**：在任何不确定的地方加 `print(tensor.shape)`，形状是理解数据流的最佳线索。
2. **检查 one-hot 编码**：`restype_onehot.sum(dim=-1)` 应该全为 1.0（每行恰好一个 1）。
3. **验证映射关系**：`atom_to_token_idx` 的最大值应等于 `N_tokens - 1`，最小值应为 0。
4. **可视化 token_bonds**：这是一个三对角矩阵（主对角线上下各一条），可以用 `print(token_bonds[:5, :5])` 快速检查。

---

## 下一步

完成本单元后，你已经理解了模型的"食物"是什么样子。下一步进入 **Unit 3: 输入嵌入**，看看模型如何把这些特征张量"消化"成内部表示。
