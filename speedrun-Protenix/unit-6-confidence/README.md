# Unit 6: 置信度与输出 — 预测质量评估

## 通俗理解

想象一个工厂的质检流程：

- **工厂（模型）** 生产了多件产品（候选结构，N_sample=5）
- **质检员（ConfidenceHead）** 对每件产品进行全面检查
- 质检员不只看整体，还会**逐个零件（原子）检查**，给出 pLDDT 分数
- 还会评估**零件之间的配合精度**，给出 PAE 分数
- 最后综合打分（Ranking Score），**选出最好的一件出厂**

关键洞察：模型知道自己哪里预测得好、哪里预测得差。柔性 loop 区域通常 pLDDT 较低，而稳定的二级结构（alpha螺旋、beta折叠）通常 pLDDT 较高。这个"自知之明"对下游使用者非常重要。

## 背景知识

### LDDT (Local Distance Difference Test)
结构生物学中评估预测质量的标准指标。核心思想：对于每个原子，看它与周围原子（15Å内）的距离在预测结构和真实结构中是否一致。如果大部分距离差异小于阈值（0.5/1/2/4Å），则该原子的 LDDT 分数高。

### TM-score
衡量两个蛋白质结构整体相似度的指标，范围 0-1：
- \>0.5：正确的折叠拓扑
- \>0.7：高质量预测
- 与 RMSD 不同，TM-score 对蛋白质长度不敏感

### 为什么需要置信度？
- 不是所有区域都能被准确预测（如柔性 loop、无序区域）
- 用户需要知道哪些区域可信、哪些不可信
- 多样本采样 + 排序策略：生成多个候选，用置信度选最优

### 多样本策略
Protenix 默认生成 5 个候选结构（N_sample=5），每个使用不同的扩散噪声。然后用 ConfidenceHead 对每个候选评分，选出 Ranking Score 最高的作为最终输出。

## 关键术语

| 术语 | 含义 | 维度/范围 |
|------|------|-----------|
| **pLDDT** | 每个原子的局部距离差异测试分数 | [N_atoms], 0-100, 50个bin |
| **PAE** | 预测对齐误差（Predicted Aligned Error） | [N_token, N_token], 0-32Å, 64个bin |
| **PDE** | 预测距离误差（Predicted Distance Error） | [N_token, N_token], 64个bin |
| **PTM** | 预测TM分数，全局结构质量 | 标量, 0-1 |
| **iPTM** | 界面PTM，只看不同链之间的残基对 | 标量, 0-1 |
| **Ranking Score** | 0.8 * iPTM + 0.2 * PTM | 标量, 0-1 |
| **ConfidenceHead** | 包含小型PairformerStack + 多个预测头 | Algorithm 31 |
| **Resolved Head** | 预测每个原子是否被"解析"（有可靠坐标） | [N_atoms], 二分类 |

### pLDDT 分数解读

| 范围 | 含义 | 典型区域 |
|------|------|----------|
| >90 | 非常高置信度 | 稳定的核心区域、二级结构 |
| 70-90 | 高置信度 | 大部分结构化区域 |
| 50-70 | 低置信度 | 柔性loop、表面残基 |
| <50 | 非常低置信度 | 无序区域、末端 |

## 本单元做什么

1. **实现距离特征计算**：从预测坐标提取 token 间距离，作为置信度预测的输入
2. **实现 pLDDT Head**：预测每个原子的局部置信度分数
3. **实现 PAE Head**：预测任意两个 token 之间的对齐误差
4. **实现 PTM/iPTM 计算**：从 PAE 推导全局和界面质量分数
5. **组装 ConfidenceHead**：整合所有组件，完成 Algorithm 31
6. **多样本排序**：生成 5 个候选结构，用 Ranking Score 选出最佳

## 关键代码走读

### 真实源码位置
- `protenix/model/modules/confidence.py` — ConfidenceHead 主模块
- `protenix/model/sample_confidence.py` — 多样本置信度评估与排序
- `protenix/model/modules/head.py` — pLDDT/PAE/PDE 等预测头

### 核心流程（Algorithm 31）

```
输入: s (single repr), z (pair repr), 预测坐标 x
  ↓
1. 从 x 计算 token 间距离 → 距离特征
  ↓
2. 距离特征注入 z → z_conf
  ↓
3. 小型 PairformerStack 处理 (s, z_conf) → (s_conf, z_conf)
  ↓
4. pLDDT Head(s_conf) → 每原子置信度
   PAE Head(z_conf) → 每对 token 对齐误差
   PDE Head(z_conf) → 每对 token 距离误差
  ↓
5. PTM = f(PAE), iPTM = f(PAE, interface_mask)
  ↓
6. Ranking = 0.8 * iPTM + 0.2 * PTM
```

