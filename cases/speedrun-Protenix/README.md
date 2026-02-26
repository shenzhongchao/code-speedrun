# Speedrun Protenix — 蛋白质结构预测系统学习路径

> **源项目**: [Protenix](https://github.com/bytedance/Protenix) — 基于扩散模型的蛋白质结构预测系统（类似 AlphaFold3）

## 架构总览

```
输入 JSON (蛋白质序列/MSA/模板)
        ↓
┌─────────────────────────┐
│  数据管线 (Unit 2)       │  序列 → Token → 特征张量
└────────┬────────────────┘
         ↓
┌─────────────────────────┐
│  输入嵌入 (Unit 3)       │  特征 → token嵌入 s + pair嵌入 z
└────────┬────────────────┘
         ↓
┌─────────────────────────┐
│  Pairformer (Unit 4)     │  三角注意力迭代精炼 s, z
└────────┬────────────────┘
         ↓
┌─────────────────────────┐
│  扩散模块 (Unit 5)       │  噪声 → 去噪 → 三维原子坐标
└────────┬────────────────┘
         ↓
┌─────────────────────────┐
│  置信度与输出 (Unit 6)   │  pLDDT/PAE/PTM 质量评估
└────────┘────────────────┘
         ↓
    输出 CIF 结构文件

训练路径 (Unit 7):
  真实结构 → 加噪 → 单步去噪 → 损失计算 → 梯度更新
  + Mini-Rollout 标签置换 + EMA 参数平滑
```

## 学习路径

| 单元 | 主题 | 核心概念 |
|------|------|----------|
| Unit 1 | 端到端总览 | 用桩函数跑通完整预测流程 |
| Unit 2 | 数据管线 | 序列 → Token → 特征张量 |
| Unit 3 | 输入嵌入 | AtomAttentionEncoder + 相对位置编码 |
| Unit 4 | Pairformer | 三角注意力 + 三角乘法更新 |
| Unit 5 | 扩散模块 | 去噪扩散生成三维坐标 |
| Unit 6 | 置信度与输出 | pLDDT/PAE/PTM 自评打分 |
| Unit 7 | 训练流程 | 损失函数 + 噪声采样 + 标签置换 + EMA |

## 快速开始

```bash
# 安装依赖
cd speedrun-Protenix
pip install -r requirements.txt

# 运行所有单元
python unit-1-overall/main.py
python unit-2-data-pipeline/main.py
python unit-3-input-embedding/main.py
python unit-4-pairformer/main.py
python unit-5-diffusion/main.py
python unit-6-confidence/main.py
python unit-7-training/main.py
```

## 从速通版向原版扩展

速通版对原版做了大量简化。完整的简化清单和推荐扩展路径见 [SIMPLIFICATIONS.md](SIMPLIFICATIONS.md)。

你可以借助 AI 编程工具，在速通版基础上逐项补充原版实现，逐步理解工程决策。

## 前置知识

- Python + PyTorch 基础
- Transformer 注意力机制基本概念
- 了解蛋白质由氨基酸序列折叠成三维结构（不需要生物学背景）
