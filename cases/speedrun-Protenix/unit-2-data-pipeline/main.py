"""
Unit 2: 数据管线 — 从序列到特征

演示蛋白质序列如何经过 Tokenization → Featurization → MSA/Template 处理变成模型输入张量。

对应 Protenix 源码：
  - protenix/data/tokenizer.py          (AtomArrayTokenizer)
  - protenix/data/core/featurizer.py    (Featurizer)
  - protenix/data/msa/                  (MSA 搜索与特征提取)
  - protenix/data/template/             (模板搜索与结构特征提取)

运行方式：
  python main.py
"""

import torch
import torch.nn.functional as F

# === 常量 ===
AMINO_ACIDS = "ACDEFGHIKLMNPQRSTVWY"  # 20种标准氨基酸（单字母代码）
NUM_RESTYPES = 32  # 残基类型总维度，包含20种标准 + 非标准类型 + padding
BACKBONE_ATOMS = ["N", "CA", "C"]  # 主链原子：氮、α碳、羰基碳
MAX_ATOMS_PER_RESIDUE = 14  # 单个残基最多的重原子数（色氨酸 Trp）


# ============================================================
# 阶段 1: 序列解析
# ============================================================
def parse_sequence(sequence: str) -> torch.Tensor:
    """
    将氨基酸字母序列转换为残基类型索引。

    类比：把英文单词拆成字母，再查字母表得到编号。
    例如 'A' → 0, 'C' → 1, ..., 'Y' → 19, 未知 → 20

    参数:
        sequence: 氨基酸单字母序列，如 "FVNQHLCGSHLVEALY"

    返回:
        restype_indices: 形状 [N_token] 的整数张量，每个元素是氨基酸索引
    """
    # LEARN: 每个氨基酸字母对应一个索引(0-19)，未知类型用20表示
    # 在真实 Protenix 中，tokenizer.py 的 AtomArrayTokenizer 完成类似工作，
    # 但它还处理核酸、配体等非蛋白质分子
    restype_indices = []
    for aa in sequence:
        if aa in AMINO_ACIDS:
            restype_indices.append(AMINO_ACIDS.index(aa))
        else:
            restype_indices.append(20)  # 未知类型（如非标准氨基酸）
    return torch.tensor(restype_indices)


# ============================================================
# 阶段 2: Tokenization（序列 → Token）
# ============================================================
def tokenize(restype_indices: torch.Tensor):
    """
    模拟 AtomArrayTokenizer：为每个残基生成原子级信息。

    核心思想：蛋白质有两个粒度——
      - Token 级（残基级）：用于高效的注意力计算
      - Atom 级（原子级）：用于精确的坐标预测
    Tokenization 的任务就是建立这两个粒度之间的映射关系。

    参数:
        restype_indices: 形状 [N_token] 的残基类型索引

    返回:
        N_atoms: 总原子数
        atom_to_token_idx: 形状 [N_atom] 的映射张量
        ref_pos: 形状 [N_atom, 3] 的参考坐标张量
    """
    N_tokens = len(restype_indices)

    # LEARN: 每个残基至少有3个主链原子(N, CA, C)，加上不同数量的侧链原子
    # 简化处理：每个残基统一分配3个主链原子
    # 真实情况中，甘氨酸(G)只有4个重原子，色氨酸(W)有14个
    atoms_per_token = 3  # 仅主链: N, CA, C
    N_atoms = N_tokens * atoms_per_token

    # LEARN: atom_to_token_idx 是连接原子级和token级的桥梁
    # 它告诉模型"第 i 个原子属于第 j 个 token（残基）"
    # 例如: [0,0,0, 1,1,1, 2,2,2, ...] 表示前3个原子属于token 0，接下来3个属于token 1...
    atom_to_token_idx = torch.arange(N_tokens).repeat_interleave(atoms_per_token)

    # LEARN: 参考坐标（ref_pos）是理想化的主链几何构型
    # 真实蛋白质中，相邻残基的 CA 原子间距约 3.8 Å
    # 这些参考坐标为模型提供一个"起点"，模型在此基础上预测真实坐标
    ref_pos = torch.zeros(N_atoms, 3)
    for i in range(N_tokens):
        base = i * atoms_per_token
        ref_pos[base] = torch.tensor([i * 3.8, 0.0, 0.0])          # N 原子
        ref_pos[base + 1] = torch.tensor([i * 3.8 + 1.5, 0.0, 0.0])  # CA 原子
        ref_pos[base + 2] = torch.tensor([i * 3.8 + 2.4, 1.2, 0.0])  # C 原子

    print(f"  Token数量: {N_tokens}")
    print(f"  原子数量: {N_atoms}")
    print(f"  每个token的原子数: {atoms_per_token} (仅主链)")
    print(f"  atom_to_token_idx: {atom_to_token_idx.shape}")
    print(f"  ref_pos: {ref_pos.shape}")
    print(f"  atom_to_token_idx 前9个: {atom_to_token_idx[:9].tolist()}")
    print(f"    → 含义: 前3个原子属于token 0, 接下来3个属于token 1, ...")

    return N_atoms, atom_to_token_idx, ref_pos


