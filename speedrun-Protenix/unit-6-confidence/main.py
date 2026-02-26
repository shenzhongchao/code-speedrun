"""
Unit 6: 置信度与输出 — 预测质量评估
演示 ConfidenceHead 如何评估预测结构的质量并选出最佳候选。

核心思想：
  模型生成多个候选结构后，需要一个"质检员"来评估每个候选的质量。
  ConfidenceHead 就是这个质检员，它输出多种置信度指标：
  - pLDDT: 每个原子的局部置信度
  - PAE: 每对token之间的对齐误差
  - PTM/iPTM: 全局/界面结构质量
  - Ranking Score: 最终排序分数

真实源码参考：
  - protenix/model/modules/confidence.py
  - protenix/model/sample_confidence.py
  - protenix/model/modules/head.py
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import math

# === 配置 ===
N_tokens = 16            # token数量（残基数）
atoms_per_token = 3      # 每个token的原子数（简化：N, CA, C）
N_atoms = N_tokens * atoms_per_token  # 总原子数
c_s = 384                # single representation 维度
c_z = 128                # pair representation 维度
N_sample = 5             # 候选结构数量
PLDDT_BINS = 50          # pLDDT 分bin数
PAE_BINS = 64            # PAE 分bin数
PDE_BINS = 64            # PDE 分bin数
PAE_MAX = 32.0           # PAE最大值(Å)


# === 组件 1: 距离特征计算 ===
def compute_distance_features(coords, atom_to_token_idx, N_tokens):
    """
    从预测坐标计算token间距离特征。
    类比：测量产品各零件之间的实际距离，作为质检的输入。

    参数:
        coords: [N_atoms, 3] 预测的原子坐标
        atom_to_token_idx: [N_atoms] 每个原子属于哪个token
        N_tokens: token总数

    返回:
        distances: [N_tokens, N_tokens] token间距离矩阵
        ca_coords: [N_tokens, 3] CA原子坐标
    """
    # LEARN: 取每个token的代表原子(CA原子，即每个残基的第二个原子)
    # 在真实蛋白质中，CA(alpha碳)是残基的中心原子，常用作代表
    ca_indices = torch.arange(N_tokens) * atoms_per_token + 1
    ca_coords = coords[ca_indices]  # [N_tokens, 3]

    # LEARN: 计算所有token对之间的距离
    # 这是置信度预测的关键输入——模型需要知道预测的距离是多少，
    # 才能判断这些距离是否合理
    diff = ca_coords.unsqueeze(0) - ca_coords.unsqueeze(1)  # [N, N, 3]
    distances = diff.norm(dim=-1)  # [N, N]

    return distances, ca_coords


# === 组件 2: pLDDT Head ===
class PLDDTHead(nn.Module):
    """
    预测每个原子的局部距离差异测试分数。

    类比：给每个零件打一个"合格分"——这个零件周围的距离关系是否符合预期。
    分数越高，说明这个原子的位置越可靠。

    pLDDT 分数解读：
      >90  = 非常高置信度（稳定核心区域）
      70-90 = 高置信度（大部分结构化区域）
      50-70 = 低置信度（柔性loop）
      <50  = 非常低置信度（无序区域）
    """
    def __init__(self, c_s, n_bins=PLDDT_BINS):
        super().__init__()
        self.n_bins = n_bins
        # LEARN: 简单的两层MLP，从原子特征预测bin概率
        self.net = nn.Sequential(
            nn.LayerNorm(c_s),
            nn.Linear(c_s, c_s),
            nn.ReLU(),
            nn.Linear(c_s, n_bins),
        )

    def forward(self, s_atom):
        """
        参数:
            s_atom: [N_atoms, c_s] — 每个原子的特征

        返回:
            logits: [N_atoms, n_bins] — 每个bin的原始分数
            score: [N_atoms] — 0-100的置信度分数
        """
        logits = self.net(s_atom)  # [N_atoms, n_bins]

        # LEARN: 将logits转换为0-100的分数
        # 每个bin代表一个置信度区间，取期望值作为最终分数
        # 例如50个bin: bin_0=0-2分, bin_1=2-4分, ..., bin_49=98-100分
        probs = F.softmax(logits, dim=-1)
        bin_centers = torch.arange(self.n_bins).float() / self.n_bins * 100
        score = (probs * bin_centers).sum(dim=-1)  # [N_atoms]

        return logits, score


# === 组件 3: PAE Head ===
class PAEHead(nn.Module):
    """
    预测任意两个token之间的对齐误差（Predicted Aligned Error）。

    类比：评估任意两个零件之间的"配合精度"——
    即使每个零件单独看都合格(pLDDT高)，它们之间的相对位置也可能不准。

    PAE[i][j] 的含义：
      以token i为参考进行对齐后，token j的位置误差是多少Å。
      注意：PAE矩阵不一定对称，因为参考点不同。
    """
    def __init__(self, c_z, n_bins=PAE_BINS, max_error=PAE_MAX):
        super().__init__()
        self.n_bins = n_bins
        self.max_error = max_error
        self.net = nn.Sequential(
            nn.LayerNorm(c_z),
            nn.Linear(c_z, c_z),
            nn.ReLU(),
            nn.Linear(c_z, n_bins),
        )

    def forward(self, z):
        """
        参数:
            z: [N_token, N_token, c_z] — pair representation

        返回:
            logits: [N_token, N_token, n_bins] — 每个bin的原始分数
            error: [N_token, N_token] — 预测误差(Å)
        """
        logits = self.net(z)  # [N_token, N_token, n_bins]

        # LEARN: 将logits转换为预测误差(Å)
        # 64个bin均匀覆盖0-32Å范围
        probs = F.softmax(logits, dim=-1)
        bin_centers = torch.arange(self.n_bins).float() / self.n_bins * self.max_error
        error = (probs * bin_centers).sum(dim=-1)  # [N_token, N_token]

        return logits, error


# === 组件 4: PTM/iPTM 计算 ===
def compute_ptm(pae_logits, max_error=PAE_MAX, interface_mask=None):
    """
    从PAE logits计算PTM（Predicted TM-score）分数。

    PTM基于TM-score的思想：
      TM-score = (1/N) * Σ 1/(1 + (d_i/d_0)^2)
    其中d_0是长度相关的归一化因子，使得TM-score对蛋白质长度不敏感。

    参数:
        pae_logits: [N, N, n_bins] — PAE的原始logits
        max_error: PAE最大值
        interface_mask: [N, N] — 可选，标记哪些残基对属于不同链（用于iPTM）

    返回:
        score: 标量，PTM或iPTM分数(0-1)
    """
    N = pae_logits.shape[0]
    n_bins = pae_logits.shape[-1]

    # LEARN: d_0 是TM-score的归一化因子，取决于蛋白质长度
    # 这个公式来自Zhang & Skolnick (2004)的TM-score论文
    # 蛋白质越长，d_0越大，对远距离误差更宽容
    d_0 = 1.24 * max(N - 15, 1) ** (1/3) - 1.8
    d_0 = max(d_0, 0.02)  # 防止除零

    # LEARN: 计算每个bin对应的TM-score贡献
    # bin_center越小(误差越小)，TM贡献越大(接近1)
    # bin_center越大(误差越大)，TM贡献越小(接近0)
    bin_centers = torch.arange(n_bins).float() / n_bins * max_error
    tm_per_bin = 1.0 / (1.0 + (bin_centers / d_0) ** 2)  # [n_bins]

    probs = F.softmax(pae_logits, dim=-1)  # [N, N, n_bins]

    # LEARN: 对每个残基对计算期望TM贡献
    tm_per_pair = (probs * tm_per_bin).sum(dim=-1)  # [N, N]

    if interface_mask is not None:
        # LEARN: iPTM只看不同链之间的残基对
        # 这是iPTM的关键——它只关注跨链的相对位置是否正确
        # 两条链各自折叠正确但对接错误时，iPTM会很低
        tm_per_pair = tm_per_pair * interface_mask
        score = tm_per_pair.sum() / interface_mask.sum().clamp(min=1)
    else:
        # LEARN: PTM取每行最大值的平均(标准TM-score定义)
        # 对于每个残基，找到与它对齐最好的那个残基，然后取平均
        score = tm_per_pair.max(dim=-1).values.mean()

    return score


# === 组件 5: ConfidenceHead (主模块) ===
class ConfidenceHead(nn.Module):
    """
    Algorithm 31: 置信度预测头。
    接收预测坐标和trunk嵌入，输出多种置信度指标。

    这是整个置信度系统的核心模块，它：
    1. 将预测坐标的距离信息编码到pair representation中
    2. 通过一个小型PairformerStack处理
    3. 输出pLDDT、PAE等多种置信度指标

    在真实Protenix中，PairformerStack有4个block，
    这里简化为单层MLP以便理解核心流程。
    """
    def __init__(self, c_s, c_z):
        super().__init__()
        # LEARN: 将预测坐标的距离信息编码到pair representation中
        # 距离是一个标量，通过线性层映射到c_z维
        self.dist_embed = nn.Linear(1, c_z)

        # 简化的PairformerStack（真实系统中有4个block）
        self.pair_norm = nn.LayerNorm(c_z)
        self.pair_update = nn.Sequential(
            nn.Linear(c_z, c_z * 2),
            nn.ReLU(),
            nn.Linear(c_z * 2, c_z),
        )
        self.single_update = nn.Sequential(
            nn.LayerNorm(c_s),
            nn.Linear(c_s, c_s * 2),
            nn.ReLU(),
            nn.Linear(c_s * 2, c_s),
        )

        # 预测头
        self.plddt_head = PLDDTHead(c_s)
        self.pae_head = PAEHead(c_z)

    def forward(self, s, z, coords, atom_to_token_idx, N_tokens):
        """
        参数:
            s: [N_tokens, c_s] — single representation (来自Evoformer)
            z: [N_tokens, N_tokens, c_z] — pair representation (来自Evoformer)
            coords: [N_atoms, 3] — 预测的原子坐标 (来自扩散模块)
            atom_to_token_idx: [N_atoms] — 原子到token的映射
            N_tokens: token总数

        返回:
            dict: 包含plddt_logits, plddt_scores, pae_logits, pae_errors
        """
        # LEARN: 步骤1 — 从预测坐标计算距离特征
        # 这是ConfidenceHead的独特之处：它使用模型自己的预测结果作为输入
        distances, ca_coords = compute_distance_features(
            coords, atom_to_token_idx, N_tokens
        )
        dist_feat = self.dist_embed(distances.unsqueeze(-1))  # [N, N, c_z]

        # LEARN: 步骤2 — 将距离信息注入pair representation
        # 原始的z来自Evoformer，加上距离特征后，z_conf同时包含
        # 序列/进化信息和结构距离信息
        z_conf = z + dist_feat
        z_conf = z_conf + self.pair_update(self.pair_norm(z_conf))

        # LEARN: 步骤3 — 更新single representation
        s_conf = s + self.single_update(s)

        # LEARN: 步骤4 — 展开到原子级别用于pLDDT
        # pLDDT是原子级别的分数，需要将token级别的特征展开
        s_atom = s_conf[atom_to_token_idx]  # [N_atoms, c_s]

        # LEARN: 步骤5 — 预测各项置信度
        plddt_logits, plddt_scores = self.plddt_head(s_atom)
        pae_logits, pae_errors = self.pae_head(z_conf)

        return {
            "plddt_logits": plddt_logits,   # [N_atoms, PLDDT_BINS]
            "plddt_scores": plddt_scores,   # [N_atoms] 0-100
            "pae_logits": pae_logits,       # [N_tokens, N_tokens, PAE_BINS]
            "pae_errors": pae_errors,       # [N_tokens, N_tokens] 单位Å
        }


# === 主流程 ===
def main():
    print("=" * 60)
    print("Protenix 学习冲刺 — Unit 6: 置信度与输出")
    print("预测质量评估：ConfidenceHead + pLDDT/PAE/PTM/iPTM")
    print("=" * 60)
    print(f"\n配置: N_tokens={N_tokens}, N_atoms={N_atoms}, "
          f"N_sample={N_sample}")
    print(f"      pLDDT bins={PLDDT_BINS}, PAE bins={PAE_BINS}, "
          f"PAE max={PAE_MAX}Å\n")

    # --- 模拟输入（来自 Unit 4 的 s/z 和 Unit 5 的坐标）---
    s = torch.randn(N_tokens, c_s) * 0.02
    z = torch.randn(N_tokens, N_tokens, c_z) * 0.02
    atom_to_token_idx = torch.arange(N_tokens).repeat_interleave(atoms_per_token)

    # 模拟多个候选结构（来自 Unit 5 的扩散采样，每个使用不同噪声）
    all_coords = [torch.randn(N_atoms, 3) * 5.0 for _ in range(N_sample)]

    # 模拟双链复合物的界面mask
    # 前半token属于链A，后半属于链B
    chain_id = torch.zeros(N_tokens, dtype=torch.long)
    chain_id[N_tokens // 2:] = 1
    interface_mask = (chain_id.unsqueeze(0) != chain_id.unsqueeze(1)).float()
    print(f"双链复合物: 链A={N_tokens // 2}个token, "
          f"链B={N_tokens - N_tokens // 2}个token")
    print(f"界面残基对数: {int(interface_mask.sum().item())}\n")

    # --- 构建 ConfidenceHead ---
    conf_head = ConfidenceHead(c_s, c_z)
    n_params = sum(p.numel() for p in conf_head.parameters())
    print(f"ConfidenceHead 参数量: {n_params:,}")

    # --- 对每个候选结构评估置信度 ---
    results = []
    print(f"\n{'=' * 60}")
    print("第一步：置信度评估（对每个候选结构打分）")
    print("=" * 60)

    with torch.no_grad():
        for i, coords in enumerate(all_coords):
            print(f"\n--- 候选 {i + 1}/{N_sample} ---")

            output = conf_head(s, z, coords, atom_to_token_idx, N_tokens)

            plddt = output["plddt_scores"]
            pae = output["pae_errors"]
            pae_logits = output["pae_logits"]

            # 计算PTM和iPTM
            ptm = compute_ptm(pae_logits)
            iptm = compute_ptm(pae_logits, interface_mask=interface_mask)

            # LEARN: Ranking Score = 0.8 * iPTM + 0.2 * PTM
            # iPTM权重更大，因为对复合物来说界面质量更重要
            ranking = 0.8 * iptm + 0.2 * ptm

            print(f"  pLDDT:   均值={plddt.mean():.1f}, "
                  f"最小={plddt.min():.1f}, 最大={plddt.max():.1f}")
            print(f"  PAE:     均值={pae.mean():.1f}Å")
            print(f"  PTM:     {ptm:.3f}")
            print(f"  iPTM:    {iptm:.3f}")
            print(f"  Ranking: {ranking:.3f}")

            results.append({
                "sample": i + 1,
                "plddt_mean": plddt.mean().item(),
                "pae_mean": pae.mean().item(),
                "ptm": ptm.item(),
                "iptm": iptm.item(),
                "ranking": ranking.item(),
            })

    # --- 排序选择最佳候选 ---
    results.sort(key=lambda x: x["ranking"], reverse=True)

    print(f"\n{'=' * 60}")
    print("第二步：候选排序（按 Ranking Score 从高到低）")
    print("=" * 60)
    print(f"  {'排名':>4s}  {'候选':>4s}  {'pLDDT':>6s}  {'PAE(Å)':>7s}  "
          f"{'PTM':>5s}  {'iPTM':>5s}  {'Ranking':>7s}")
    print(f"  {'─' * 4}  {'─' * 4}  {'─' * 6}  {'─' * 7}  "
          f"{'─' * 5}  {'─' * 5}  {'─' * 7}")
    for rank, r in enumerate(results):
        marker = " <-- 最佳" if rank == 0 else ""
        print(f"  {rank + 1:>4d}  {r['sample']:>4d}  {r['plddt_mean']:>6.1f}  "
              f"{r['pae_mean']:>7.1f}  {r['ptm']:>5.3f}  {r['iptm']:>5.3f}  "
              f"{r['ranking']:>7.3f}{marker}")

    best = results[0]
    print(f"\n  最佳候选: 候选 {best['sample']} "
          f"(Ranking={best['ranking']:.3f})")
    print(f"  在真实系统中，最佳候选的坐标会被保存为 CIF 文件输出。")

    # --- pLDDT 分布可视化 ---
    print(f"\n{'=' * 60}")
    print("第三步：pLDDT 分布分析（最佳候选）")
    print("=" * 60)

    with torch.no_grad():
        best_output = conf_head(
            s, z, all_coords[best["sample"] - 1],
            atom_to_token_idx, N_tokens
        )
    best_plddt = best_output["plddt_scores"]

    bins = [
        (0, 50, "很低"),
        (50, 70, " 低 "),
        (70, 90, " 高 "),
        (90, 100, "很高"),
    ]
    for lo, hi, label in bins:
        count = ((best_plddt >= lo) & (best_plddt < hi)).sum().item()
        pct = count / len(best_plddt) * 100
        bar = "█" * int(pct / 2)
        print(f"  {label} ({lo:>3d}-{hi:>3d}): "
              f"{count:>3d} 原子 ({pct:>5.1f}%) {bar}")

    # --- PAE 矩阵统计 ---
    print(f"\n{'=' * 60}")
    print("第四步：PAE 矩阵分析（最佳候选）")
    print("=" * 60)
    best_pae = best_output["pae_errors"]

    # 链内PAE vs 链间PAE
    intra_mask = (chain_id.unsqueeze(0) == chain_id.unsqueeze(1)).float()
    inter_mask = interface_mask

    intra_pae = (best_pae * intra_mask).sum() / intra_mask.sum()
    inter_pae = (best_pae * inter_mask).sum() / inter_mask.sum()

    print(f"  链内PAE均值: {intra_pae:.1f}Å（同一条链内残基对的误差）")
    print(f"  链间PAE均值: {inter_pae:.1f}Å（不同链残基对的误差）")
    print(f"  说明: 链间PAE通常高于链内PAE，因为界面预测更难。")

    # --- 总结 ---
    print(f"\n{'=' * 60}")
    print("总结")
    print("=" * 60)
    print(f"""
  ConfidenceHead 的工作流程：
    1. 接收预测坐标 + trunk嵌入(s, z)
    2. 从坐标计算距离特征，注入pair representation
    3. 通过小型PairformerStack处理
    4. 输出 pLDDT（原子级）、PAE（token对级）
    5. 从PAE推导 PTM（全局）和 iPTM（界面）
    6. Ranking = 0.8*iPTM + 0.2*PTM，选出最佳候选

  这是 Protenix 流水线的最后一步。
  至此，从输入序列到输出结构+置信度的完整流程已经走通。
""")


if __name__ == "__main__":
    torch.manual_seed(42)
    main()
