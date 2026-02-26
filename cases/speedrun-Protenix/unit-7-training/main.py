"""
Unit 7: 训练流程 — 从损失函数到参数更新
演示 Protenix 的完整训练循环。

关键点：训练时梯度流过整个模型——
  InputEmbedder → Pairformer → DiffusionModule → Loss → 反向传播
所有模块的参数都在被优化，不只是去噪网络。
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import math


# === 配置 ===
N_tokens = 16
atoms_per_token = 3
N_atoms = N_tokens * atoms_per_token
c_s = 64            # 简化维度（训练演示不需要大模型）
c_z = 32
c_s_inputs = 64
N_diffusion_samples = 4   # 训练时每个样本的扩散采样数（真实值48）
sigma_data = 16.0
N_train_steps = 5         # 演示训练步数
N_cycle = 2               # Pairformer 循环次数
lr = 1e-3
NUM_RESTYPES = 32


# ============================================================
# 完整模型：InputEmbedder + Pairformer + Denoiser
# ============================================================
# LEARN: 训练时梯度流过整条链，不只是 Denoiser
# 这是和 Unit 5（只演示推理）的关键区别

class InputEmbedder(nn.Module):
    """
    简化版 InputFeatureEmbedder (→ Unit 3 有详细讲解)。
    将输入特征投影为 s_inputs 和 z_init。
    """
    def __init__(self):
        super().__init__()
        self.token_proj = nn.Linear(NUM_RESTYPES, c_s_inputs)
        self.pair_proj = nn.Linear(2 * 32 + 1, c_z)  # 相对位置 one-hot
        self.max_rel_pos = 32

    def forward(self, restype_onehot):
        N = restype_onehot.shape[0]
        # LEARN: token 嵌入
        s_inputs = self.token_proj(restype_onehot)  # [N, c_s_inputs]

        # LEARN: pair 嵌入（相对位置编码）
        pos = torch.arange(N)
        rel_pos = (pos.unsqueeze(0) - pos.unsqueeze(1)).clamp(
            -self.max_rel_pos, self.max_rel_pos
        ) + self.max_rel_pos
        rel_onehot = F.one_hot(rel_pos, 2 * self.max_rel_pos + 1).float()
        z = self.pair_proj(rel_onehot)  # [N, N, c_z]

        return s_inputs, z


class SimplePairformerBlock(nn.Module):
    """简化版 PairformerBlock (→ Unit 4 有详细讲解)。"""
    def __init__(self):
        super().__init__()
        # pair 更新（简化的三角乘法）
        self.z_norm = nn.LayerNorm(c_z)
        self.z_proj_a = nn.Linear(c_z, c_z)
        self.z_proj_b = nn.Linear(c_z, c_z)
        self.z_out = nn.Linear(c_z, c_z)
        # single 更新（pair-biased attention 简化为投影）
        self.s_norm = nn.LayerNorm(c_s)
        self.s_proj = nn.Linear(c_s, c_s)
        self.z_to_s = nn.Linear(c_z, c_s)
        # transition
        self.s_ffn = nn.Sequential(nn.LayerNorm(c_s), nn.Linear(c_s, c_s * 2),
                                   nn.SiLU(), nn.Linear(c_s * 2, c_s))
        self.z_ffn = nn.Sequential(nn.LayerNorm(c_z), nn.Linear(c_z, c_z * 2),
                                   nn.SiLU(), nn.Linear(c_z * 2, c_z))

    def forward(self, s, z):
        # LEARN: 三角乘法更新 z（简化版）
        z_n = self.z_norm(z)
        a = self.z_proj_a(z_n)
        b = self.z_proj_b(z_n)
        z = z + self.z_out(torch.einsum("ikc,jkc->ijc", a, b) / N_tokens)
        z = z + self.z_ffn(z)

        # LEARN: pair 信息流入 single
        z_bias = self.z_to_s(z.mean(dim=1))  # [N, c_s]
        s = s + self.s_proj(self.s_norm(s)) + z_bias
        s = s + self.s_ffn(s)
        return s, z


class Denoiser(nn.Module):
    """
    简化版 DiffusionModule (→ Unit 5 有详细讲解)。
    接收 Pairformer 输出的 s, z 作为条件。
    """
    def __init__(self):
        super().__init__()
        # LEARN: 噪声水平编码
        self.sigma_embed = nn.Sequential(
            nn.Linear(1, c_s), nn.SiLU(), nn.Linear(c_s, c_s)
        )
        # LEARN: 坐标 + 条件 → 预测坐标
        self.coord_proj = nn.Linear(3, c_s)
        self.cond_norm = nn.LayerNorm(c_s)
        self.net = nn.Sequential(
            nn.Linear(c_s, c_s * 2), nn.SiLU(), nn.Linear(c_s * 2, c_s),
        )
        self.out_proj = nn.Linear(c_s, 3)

    def forward(self, x_noisy, s, atom_to_token_idx, sigma):
        """
        x_noisy: [N_samples, N_atoms, 3]
        s: [N_tokens, c_s] — 来自 Pairformer
        sigma: [N_samples]
        """
        N_samples = x_noisy.shape[0]

        # LEARN: 噪声水平编码
        sigma_feat = self.sigma_embed(sigma.view(-1, 1))  # [N_samples, c_s]

        # LEARN: 将 Pairformer 的 single representation 作为条件
        # 这就是梯度能流回 Pairformer 的关键连接
        s_per_atom = s[atom_to_token_idx]  # [N_atoms, c_s]
        s_cond = self.cond_norm(s_per_atom)  # [N_atoms, c_s]

        # LEARN: 坐标嵌入 + 条件 + 噪声水平
        coord_feat = self.coord_proj(x_noisy)  # [N_samples, N_atoms, c_s]
        # 广播: s_cond [N_atoms, c_s] → [1, N_atoms, c_s]
        # sigma_feat [N_samples, c_s] → [N_samples, 1, c_s]
        h = coord_feat + s_cond.unsqueeze(0) + sigma_feat.unsqueeze(1)
        h = self.net(h)
        return self.out_proj(h)


class ProtenixTrainModel(nn.Module):
    """
    完整的训练模型，包含所有子模块。

    LEARN: 训练时的前向路径：
      InputEmbedder → Pairformer (N_cycle) → Denoiser → 预测坐标
                                                ↓
                                            Loss → 反向传播
                                                ↓
                              梯度流回所有模块（包括 Pairformer 和 Embedder）
    """
    def __init__(self):
        super().__init__()
        self.embedder = InputEmbedder()
        self.s_proj = nn.Linear(c_s_inputs, c_s)
        self.pairformer_blocks = nn.ModuleList(
            [SimplePairformerBlock() for _ in range(2)]
        )
        self.denoiser = Denoiser()
        self.distogram_head = nn.Linear(c_z, 64)

    def forward_trunk(self, restype_onehot):
        """前向传播 trunk 部分：Embedder + Pairformer"""
        s_inputs, z = self.embedder(restype_onehot)
        s = self.s_proj(s_inputs)

        for cycle in range(N_cycle):
            for block in self.pairformer_blocks:
                s, z = block(s, z)

        return s, z

    def forward_diffusion(self, s, x_noisy, atom_to_token_idx, sigma):
        """前向传播扩散部分：Denoiser"""
        return self.denoiser(x_noisy, s, atom_to_token_idx, sigma)

    def forward_distogram(self, z):
        """Distogram 预测"""
        logits = self.distogram_head(z)
        return (logits + logits.transpose(0, 1)) / 2


# ============================================================
# 训练噪声采样器
# ============================================================

class TrainingNoiseSampler:
    """
    使用对数正态分布采样噪声水平。
    类比：推理时按固定工序从粗到细，训练时随机抽一个"灰尘程度"让学徒练习。
    sigma = exp(N(p_mean, p_std)) * sigma_data
    """
    def __init__(self, p_mean=-1.2, p_std=1.5, sigma_data=16.0):
        self.p_mean = p_mean
        self.p_std = p_std
        self.sigma_data = sigma_data

    def sample(self, n):
        log_sigma = torch.randn(n) * self.p_std + self.p_mean
        return log_sigma.exp() * self.sigma_data


# ============================================================
# 损失函数
# ============================================================

class SmoothLDDTLoss(nn.Module):
    """
    Algorithm 27: 平滑局部距离差异测试损失。
    比较原子之间的距离是否正确（而非绝对坐标），对平移/旋转不变。
    """
    def __init__(self, thresholds=None, radius=15.0):
        super().__init__()
        self.thresholds = thresholds or [0.5, 1.0, 2.0, 4.0]
        self.radius = radius

    def forward(self, pred_coords, true_coords):
        pred_dist = torch.cdist(pred_coords.unsqueeze(0), pred_coords.unsqueeze(0)).squeeze(0)
        true_dist = torch.cdist(true_coords.unsqueeze(0), true_coords.unsqueeze(0)).squeeze(0)
        local_mask = (true_dist < self.radius) & (true_dist > 0)
        dist_diff = (pred_dist - true_dist).abs()

        score = torch.zeros_like(dist_diff)
        for t in self.thresholds:
            score += 0.25 * torch.sigmoid(2.0 * (t - dist_diff))

        if local_mask.sum() > 0:
            lddt = (score * local_mask).sum() / local_mask.sum()
        else:
            lddt = torch.tensor(0.5)
        return 1.0 - lddt, lddt


class BondLoss(nn.Module):
    """化学键长度损失：惩罚不正确的键长。"""
    def forward(self, pred_coords, true_coords, bond_pairs):
        if len(bond_pairs) == 0:
            return torch.tensor(0.0)
        i, j = bond_pairs[:, 0], bond_pairs[:, 1]
        pred_len = (pred_coords[i] - pred_coords[j]).norm(dim=-1)
        true_len = (true_coords[i] - true_coords[j]).norm(dim=-1)
        return F.mse_loss(pred_len, true_len)


# ============================================================
# Mini-Rollout + 标签置换
# ============================================================

def mini_rollout(model, restype_onehot, atom_to_token_idx, n_steps=5):
    """
    快速生成一个粗略预测，用于标签对齐。
    注意：mini-rollout 在 no_grad 下运行，不参与梯度计算。
    """
    with torch.no_grad():
        s, z = model.forward_trunk(restype_onehot)
        x = torch.randn(1, N_atoms, 3) * 160.0
        sigmas = torch.linspace(160.0, 0.01, n_steps + 1)
        for i in range(n_steps):
            x_pred = model.forward_diffusion(s, x, atom_to_token_idx, sigmas[i:i+1])
            d = (x - x_pred) / sigmas[i]
            x = x + d * (sigmas[i+1] - sigmas[i])
    return x.squeeze(0)


def label_permutation(pred_coords, true_coords):
    """简化版标签置换：原始 vs x轴翻转，选 RMSD 更小的。"""
    flipped = true_coords.clone()
    flipped[:, 0] *= -1
    rmsd_orig = (pred_coords - true_coords).pow(2).sum(-1).mean().sqrt()
    rmsd_flip = (pred_coords - flipped).pow(2).sum(-1).mean().sqrt()
    if rmsd_flip < rmsd_orig:
        return flipped, rmsd_flip.item()
    return true_coords, rmsd_orig.item()


# ============================================================
# EMA (指数移动平均)
# ============================================================

class EMAWrapper:
    """shadow = decay * shadow + (1-decay) * current"""
    def __init__(self, model, decay=0.999):
        self.model = model
        self.decay = decay
        self.shadow = {n: p.clone().detach() for n, p in model.named_parameters()}

    def update(self):
        for n, p in self.model.named_parameters():
            self.shadow[n].mul_(self.decay).add_(p.data, alpha=1 - self.decay)

    def apply_shadow(self):
        self.backup = {n: p.data.clone() for n, p in self.model.named_parameters()}
        for n, p in self.model.named_parameters():
            p.data.copy_(self.shadow[n])

    def restore(self):
        for n, p in self.model.named_parameters():
            p.data.copy_(self.backup[n])


# ============================================================
# 完整训练步
# ============================================================

def train_step(model, noise_sampler, lddt_loss_fn, bond_loss_fn,
               optimizer, restype_onehot, true_coords, bond_pairs,
               atom_to_token_idx, step_idx):

    print(f"\n{'─' * 60}")
    print(f"训练步 {step_idx + 1}/{N_train_steps}")
    print("─" * 60)

    # --- 步骤 1: Mini-Rollout + 标签置换 (no_grad) ---
    mini_pred = mini_rollout(model, restype_onehot, atom_to_token_idx, n_steps=5)
    aligned_label, best_rmsd = label_permutation(mini_pred, true_coords)
    print(f"  [Mini-Rollout] 标签置换 RMSD: {best_rmsd:.2f}Å")

    # --- 步骤 2: 前向传播 trunk (有梯度!) ---
    # LEARN: 这是关键——s 和 z 带着梯度，损失会反传到 Embedder 和 Pairformer
    s, z = model.forward_trunk(restype_onehot)
    print(f"  [Trunk] s: {s.shape}, z: {z.shape} (梯度已连接)")

    # --- 步骤 3: 采样噪声 + 加噪 + 去噪 ---
    sigmas = noise_sampler.sample(N_diffusion_samples)
    noise = torch.randn(N_diffusion_samples, N_atoms, 3)
    x_noisy = aligned_label.unsqueeze(0) + sigmas.view(-1, 1, 1) * noise

    # LEARN: Denoiser 接收 Pairformer 输出的 s 作为条件
    # 梯度从 loss → x_pred → Denoiser → s → Pairformer → Embedder
    x_pred = model.forward_diffusion(s, x_noisy, atom_to_token_idx, sigmas)
    print(f"  [Diffusion] σ: [{sigmas.min():.2f}, {sigmas.max():.2f}], "
          f"x_pred: {x_pred.shape}")

    # --- 步骤 4: 计算损失 ---
    loss_dict = {}

    # SmoothLDDT 损失
    lddt_losses = []
    for i in range(N_diffusion_samples):
        l, _ = lddt_loss_fn(x_pred[i], aligned_label)
        lddt_losses.append(l)
    loss_lddt = torch.stack(lddt_losses).mean()
    loss_dict["smooth_lddt"] = loss_lddt.item()

    # MSE 损失（按噪声水平加权）
    mse_weights = sigma_data ** 2 / (sigmas ** 2 + sigma_data ** 2)
    mse_per_sample = (x_pred - aligned_label.unsqueeze(0)).pow(2).sum(-1).mean(-1)
    loss_mse = (mse_per_sample * mse_weights).mean()
    loss_dict["mse"] = loss_mse.item()

    # Bond 损失
    bond_losses = [bond_loss_fn(x_pred[i], aligned_label, bond_pairs)
                   for i in range(N_diffusion_samples)]
    loss_bond = torch.stack(bond_losses).mean()
    loss_dict["bond"] = loss_bond.item()

    # Distogram 损失（梯度也流过 z → Pairformer）
    ca_idx = torch.arange(N_tokens) * atoms_per_token + 1
    true_ca = aligned_label[ca_idx]
    dist_logits = model.forward_distogram(z)  # z 带梯度!
    true_dist = torch.cdist(true_ca.unsqueeze(0), true_ca.unsqueeze(0)).squeeze(0)
    true_bins = ((true_dist - 2.0) / (20.0 / 64)).long().clamp(0, 63)
    loss_dist = F.cross_entropy(dist_logits.reshape(-1, 64), true_bins.reshape(-1))
    loss_dict["distogram"] = loss_dist.item()

    # 加权总损失
    total_loss = (1.0 * (loss_lddt + loss_mse)
                  + 0.1 * loss_bond
                  + 0.3 * loss_dist)
    loss_dict["total"] = total_loss.item()

    # --- 步骤 5: 反向传播 ---
    optimizer.zero_grad()
    total_loss.backward()
    grad_norm = nn.utils.clip_grad_norm_(model.parameters(), max_norm=10.0)
    optimizer.step()

    # LEARN: 验证梯度确实流过了所有模块
    grad_info = {}
    for name, param in model.named_parameters():
        if param.grad is not None:
            module = name.split(".")[0]
            if module not in grad_info:
                grad_info[module] = []
            grad_info[module].append(param.grad.abs().mean().item())

    print(f"  [损失] lddt={loss_dict['smooth_lddt']:.4f}, mse={loss_dict['mse']:.4f}, "
          f"bond={loss_dict['bond']:.4f}, dist={loss_dict['distogram']:.4f}")
    print(f"  [总损失] {total_loss.item():.4f}, 梯度范数={grad_norm:.4f}")
    print(f"  [梯度分布] ", end="")
    for module, grads in sorted(grad_info.items()):
        avg = sum(grads) / len(grads)
        print(f"{module}={avg:.4f}  ", end="")
    print()

    return loss_dict


# ============================================================
# 主流程
# ============================================================

def main():
    print("🧬 Protenix 训练流程 — 完整前向路径 + 损失 + 反向传播")
    print(f"   配置: N_tokens={N_tokens}, N_atoms={N_atoms}, N_cycle={N_cycle}")
    print(f"   扩散采样数={N_diffusion_samples}, 训练步数={N_train_steps}, lr={lr}")

    # --- 构造模拟数据 ---
    print(f"\n{'=' * 60}")
    print("准备训练数据")
    print("=" * 60)

    # 输入特征
    restype_onehot = F.one_hot(torch.randint(0, 20, (N_tokens,)), NUM_RESTYPES).float()
    atom_to_token_idx = torch.arange(N_tokens).repeat_interleave(atoms_per_token)

    # 真实坐标（螺旋结构）
    true_coords = torch.zeros(N_atoms, 3)
    for i in range(N_atoms):
        t = i * 0.5
        true_coords[i] = torch.tensor([math.cos(t) * 5, math.sin(t) * 5, t * 1.5])
    print(f"  输入: restype {restype_onehot.shape}, 真实坐标 {true_coords.shape}")

    # 化学键
    bond_pairs = torch.stack([torch.arange(N_atoms - 1), torch.arange(1, N_atoms)], dim=1)

    # --- 构建完整模型 ---
    print(f"\n{'=' * 60}")
    print("构建完整模型")
    print("=" * 60)

    model = ProtenixTrainModel()
    total_params = sum(p.numel() for p in model.parameters())
    for name, module in [("embedder", model.embedder), ("s_proj", model.s_proj),
                         ("pairformer", model.pairformer_blocks),
                         ("denoiser", model.denoiser),
                         ("distogram_head", model.distogram_head)]:
        n = sum(p.numel() for p in module.parameters())
        print(f"  {name:20s}: {n:>8,} 参数")
    print(f"  {'总计':20s}: {total_params:>8,} 参数")
    print(f"\n  LEARN: 所有模块的参数都参与训练，梯度流过完整路径：")
    print(f"         Embedder → Pairformer → Denoiser → Loss → 反向传播")

    noise_sampler = TrainingNoiseSampler()
    lddt_loss_fn = SmoothLDDTLoss()
    bond_loss_fn = BondLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    ema = EMAWrapper(model, decay=0.999)

    # --- 噪声分布 ---
    print(f"\n{'=' * 60}")
    print("训练噪声分布 (对数正态)")
    print("=" * 60)
    sample_sigmas = noise_sampler.sample(1000)
    for lo, hi in [(0, 1), (1, 10), (10, 100), (100, 1000)]:
        count = ((sample_sigmas >= lo) & (sample_sigmas < hi)).sum().item()
        pct = count / 10
        bar = "█" * int(pct / 2)
        print(f"  σ ∈ [{lo:>5d}, {hi:>5d}): {count:>4d}/1000 ({pct:>5.1f}%) {bar}")

    # --- 训练循环 ---
    print(f"\n{'=' * 60}")
    print("开始训练")
    print("=" * 60)

    loss_history = []
    for step in range(N_train_steps):
        loss_dict = train_step(
            model, noise_sampler, lddt_loss_fn, bond_loss_fn,
            optimizer, restype_onehot, true_coords, bond_pairs,
            atom_to_token_idx, step
        )
        loss_history.append(loss_dict)
        ema.update()

    # --- 训练曲线 ---
    print(f"\n{'=' * 60}")
    print("训练损失曲线")
    print("=" * 60)
    print(f"  {'步数':>4s}  {'总损失':>8s}  {'LDDT':>8s}  {'MSE':>8s}  "
          f"{'Bond':>8s}  {'Distogram':>10s}")
    print(f"  {'─'*4}  {'─'*8}  {'─'*8}  {'─'*8}  {'─'*8}  {'─'*10}")
    for i, ld in enumerate(loss_history):
        print(f"  {i+1:>4d}  {ld['total']:>8.4f}  {ld['smooth_lddt']:>8.4f}  "
              f"{ld['mse']:>8.4f}  {ld['bond']:>8.4f}  {ld['distogram']:>10.4f}")

    # --- 总结 ---
    print(f"\n{'=' * 60}")
    print("总结")
    print("=" * 60)
    print("""
  完整训练路径（梯度流向）:

    restype_onehot
         ↓
    [InputEmbedder] → s_inputs, z_init     ← 梯度到达这里
         ↓
    [Pairformer × N_cycle] → s, z          ← 梯度到达这里
         ↓                    ↓
    [Denoiser]          [DistogramHead]     ← 梯度到达这里
    (条件: s)           (输入: z)
         ↓                    ↓
    x_pred               dist_logits
         ↓                    ↓
    LDDT+MSE+Bond Loss   Distogram Loss
         ↓                    ↓
         └────── total_loss ──┘
                    ↓
              反向传播 → 更新所有参数 → EMA

  训练 vs 推理:
    训练: 单步去噪 + 对数正态噪声 + 标签置换 + 全模型梯度
    推理: 200步去噪链 + 确定性调度 + 无梯度 + EMA参数
    """)


if __name__ == "__main__":
    torch.manual_seed(42)
    main()