# ============================================================
# 阶段 3: Featurization（Token → 特征张量）
# ============================================================
def featurize(
    restype_indices: torch.Tensor,
    N_atoms: int,
    atom_to_token_idx: torch.Tensor,
    ref_pos: torch.Tensor,
) -> dict:
    """
    模拟 Featurizer：生成模型需要的所有特征张量。

    这是数据管线的核心环节。Featurizer 将结构化的 TokenArray
    转换为纯数值张量，供神经网络直接消费。

    对应源码: protenix/data/core/featurizer.py

    参数:
        restype_indices: 形状 [N_token] 的残基类型索引
        N_atoms: 总原子数
        atom_to_token_idx: 形状 [N_atom] 的原子→token映射
        ref_pos: 形状 [N_atom, 3] 的参考坐标

    返回:
        feature_dict: 包含所有特征张量的字典
    """
    N_tokens = len(restype_indices)

    # ---- 特征 1: restype one-hot ----
    # LEARN: 将残基类型编码为32维 one-hot 向量
    # 为什么是32维而不是20维？因为需要预留空间给：
    #   - 20种标准氨基酸 (索引 0-19)
    #   - 未知类型 (索引 20)
    #   - 非标准氨基酸如硒代半胱氨酸 (索引 21+)
    #   - padding (最后几个索引)
    # 这种设计让系统无需修改维度即可扩展
    restype_onehot = F.one_hot(restype_indices.long(), NUM_RESTYPES).float()
    print(f"  restype_onehot: {restype_onehot.shape}")
    print(f"    → 每行是一个32维向量，恰好有一个1 (验证: sum={restype_onehot.sum(dim=-1)[0].item()})")

    # ---- 特征 2: ref_element ----
    # LEARN: 原子元素类型的 one-hot 编码
    # 128维是为了覆盖元素周期表中的所有元素
    # 蛋白质中常见的元素: C(碳)=6, N(氮)=7, O(氧)=8, S(硫)=16
    ref_element = torch.zeros(N_atoms, 128)
    for i in range(N_atoms):
        atom_type = i % 3  # 0=N(氮), 1=CA(碳), 2=C(碳)
        element_idx = [7, 6, 6][atom_type]  # 氮的原子序数=7, 碳=6
        ref_element[i, element_idx] = 1.0
    print(f"  ref_element: {ref_element.shape}")

    # ---- 特征 3: token_bonds ----
    # LEARN: token 之间的共价键连接矩阵
    # 蛋白质主链是线性的：残基0-残基1-残基2-...
    # 所以 token_bonds 是一个三对角矩阵（相邻残基之间有键）
    # 在真实 Protenix 中，还会处理二硫键等非相邻连接
    token_bonds = torch.zeros(N_tokens, N_tokens)
    for i in range(N_tokens - 1):
        token_bonds[i, i + 1] = 1.0  # 正向: 残基i → 残基i+1
        token_bonds[i + 1, i] = 1.0  # 反向: 残基i+1 → 残基i（对称矩阵）
    print(f"  token_bonds: {token_bonds.shape}")
    print(f"    → 三对角结构 (前4×4):")
    for row in range(min(4, N_tokens)):
        print(f"      {token_bonds[row, :min(4, N_tokens)].tolist()}")

    # ---- 组装特征字典 ----
    # LEARN: 这个字典就是模型的"食物"——所有信息都以张量形式打包
    # 在 Unit 3 中，InputFeatureEmbedder 会把这些张量嵌入到统一的向量空间
    feature_dict = {
        "restype": restype_onehot,               # [N_token, 32]  残基类型
        "ref_pos": ref_pos,                       # [N_atom, 3]    参考坐标
        "ref_element": ref_element,               # [N_atom, 128]  原子元素类型
        "atom_to_token_idx": atom_to_token_idx,   # [N_atom]       原子→token映射
        "token_bonds": token_bonds,               # [N_token, N_token] 共价键
    }

    return feature_dict