### 关键设计决策

**为什么用预测坐标作为输入？**
ConfidenceHead 接收的是模型自己预测的坐标，而不是真实坐标。它需要学会判断"这些预测坐标看起来合不合理"。这是一种自我评估能力。

**为什么 PAE 是非对称的？**
PAE[i][j] 表示"以 token i 为参考对齐后，token j 的位置误差"。以不同 token 为参考，误差可能不同，所以 PAE 矩阵不一定对称。

**为什么需要 iPTM？**
对于蛋白质复合物，两条链可能各自折叠正确（PTM 高），但对接位置完全错误。iPTM 只看跨链的残基对，能捕捉这种情况。

## 运行方式

```bash
cd /root/key_projects/learn-codebase/speedrun-Protenix/unit-6-confidence
python main.py
```

## 预期输出

程序会输出：
1. 每个候选结构的置信度指标（pLDDT、PAE、PTM、iPTM、Ranking）
2. 按 Ranking Score 排序的候选列表，标记最佳候选
3. 最佳候选的 pLDDT 分布直方图

示例输出格式：
```
置信度评估
--- Sample 1/5 ---
  pLDDT:   mean=XX.X, min=XX.X, max=XX.X
  PAE:     mean=XX.XÅ
  PTM:     0.XXX
  iPTM:    0.XXX
  Ranking: 0.XXX

候选排序结果
  排名  Sample   pLDDT   PAE(Å)    PTM   iPTM  Ranking
    1       3    XX.X     XX.X   0.XXX  0.XXX    0.XXX ← 最佳
    ...

pLDDT 分布 (最佳候选)
  很高 ( 90-100):  XX 原子 ( XX.X%) ████
  ...
```

注意：由于使用随机初始化的权重，具体数值每次运行会不同，但流程和格式一致。

## 练习

1. **修改 Ranking 权重**：将 `0.8 * iPTM + 0.2 * PTM` 改为 `0.5 * iPTM + 0.5 * PTM`，观察排序是否变化。思考：什么场景下应该更重视 PTM？

2. **修改 pLDDT bin 数**：将 `PLDDT_BINS` 从 50 改为 10，观察分数分布的变化。思考：bin 数越多精度越高，但计算量也越大，如何权衡？

3. **【费曼练习】** 解释：为什么 iPTM 在蛋白质复合物预测中比 PTM 更重要？
   - 提示：想想两条链各自折叠正确但对接位置错误的情况
   - PTM 会给出较高分数（因为每条链内部结构正确）
   - 但 iPTM 会给出低分数（因为跨链的相对位置不对）
   - 这就是为什么 Ranking Score 中 iPTM 权重（0.8）远大于 PTM（0.2）

4. **思考题**：如果一个蛋白质没有复合物（只有单链），iPTM 应该如何处理？查看 `interface_mask` 的实现。

## 调试指南

### 常见问题

**Q: pLDDT 分数全部集中在某个范围？**
A: 随机初始化的网络输出接近均匀分布，训练后才会出现有意义的分布。真实模型中，核心区域 pLDDT > 90，loop 区域 50-70。

**Q: PTM 和 iPTM 值很接近？**
A: 在随机数据上这是正常的。真实数据中，如果对接预测不准，iPTM 会明显低于 PTM。

**Q: Ranking Score 区分度不大？**
A: 随机权重下各候选差异不大。真实模型中，不同扩散噪声会产生质量差异明显的候选。

### 与真实代码的差异

| 方面 | 本教程 | 真实 Protenix |
|------|--------|---------------|
| PairformerStack | 简化为单层MLP | 4层完整Pairformer |
| PDE Head | 未实现 | 完整实现 |
| Resolved Head | 未实现 | 预测原子是否被解析 |
| 坐标处理 | 直接取CA原子 | 完整的原子级处理 |
| bin 边界 | 均匀分布 | 可能有非均匀分布 |

## 单元依赖

- **Unit 4（Evoformer）**：提供 single representation (s) 和 pair representation (z)
- **Unit 5（扩散模块）**：提供预测坐标和多个候选结构
- **本单元输出**：最终的置信度分数和最佳候选结构，即模型的最终输出