# ============================================================
# 阶段 4: MSA 特征生成
# ============================================================
def generate_msa_features(
    sequence: str, N_tokens: int, N_msa: int = 16
) -> dict:
    """
    模拟 MSAFeaturizer：生成多序列比对特征。

    MSA 的生物学意义：
      通过搜索序列数据库（如 UniRef、BFD），找到与查询序列进化相关的同源序列。
      如果某个位置在所有同源序列中都保持不变（高保守性），说明该位置对蛋白质的
      结构或功能至关重要——突变会被自然选择淘汰。

    对应源码: protenix/data/msa/

    参数:
        sequence: 查询蛋白质序列
        N_tokens: token 数量
        N_msa: MSA 中的序列数量（包括查询序列本身）

    返回:
        包含 MSA 相关特征的字典
    """
    # LEARN: MSA 矩阵的第一行是查询序列本身，后面是同源序列
    msa = torch.zeros(N_msa, N_tokens, dtype=torch.long)
    msa[0] = torch.tensor(
        [AMINO_ACIDS.index(aa) if aa in AMINO_ACIDS else 20 for aa in sequence]
    )

    # 模拟同源序列：大部分位置与查询序列相同，少数位置发生突变
    # 真实场景中，这些序列来自数据库搜索（如 JackHMMER、HHblits）
    for i in range(1, N_msa):
        msa[i] = msa[0].clone()
        # 约 20% 的位置发生随机突变
        n_mutations = max(1, N_tokens // 5)
        mut_positions = torch.randperm(N_tokens)[:n_mutations]
        msa[i, mut_positions] = torch.randint(0, 20, (n_mutations,))

    # LEARN: has_deletion 和 deletion_value 记录比对中的插入/缺失(indel)信息
    # 缺失意味着某些同源序列在该位置没有对应的残基
    has_deletion = torch.zeros(N_msa, N_tokens)
    deletion_value = torch.zeros(N_msa, N_tokens)

    print(f"  MSA矩阵: {msa.shape} (序列数×token数)")
    print(f"  查询序列(前10): {msa[0, :10].tolist()}")
    print(f"  同源序列1(前10): {msa[1, :10].tolist()}")

    # LEARN: 序列保守性 — 衡量每个位置在进化中的稳定程度
    # 保守性 = 该位置与查询序列相同的比例
    # 保守性高的位置往往是结构核心或功能关键位点
    conservation = (msa == msa[0:1]).float().mean(dim=0)
    print(f"  序列保守性(前10): {[round(x, 2) for x in conservation[:10].tolist()]}")
    print(f"    → 1.0=完全保守(所有序列都相同), 接近0=高度可变")

    return {
        "msa": msa,                    # [N_msa, N_token]
        "has_deletion": has_deletion,   # [N_msa, N_token]
        "deletion_value": deletion_value,  # [N_msa, N_token]
    }


# ============================================================
# 阶段 5: 模板特征生成
# ============================================================
def generate_template_features(N_tokens: int, N_templates: int = 4) -> dict:
    """
    模拟 TemplateFeaturizer：生成结构模板特征。

    模板的作用：
      如果数据库中已有一个结构相似的蛋白质（同源蛋白），它的已知三维结构
      可以作为"参考答案"。模型可以借鉴模板的骨架构型来预测新蛋白的结构。
      这就像考试时有一份"参考答案"——不完全一样，但能提供重要线索。

    对应源码: protenix/data/template/

    参数:
        N_tokens: token 数量
        N_templates: 模板数量

    返回:
        包含模板相关特征的字典
    """
    # LEARN: pseudo_beta 是残基的代表性原子位置
    # 对于非甘氨酸残基用 CB（β碳），甘氨酸用 CA（α碳）
    # mask 表示该位置是否有有效的模板信息
    template_pseudo_beta_mask = torch.ones(N_templates, N_tokens)
    template_backbone_frame_mask = torch.ones(N_templates, N_tokens)

    # LEARN: distogram 是残基对之间的距离直方图
    # 39 个 bin 覆盖 2Å 到 22Å 的距离范围
    # 这比单一距离值更有信息量，因为它表达了距离的不确定性
    template_distogram = torch.randn(N_templates, N_tokens, N_tokens, 39)

    # LEARN: unit_vector 是残基对之间的方向向量
    # 提供了空间中的相对朝向信息
    template_unit_vector = torch.randn(N_templates, N_tokens, N_tokens, 3)
    # 归一化为单位向量
    template_unit_vector = F.normalize(template_unit_vector, dim=-1)

    print(f"  模板数量: {N_templates}")
    print(f"  template_pseudo_beta_mask: {template_pseudo_beta_mask.shape}")
    print(f"  template_backbone_frame_mask: {template_backbone_frame_mask.shape}")
    print(f"  template_distogram: {template_distogram.shape}")
    print(f"    → 39个bin覆盖2-22\u00c5的距离范围")
    print(f"  template_unit_vector: {template_unit_vector.shape}")
    print(f"    → 归一化后的方向向量 (模长验证: {template_unit_vector[0,0,0].norm().item():.4f})")

    return {
        "template_pseudo_beta_mask": template_pseudo_beta_mask,       # [N_tmpl, N_token]
        "template_backbone_frame_mask": template_backbone_frame_mask, # [N_tmpl, N_token]
        "template_distogram": template_distogram,                     # [N_tmpl, N_token, N_token, 39]
        "template_unit_vector": template_unit_vector,                 # [N_tmpl, N_token, N_token, 3]
    }


# ============================================================
# 主流程
# ============================================================
def main():
    """
    完整的数据管线演示。

    输入: 一条蛋白质序列（字母串）
    输出: 一个特征字典（张量集合），可直接传入模型

    数据流:
      序列字符串 → 残基索引 → TokenArray → 特征张量 → 模型输入
    """
    # 示例蛋白质序列（胰岛素B链的部分序列）
    sequence = "FVNQHLCGSHLVEALY"

    print("=" * 60)
    print("  Protenix 数据管线 — 从序列到特征")
    print("=" * 60)
    print(f"  输入序列: {sequence}")
    print(f"  序列长度: {len(sequence)} 个氨基酸")
    print()

    # ----------------------------------------------------------
    # 阶段 1: 序列解析
    # ----------------------------------------------------------
    print("=" * 60)
    print("阶段 1: 序列解析")
    print("=" * 60)
    restype_indices = parse_sequence(sequence)
    print(f"  残基索引: {restype_indices.tolist()}")
    print(f"  验证: '{sequence[0]}' → 索引 {restype_indices[0].item()}"
          f" (在AMINO_ACIDS中的位置: {AMINO_ACIDS.index(sequence[0])})")

    # ----------------------------------------------------------
    # 阶段 2: Tokenization
    # ----------------------------------------------------------
    print(f"\n{'=' * 60}")
    print("阶段 2: Tokenization (序列 → Token)")
    print("=" * 60)
    N_atoms, atom_to_token_idx, ref_pos = tokenize(restype_indices)

    # ----------------------------------------------------------
    # 阶段 3: Featurization
    # ----------------------------------------------------------
    print(f"\n{'=' * 60}")
    print("阶段 3: Featurization (Token → 特征张量)")
    print("=" * 60)
    features = featurize(restype_indices, N_atoms, atom_to_token_idx, ref_pos)

    # ----------------------------------------------------------
    # 阶段 4: MSA 特征
    # ----------------------------------------------------------
    print(f"\n{'=' * 60}")
    print("阶段 4: MSA 特征生成")
    print("=" * 60)
    msa_features = generate_msa_features(sequence, len(sequence))
    features.update(msa_features)

    # ----------------------------------------------------------
    # 阶段 5: 模板特征
    # ----------------------------------------------------------
    print(f"\n{'=' * 60}")
    print("阶段 5: 模板特征生成")
    print("=" * 60)
    template_features = generate_template_features(len(sequence))
    features.update(template_features)

    # ----------------------------------------------------------
    # 总结: 打印完整的特征字典
    # ----------------------------------------------------------
    print(f"\n{'=' * 60}")
    print("特征字典总结")
    print("=" * 60)
    for key, value in features.items():
        if isinstance(value, torch.Tensor):
            print(f"  {key:35s} {str(value.shape):25s} dtype={value.dtype}")

    print(f"\n  数据管线完成！")
    print(f"  这些特征将传入 InputFeatureEmbedder (→ Unit 3)")
    print(f"  总共 {len(features)} 个特征张量，覆盖了残基类型、原子坐标、")
    print(f"  进化信息(MSA)和结构模板四大类信息。")


if __name__ == "__main__":
    # 固定随机种子以保证可复现性
    torch.manual_seed(42)
    main()
