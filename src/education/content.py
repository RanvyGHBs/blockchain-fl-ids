"""
Educational Content Registry for Section 6: Learn & Explore.
Contains rich, pedagogically structured educational material for all 9 modules across 5 progressive levels:
Level 1: Understand (Plain-English explanation & analogy)
Level 2: Visualize (Interactive demonstrations & process flows)
Level 3: Mathematical Foundations (Equations, variable definitions, worked numerical examples)
Level 4: Technical Deep-Dive (Pseudocode, algorithmic trade-offs, limitations)
Level 5: Knowledge Check (Interactive quizzes with explanations)
Plus "How This Works in Our System" linkages to active codebase files.
"""

from typing import Dict, Any, List

EDUCATIONAL_MODULES: Dict[str, Dict[str, Any]] = {
    "module_1": {
        "id": "module_1",
        "title": "Module 1: Federated Learning Fundamentals",
        "icon": "🌐",
        "tagline": "Collaborative machine learning without raw data centralization",
        "level_1_understand": {
            "summary": "In traditional machine learning, all data must be sent to one central server. Federated Learning inverts this: the model travels to the data, trains locally on each participant's device, and only mathematical weight updates are shared.",
            "analogy": "Imagine five hospitals that want to train an AI to detect a rare disease. Due to medical privacy laws (HIPAA), they cannot share patient records with each other or a tech company. Instead, a central coordinator sends an untrained AI model to each hospital. Each hospital trains the model on its own private patients, calculates how the model's weights should adjust, and sends only those adjustments back to be averaged together.",
            "why_it_matters": "Federated Learning enables multi-organizational collaboration across sensitive domains—banking fraud, healthcare diagnostics, and network cyber-defense—without violating data sovereignty or confidentiality laws.",
            "core_concepts": [
                "Local Datasets: Data remains strictly within the organization's boundary.",
                "Client-Server Architecture: Server coordinates global model distribution; clients perform local stochastic gradient descent.",
                "Communication Rounds: Iterative cycle of weight broadcast -> local training -> aggregation -> global update."
            ]
        },
        "level_2_visualize": {
            "demo_type": "fl_lifecycle",
            "description": "Visualizing the 4-phase Federated Learning lifecycle across rounds.",
            "steps": [
                {"step": "1. Broadcast", "desc": "Central coordinator sends current global model weights w^t to all active clients."},
                {"step": "2. Local Training", "desc": "Each client trains w^t on private data for E epochs using Adam or SGD."},
                {"step": "3. Update Upload", "desc": "Clients send weight updates w_k to the coordinator. No raw records are shared."},
                {"step": "4. Aggregation", "desc": "Coordinator averages client updates into new global model w^(t+1) via FedAvg."}
            ]
        },
        "level_3_math": {
            "equation": r"w^{t+1} = \sum_{k=1}^{K} \frac{n_k}{N} w_k^{t+1}",
            "variables": [
                ("w^{t+1}", "New global model weight vector for round t+1"),
                ("K", "Total number of participating federated clients"),
                ("n_k", "Number of local training samples held by client k"),
                ("N", "Total number of samples across all clients (sum of all n_k)"),
                ("w_k^{t+1}", "Local model weight vector trained by client k in round t")
            ],
            "worked_example": "Suppose Client A has 3,000 samples and submits weight w_A = [1.0, 2.0]. Client B has 1,000 samples and submits w_B = [3.0, 6.0]. Total samples N = 4,000. Weight of A = 3,000/4,000 = 0.75. Weight of B = 1,000/4,000 = 0.25. New global weight = 0.75*[1.0, 2.0] + 0.25*[3.0, 6.0] = [0.75 + 0.75, 1.5 + 1.5] = [1.5, 3.0]."
        },
        "level_4_technical": {
            "pseudocode": """Algorithm: FederatedAveraging (FedAvg)
Server initializes w_0
for each round t = 1, 2, ... do:
    for each client k in parallel do:
        w_k^(t+1) = ClientUpdate(k, w^t)
    w^(t+1) = sum( (n_k / N) * w_k^(t+1) )

ClientUpdate(k, w):
    Initialize local model with w
    for local epoch e = 1 to E do:
        for batch (x, y) in local_data do:
            w = w - eta * grad_loss(w; x, y)
    return w to server""",
            "tradeoffs": "Advantage: Drastically cuts raw communication bandwidth and keeps raw data local. Limitation: Prone to poisoning attacks—if Client B is malicious and submits w_B = [1000, 2000], standard FedAvg blindly averages it, destroying the global model."
        },
        "level_5_quiz": [
            {
                "question": "What is exchanged between clients and the coordinator in standard Federated Learning?",
                "options": ["Raw training records and patient files", "Model weight vectors and parameter updates", "Complete database dumps", "Feature correlation matrices"],
                "correct": 1,
                "explanation": "In Federated Learning, raw datasets never leave the local nodes. Clients only send model parameter updates (weights/gradients)."
            },
            {
                "question": "Why does FedAvg weight client contributions by n_k / N?",
                "options": ["To give more influence to clients with faster internet", "To give proportional influence to clients holding more training data", "To penalize clients with larger datasets", "To randomize client influence"],
                "correct": 1,
                "explanation": "Weighting by n_k / N ensures that the federated average mathematically approximates training on the entire combined dataset."
            }
        ],
        "how_it_works_in_system": {
            "source_files": ["src/federated/client.py", "src/federated/server.py", "src/federated/orchestrator.py"],
            "role": "Implements the core multi-client training loop. Clients train PyTorch IDSNet models locally on private NSL-KDD slices.",
            "action_link": "Section 2: Federated Learning & Defense Studio"
        }
    },

    "module_2": {
        "id": "module_2",
        "title": "Module 2: Non-IID Data & Statistical Heterogeneity",
        "icon": "📊",
        "tagline": "Why real-world distributed datasets have different distributions",
        "level_1_understand": {
            "summary": "In standard machine learning, researchers assume data is Independent and Identically Distributed (IID)—meaning every participant has a random, identical mix of all classes. In the real world, data is Non-IID: different network subnets see vastly different traffic patterns.",
            "analogy": "A university campus network sees heavy streaming and web browsing (normal traffic), while an enterprise database server sees repeated brute-force login attempts (R2L attacks), and a public DNS server sees massive UDP flooding (DoS attacks). Neither has a 'balanced' view of the whole internet.",
            "why_it_matters": "If Node A sees mostly DoS and Node B sees mostly Normal traffic, their gradient updates naturally point in different directions. A naive security filter might mistakenly flag Node A as an attacker simply because its traffic is specialized.",
            "core_concepts": [
                "IID Data: Uniform class distribution across all participants.",
                "Non-IID Data: Extreme class skew; some nodes hold zero samples of certain attack types.",
                "Dirichlet Distribution Dir(alpha): Mathematical distribution used to simulate realistic Non-IID partitions."
            ]
        },
        "level_2_visualize": {
            "demo_type": "dirichlet_slider",
            "description": "Adjust Dirichlet alpha to observe how class distributions skew across clients.",
            "explanation": "When alpha is large (e.g. 10.0), data is nearly IID (balanced). When alpha is small (e.g. 0.1 or 0.5), severe Non-IID skew occurs: one client might own 95% of all DoS attacks."
        },
        "level_3_math": {
            "equation": r"p_k \sim \text{Dirichlet}(\alpha \cdot \mathbf{1}_K) \quad \text{where} \quad \sum_{k=1}^K p_{k,c} = 1",
            "variables": [
                (r"\alpha", "Dirichlet concentration parameter (lower = higher skew)"),
                ("K", "Number of participating clients"),
                ("p_k", "Proportion vector of class c assigned to client k"),
                ("c", "Class index (e.g. Normal vs Attack)")
            ],
            "worked_example": "With alpha=0.5 across 3 clients for 1,000 DoS packets, Dirichlet sampling might produce proportions [0.72, 0.25, 0.03]. Client 0 gets 720 packets, Client 1 gets 250 packets, and Client 2 gets only 30 packets. If alpha were 100.0, the proportions would be nearly identical: [0.33, 0.33, 0.34]."
        },
        "level_4_technical": {
            "pseudocode": """Algorithm: NonIID_Dirichlet_Partition(dataset, K, alpha):
for each class c in unique_classes:
    indices_c = indices of samples where label == c
    proportions = sample_dirichlet(alpha, K)
    split_points = cumulative_sum(proportions) * len(indices_c)
    for client k in 0 to K-1:
        assign indices_c[split_points[k]:split_points[k+1]] to client k
return client_splits""",
            "tradeoffs": "Advantage: Models authentic enterprise network conditions. Challenge: Weight divergence increases, slowing down global convergence and complicating cosine-similarity-based attack detection."
        },
        "level_5_quiz": [
            {
                "question": "What happens when the Dirichlet parameter alpha is set to a very low value (e.g., alpha = 0.1)?",
                "options": ["Data becomes uniformly balanced across all clients (IID)", "Data becomes extremely skewed with clients specialized in single classes (Non-IID)", "The dataset is deleted", "Client training speed doubles"],
                "correct": 1,
                "explanation": "A lower alpha concentrates probability mass into fewer clients, creating extreme class imbalance (high Non-IID skew)."
            }
        ],
        "how_it_works_in_system": {
            "source_files": ["src/data/partitioner.py"],
            "role": "Splits NSL-KDD across the 5 simulated nodes with Dir(alpha=0.5), creating specialized network profiles for Nodes 0-4.",
            "action_link": "Section 1: System Overview (Level 2 Inspection)"
        }
    },

    "module_3": {
        "id": "module_3",
        "title": "Module 3: Privacy-Preserving Machine Learning",
        "icon": "🔒",
        "tagline": "Protecting parameter updates against gradient inversion and memorization",
        "level_1_understand": {
            "summary": "Even if raw training data is not shared, raw gradient updates can theoretically leak information. Advanced adversaries can run 'gradient inversion' to reconstruct private training samples. Parameter perturbation reduces this risk.",
            "analogy": "Imagine answering an anonymous survey about your income. Instead of writing your exact salary ($75,420), the survey adds a random noise value between -$1,000 and +$1,000. When thousands of surveys are averaged, the average income is still accurate, but nobody can determine your exact salary.",
            "why_it_matters": "In collaborative cyber-defense, raw packet features might reveal sensitive internal IP addresses or server vulnerabilities. Adding calibrated noise ensures plausible deniability.",
            "core_concepts": [
                "L2 Norm Clipping: Enforces an upper bound C on weight vectors to limit any single client's maximum influence.",
                "Gaussian Mechanism: Injects zero-mean Gaussian noise scaled to the clipping threshold.",
                "Empirical Perturbation vs Formal DP: Noise addition provides heuristic scrambling, but a formal (epsilon, delta) guarantee requires mathematical privacy accounting."
            ]
        },
        "level_2_visualize": {
            "demo_type": "clipping_visualizer",
            "description": "Observe how L2-norm clipping projects large vectors back onto a sphere of radius C.",
            "explanation": "If a client submits a vector of length 15.0 and the clipping threshold C is 1.0, the vector is scaled down by 15.0 so its norm equals 1.0, before Gaussian noise is added."
        },
        "level_3_math": {
            "equation": r"w_{\text{clipped}} = \frac{w}{\max\left(1, \frac{\|w\|_2}{C}\right)}, \quad w_{\text{priv}} = w_{\text{clipped}} + \mathcal{N}\left(0, (\sigma \cdot C)^2 \mathbf{I}\right)",
            "variables": [
                ("w", "Original local model parameter vector"),
                ("C", "L2-norm clipping threshold (bounds sensitivity)"),
                (r"\sigma", "Noise multiplier ratio"),
                (r"\mathcal{N}(0, \Sigma)", "Zero-mean multivariate Gaussian noise vector")
            ],
            "worked_example": "If weight vector w = [3.0, 4.0], its L2 norm is sqrt(3^2 + 4^2) = 5.0. If clipping threshold C = 1.0, the clip factor is max(1, 5.0/1.0) = 5.0. Clipped vector w_clipped = [3/5, 4/5] = [0.6, 0.8] (norm = 1.0). If sigma = 0.01, Gaussian noise with std = 0.01*1.0 = 0.01 is added to each coordinate."
        },
        "level_4_technical": {
            "pseudocode": """Algorithm: L2_Clipped_Gaussian_Perturbation(w, C, sigma):
norm = sqrt(sum(w_i^2))
clip_factor = max(1.0, norm / C)
w_clipped = w / clip_factor
noise = sample_gaussian(mean=0, std=sigma * C, shape=w.shape)
return w_clipped + noise""",
            "tradeoffs": "Advantage: Restricts gradient inversion risk and bounds outlier weights. Technical Reality: Our existing system implements empirical clipping and perturbation. It does NOT track formal (epsilon, delta) composition over rounds with a Moments Accountant."
        },
        "level_5_quiz": [
            {
                "question": "What is the primary function of L2-norm clipping in privacy perturbation?",
                "options": ["To make training run faster", "To bound the maximum influence any single update can have on the model", "To eliminate all noise from the dataset", "To encrypt the weights with a private key"],
                "correct": 1,
                "explanation": "L2-norm clipping limits the sensitivity of the update by ensuring its norm never exceeds threshold C."
            }
        ],
        "how_it_works_in_system": {
            "source_files": ["src/privacy/differential.py"],
            "role": "Applies L2-norm clipping (C=1.0) and Gaussian noise perturbation to client weights before ECDSA signing.",
            "action_link": "Section 2: Federated Learning & Defense Studio (Scenario 4)"
        }
    },

    "module_4": {
        "id": "module_4",
        "title": "Module 4: Federated Aggregation Algorithms",
        "icon": "⚖️",
        "tagline": "How the coordinator combines multi-party model updates",
        "level_1_understand": {
            "summary": "When multiple participants submit model updates, the server must combine them into a single global model. The choice of aggregation algorithm determines whether the system is vulnerable to poisoning or robust against outliers.",
            "analogy": "Imagine asking 5 judges to score a performance. Four honest judges score 8.5, 8.7, 8.6, and 8.9. One corrupted judge scores 0.1 to ruin the contestant. If you take the standard average, the score drops to 6.96. If you use the median (8.7) or trimmed mean, the corrupted score is discarded.",
            "why_it_matters": "FedAvg is optimal when everyone is honest. But in untrusted environments, robust aggregators (Trimmed Mean, Median, Trust-Weighted) are required to filter out Byzantine outliers.",
            "core_concepts": [
                "FedAvg: Sample-weighted arithmetic mean (fast, but zero attack tolerance).",
                "Trimmed Mean: Discards the top and bottom beta fraction of updates for each coordinate.",
                "Coordinate Median: Takes the median value across clients for each coordinate.",
                "Trust-Weighted FedAvg: Weights updates by sample count AND cryptographic reputation score."
            ]
        },
        "level_2_visualize": {
            "demo_type": "aggregator_comparison",
            "description": "Compare how FedAvg, Trimmed Mean, Median, and Trust-Weighted handle an outlier update.",
            "explanation": "When an attacker submits a massive weight (e.g. +100.0), FedAvg is pulled toward +20.0, while Median and Trimmed Mean remain locked onto the honest cluster (~0.0)."
        },
        "level_3_math": {
            "equation": r"w_{\text{TrustWeighted}} = \sum_{k=1}^K \frac{n_k \cdot R_k}{\sum_{j=1}^K n_j \cdot R_j} w_k",
            "variables": [
                ("R_k", "Reputation score of client k (0.0 <= R_k <= 1.0)"),
                ("n_k", "Sample count of client k"),
                ("w_k", "Parameter vector submitted by client k")
            ],
            "worked_example": "If Node 0 (honest, R=1.0, n=100) submits w=1.0 and Node 3 (attacker, slashed R=0.1, n=100) submits w=50.0. Effective weight of Node 0 = 100*1.0 = 100. Effective weight of Node 3 = 100*0.1 = 10. Total = 110. Global weight = (100/110)*1.0 + (10/110)*50.0 = 0.91 + 4.55 = 5.46 (drastically reduced from FedAvg's (1.0+50.0)/2 = 25.5)."
        },
        "level_4_technical": {
            "pseudocode": """Algorithm: Coordinate_Trimmed_Mean(weights_list, beta):
D = dimension of weights
K = number of clients
for coordinate d = 1 to D:
    values = [w[d] for w in weights_list]
    sorted_values = sort(values)
    k_trim = int(beta * K)
    trimmed = sorted_values[k_trim : K - k_trim]
    w_global[d] = mean(trimmed)
return w_global""",
            "tradeoffs": "Median and Trimmed Mean provide coordinate-level Byzantine tolerance but are computationally heavier than FedAvg and discard legitimate variance under high Non-IID skew."
        },
        "level_5_quiz": [
            {
                "question": "Why does standard FedAvg fail when an attacker injects extreme Gaussian noise into its weights?",
                "options": ["FedAvg crashes due to zero-division", "FedAvg averages all weights uniformly, allowing the outlier to pull the global model off course", "FedAvg automatically disconnects the client", "FedAvg encrypts the noise"],
                "correct": 1,
                "explanation": "Because arithmetic mean is not robust against arbitrary outliers, an extreme update heavily distorts the average."
            }
        ],
        "how_it_works_in_system": {
            "source_files": ["src/federated/aggregators.py"],
            "role": "Provides aggregate_fedavg, aggregate_trimmed_mean, aggregate_median, and aggregate_trust_weighted called by the Server.",
            "action_link": "Section 2: Federated Learning & Defense Studio"
        }
    },

    "module_5": {
        "id": "module_5",
        "title": "Module 5: Security Threats & Poisoning Attacks",
        "icon": "🚨",
        "tagline": "How adversaries attempt to sabotage collaborative IDS models",
        "level_1_understand": {
            "summary": "Because the central coordinator cannot see raw client data, malicious participants can attempt to subvert the global model by poisoning their local data or manipulating their local parameter updates.",
            "analogy": "Imagine a shared neighborhood watch map where residents report suspicious activity. A criminal joins the watch and systematically marks safe streets as dangerous and dangerous burglaries as safe (label flipping), or submits random garbage locations to make the map useless (noise attack).",
            "why_it_matters": "In an intrusion detection system, an attacker could invert model weights to make DoS or PortScan attacks invisible to the neural network.",
            "core_concepts": [
                "Data Poisoning (Label Flipping): Adversary changes Attack (1) -> Normal (0) in local training batches.",
                "Gaussian Noise Poisoning: Injects zero-mean Gaussian noise with high standard deviation to blow up model weights.",
                "Sign-Flipping Attack: Inverts the sign of weights (w -> -3.0 * w) to push the global model in the opposite direction.",
                "Model Scaling Attack: Multiplies weights by a large factor (e.g. 10x) so the adversary's update dominates the average."
            ]
        },
        "level_2_visualize": {
            "demo_type": "attack_vectors",
            "description": "Visualizing how honest vs sign-flipped vs Gaussian-noised weight vectors compare.",
            "explanation": "Honest updates form a cluster pointing toward lower loss. Sign-flipped updates point directly backward (180 degrees away), while Gaussian noise produces massive random vectors."
        },
        "level_3_math": {
            "equation": r"\text{Sign-Flip: } w_{\text{atk}} = \gamma \cdot w_{\text{honest}} \ (\gamma < 0), \quad \text{Gaussian: } w_{\text{atk}} = w_{\text{honest}} + \mathcal{N}(0, \sigma_{\text{atk}}^2 \mathbf{I})",
            "variables": [
                (r"\gamma", "Negative scaling factor (e.g. -3.0)"),
                (r"\sigma_{\text{atk}}", "Adversarial noise standard deviation (e.g. 2.5)"),
                ("w_{\text{honest}}", "The authentic weights that local training would have produced")
            ],
            "worked_example": "If honest gradient update is [0.4, -0.2], sign-flipping with gamma = -3.0 converts it to [-1.2, +0.6]. When averaged with honest updates, it cancels out honest learning and drags decision boundaries toward error."
        },
        "level_4_technical": {
            "pseudocode": """def apply_sign_flipping_attack(weights, scale=-3.0):
    return (scale * weights).astype(np.float32)

def apply_gaussian_noise_attack(weights, std=2.5, seed=None):
    noise = np.random.normal(0.0, std, size=weights.shape)
    return (weights + noise).astype(np.float32)""",
            "tradeoffs": "Sign-flipping does not necessarily blow up the L2 norm, making norm-only defenses blind to it. Conversely, Gaussian noise has random directions, making cosine similarity alone insufficient. A multi-criteria defense is required."
        },
        "level_5_quiz": [
            {
                "question": "Why is a sign-flipping attack particularly insidious against simple L2-norm threshold filters?",
                "options": ["Because sign-flipped updates have zero length", "Because inverting the signs does not necessarily increase the vector's length beyond normal bounds", "Because sign-flipping encrypts the vector", "Because sign-flipping requires supercomputers"],
                "correct": 1,
                "explanation": "If scaled moderately (e.g. -1.0 or -2.0), the L2 norm remains within typical thresholds, so a norm filter alone cannot catch it."
            }
        ],
        "how_it_works_in_system": {
            "source_files": ["src/attacks/model_poisoning.py", "src/attacks/data_poisoning.py"],
            "role": "Implements Gaussian noise, sign-flipping, model scaling, and label-flipping attacks injected on Node 3.",
            "action_link": "Section 2: Federated Learning & Defense Studio"
        }
    },

    "module_6": {
        "id": "module_6",
        "title": "Module 6: Multi-Criteria Trust & Reputation Management",
        "icon": "🛡️",
        "tagline": "Detecting malicious updates under Non-IID skew without false rejections",
        "level_1_understand": {
            "summary": "Single-metric filters fail in real networks. Norm checks miss sign-flipping; cosine checks falsely flag honest Non-IID nodes. Our system uses a 3-tier inspection engine combining Norm, Cosine Consensus, and Benchmark Loss Delta.",
            "analogy": "Airport security does not rely on a single check. They check your ticket (norm), compare your passport photo to your face (cosine similarity), and scan your luggage for prohibited items (validation loss). Only passengers who pass all three are admitted.",
            "why_it_matters": "In Non-IID networks, honest nodes specialize in different attacks, naturally producing diverse update directions. The validation loss check ensures specialized honest nodes are never falsely slashed.",
            "core_concepts": [
                "Tier 1: Dynamic L2-Norm Bounding (detects exploded Gaussian noise).",
                "Tier 2: Cosine Similarity to Peer Median (detects sign-flipping direction inversion).",
                "Tier 3: Non-IID Safe Validator Loss Delta (verifies whether applying candidate weights maintains classification sanity).",
                "Asymmetric Governance: Trust builds slowly (+0.05) and slashes severely (-0.35); quarantine triggers at R < 0.40."
            ]
        },
        "level_2_visualize": {
            "demo_type": "trust_radar",
            "description": "Interactive radar showing how candidate updates pass or fail the 3 criteria.",
            "explanation": "An honest update passes all 3 checks (green). A sign-flipped update fails the cosine check (red). A Gaussian attack fails the L2 norm check (red)."
        },
        "level_3_math": {
            "equation": r"\cos(\theta) = \frac{w_k \cdot w_{\text{med}}}{\|w_k\|_2 \|w_{\text{med}}\|_2} \ge \tau_{\cos}, \quad \|w_k\|_2 \le \tau_{\text{norm}} \cdot \|w_{\text{global}}\|_2, \quad \Delta L_k \le \tau_{\text{loss}}",
            "variables": [
                (r"w_{\text{med}}", "Coordinate-wise median vector of peer submissions (consensus direction)"),
                (r"\tau_{\cos}", "Cosine similarity threshold (default 0.15)"),
                (r"\tau_{\text{norm}}", "L2 norm factor threshold (default 2.5)"),
                (r"\Delta L_k", "Loss increase on balanced validation benchmark slice")
            ],
            "worked_example": "If Node 3 submits sign-flipped weights, its dot product with the peer median is strongly negative, yielding cos(theta) = -0.959. Since -0.959 < 0.15, Tier 2 fails immediately and the update is rejected."
        },
        "level_4_technical": {
            "pseudocode": """def evaluate_update(w_k, w_global, val_data):
    # Tier 1: Norm Bounding
    if norm(w_k) > 2.5 * norm(w_global): return REJECT("Norm exceeded")
    # Tier 2: Cosine to Peer Median
    cos_sim = dot(w_k, w_med) / (norm(w_k) * norm(w_med))
    if cos_sim < 0.15: return REJECT("Cosine similarity failed")
    # Tier 3: Validation Loss Delta
    loss_cand = compute_loss(w_k, val_data)
    if loss_cand - loss_baseline > 1.5: return REJECT("Loss exploded")
    return ACCEPT("Verified Honest")""",
            "tradeoffs": "Advantage: Zero false rejections of honest Non-IID nodes while capturing both noise and inversion attacks. Requirement: Requires maintaining a small, balanced validation benchmark slice at the server."
        },
        "level_5_quiz": [
            {
                "question": "Why is the validation loss delta check critical for defending Non-IID federated networks?",
                "options": ["To slow down the training process", "To verify that candidate weights maintain classification sanity, preventing honest specialized nodes from being falsely rejected", "To delete the test set", "To mine cryptocurrency"],
                "correct": 1,
                "explanation": "Because honest specialized nodes may produce unusual gradient angles, the loss delta check confirms whether their update is genuinely beneficial."
            }
        ],
        "how_it_works_in_system": {
            "source_files": ["src/trust/evaluator.py", "src/trust/reputation.py"],
            "role": "MultiCriteriaTrustEngine evaluates every submitted update; ReputationManager handles slashing, quarantine, and probation.",
            "action_link": "Section 3: Trust & Governance"
        }
    },

    "module_7": {
        "id": "module_7",
        "title": "Module 7: Blockchain & Cryptography",
        "icon": "⛓️",
        "tagline": "Tamper-evident audit ledger and cryptographic non-repudiation",
        "level_1_understand": {
            "summary": "In collaborative security, participants need proof of what was contributed and decided. Our platform integrates a tamper-evident audit ledger using SHA-256 block chaining, Merkle trees, and ECDSA digital signatures.",
            "analogy": "Imagine a public courtroom stenographer who records every statement into a bound ledger where each page includes a seal derived from the previous page. If anyone rips out a page or alters a word, the seal on every subsequent page breaks immediately.",
            "why_it_matters": "If a rogue participant submits a poisoned update, ECDSA signatures guarantee non-repudiation: they cannot claim someone else submitted it. The ledger permanently records the rejection and slashing.",
            "core_concepts": [
                "SHA-256 Hashing: 32-byte cryptographic fingerprint of model weights and block headers.",
                "ECDSA SECP256R1 Signatures: Proves update origin and ensures updates were not modified in transit.",
                "Merkle Trees: Hierarchical hash tree linking all round transactions into a single 32-byte root.",
                "Proof-of-Trust (PoT) Consensus: Proposer election rotating among highest-reputation honest nodes."
            ]
        },
        "level_2_visualize": {
            "demo_type": "merkle_builder",
            "description": "Interactive demonstration of binary Merkle tree root calculation from transaction hashes.",
            "explanation": "Four transaction hashes (Tx0, Tx1, Tx2, Tx3) are paired and hashed to form intermediate nodes H01 and H23, which are hashed together to form the unique Merkle Root."
        },
        "level_3_math": {
            "equation": r"H_{\text{block}} = \text{SHA256}\left(\text{index} \,\|\, H_{\text{prev}} \,\|\, \text{MerkleRoot} \,\|\, H_{\text{model}} \,\|\, \text{ValidatorID}\right)",
            "variables": [
                (r"H_{\text{block}}", "Unique 64-character hexadecimal block digest"),
                (r"H_{\text{prev}}", "Cryptographic hash of the parent block (enforces chain immutability)"),
                (r"\text{MerkleRoot}", "Single root hash representing all transactions in this block"),
                (r"H_{\text{model}}", "SHA-256 hash of the global model parameter vector")
            ],
            "worked_example": "If Block #1 has hash 'a3f8...', Block #2 must record previous_hash = 'a3f8...'. If an adversary retroactively modifies an update in Block #1, Block #1's hash changes to 'e91b...'. When verified, Block #2's previous_hash ('a3f8...') no longer matches, flagging ledger tampering immediately."
        },
        "level_4_technical": {
            "pseudocode": """def is_chain_valid(chain):
    for i = 1 to len(chain) - 1:
        curr = chain[i]
        prev = chain[i - 1]
        if curr.previous_hash != prev.hash: return False
        if curr.hash != calculate_hash(curr): return False
        if curr.merkle_root != calculate_merkle_root(curr.transactions): return False
    return True""",
            "tradeoffs": "Technical Reality: Our blockchain provides a tamper-evident, cryptographically verifiable audit ledger with centralized simulation orchestration. It simulates Proof-of-Trust consensus, but does NOT implement a physical peer-to-peer gossip network across separate physical hardware."
        },
        "level_5_quiz": [
            {
                "question": "What does an ECDSA digital signature prove about a model update?",
                "options": ["It proves the update is benign and contains no attacks", "It proves the update originated from the holder of the private key and was not altered in transit", "It proves the model will achieve 100% accuracy", "It encrypts the model weights so nobody can read them"],
                "correct": 1,
                "explanation": "Digital signatures guarantee authenticity, integrity, and non-repudiation. They do NOT prove the update is honest; malicious nodes sign their attacks too!"
            }
        ],
        "how_it_works_in_system": {
            "source_files": ["src/blockchain/crypto.py", "src/blockchain/block.py", "src/blockchain/chain.py"],
            "role": "Signs model updates with ECDSA, groups transactions into Merkle trees, selects PoT miners, and verifies ledger validity.",
            "action_link": "Section 4: Blockchain Audit"
        }
    },

    "module_8": {
        "id": "module_8",
        "title": "Module 8: Network Intrusion Detection Systems (IDS)",
        "icon": "🎯",
        "tagline": "Deep learning architectures and benchmarks for network defense",
        "level_1_understand": {
            "summary": "An Intrusion Detection System inspects network flow records (duration, protocol, byte counts, error rates) to classify traffic as benign or cyber-attacks. We train PyTorch neural networks on the benchmark NSL-KDD dataset.",
            "analogy": "An IDS acts like an intelligent border security checkpoint for computer networks. It inspects packet metadata—where it came from, how fast packets are arriving, whether connection handshakes failed—to flag hackers before they breach servers.",
            "why_it_matters": "Modern networks transfer gigabytes per second. Manual inspection is impossible; deep learning models can recognize complex, non-linear attack signatures in real time.",
            "core_concepts": [
                "NSL-KDD Benchmark: 125,973 train records, 22,544 test records, 122 normalized tabular features.",
                "Attack Taxonomy: Normal, Denial-of-Service (DoS), Probe (PortScan), Remote-to-Local (R2L), User-to-Root (U2R).",
                "Evaluation Metrics: Accuracy, Precision, Recall, Weighted F1-score, Confusion Matrix.",
                "Explainable AI (XAI): Gradient-based attribution (Input * Sensitivity) explaining WHY a flow was flagged."
            ]
        },
        "level_2_visualize": {
            "demo_type": "ids_classifier",
            "description": "Interactive flow classifier showing neural network activations and feature attributions.",
            "explanation": "When an incoming flow vector passes through the IDSNet MLP, the final softmax output yields class probabilities (e.g., 99.4% Attack)."
        },
        "level_3_math": {
            "equation": r"\text{Attribution}_i = \left| x_i \cdot \frac{\partial S_{\text{target}}}{\partial x_i} \right|, \quad \text{RelImportance}_i = \frac{\text{Attribution}_i}{\sum_j \text{Attribution}_j}",
            "variables": [
                ("x_i", "Normalized input value of network feature i"),
                (r"\frac{\partial S}{\partial x_i}", "Gradient of predicted class logit with respect to feature i"),
                (r"\text{RelImportance}_i", "Relative mathematical influence of feature i on the classification decision")
            ],
            "worked_example": "If a flow has serror_rate = 1.0 (SYN error) and its gradient sensitivity is 8.5, its attribution is 1.0 * 8.5 = 8.5. If duration = 0.0 with sensitivity 2.0, its attribution is 0.0 * 2.0 = 0.0. Feature attribution highlights serror_rate as the dominant reason for the intrusion verdict."
        },
        "level_4_technical": {
            "pseudocode": """class IDSNet(nn.Module):
    def __init__(self, input_dim=122, num_classes=2):
        self.feature_extractor = nn.Sequential(
            nn.Linear(input_dim, 128), nn.BatchNorm1d(128), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(128, 64), nn.BatchNorm1d(64), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(64, 32), nn.BatchNorm1d(32), nn.ReLU()
        )
        self.classifier = nn.Linear(32, num_classes)""",
            "tradeoffs": "Tabular neural networks require careful normalization (MinMax to [0,1]) and categorical dummy encoding. NSL-KDD has 41 raw columns expanding to 122 normalized numeric features after one-hot encoding."
        },
        "level_5_quiz": [
            {
                "question": "What is the primary advantage of Explainable AI (XAI) in a cybersecurity IDS?",
                "options": ["It increases network internet speed", "It provides security analysts with the mathematical reasons and packet features that triggered an intrusion alarm", "It deletes malicious packets automatically", "It replaces the neural network with a spreadsheet"],
                "correct": 1,
                "explanation": "XAI translates black-box neural network decisions into transparent feature attributions, allowing analysts to verify and respond to alerts."
            }
        ],
        "how_it_works_in_system": {
            "source_files": ["src/models/ids_net.py", "src/xai/explainer.py", "src/data/nsl_kdd.py"],
            "role": "Defines the PyTorch IDSNet neural network and FastFeatureExplainer for packet diagnosis.",
            "action_link": "Section 5: Research Intelligence"
        }
    },

    "module_9": {
        "id": "module_9",
        "title": "Module 9: Mathematical Foundations",
        "icon": "📐",
        "tagline": "The linear algebra, statistics, and optimization behind our defense",
        "level_1_understand": {
            "summary": "Federated learning and adversarial defense are built on three mathematical branches: linear algebra (vectors, norms, dot products), probability & statistics (Dirichlet and Gaussian distributions), and multivariable optimization (gradient descent).",
            "analogy": "Just as a structural engineer relies on physics equations to ensure a bridge does not collapse under wind, our cybersecurity framework relies on geometric vector math to ensure the collaborative model does not collapse under adversarial poisoning.",
            "why_it_matters": "Understanding the mathematics turns black-box AI into a predictable, verifiable engineering system.",
            "core_concepts": [
                "L2-Norm (Euclidean Length): Measures the magnitude of a parameter update vector.",
                "Cosine Similarity (Dot Product Projection): Measures the angular directional alignment between two vectors.",
                "Gaussian Normal Distribution: Bell-curved noise distribution parameterized by mean mu and standard deviation sigma.",
                "Cross-Entropy Loss: Loss function measuring divergence between predicted probabilities and true one-hot labels."
            ]
        },
        "level_2_visualize": {
            "demo_type": "vector_geometry",
            "description": "Interactive vector visualizer: observe dot product and angle theta between vectors.",
            "explanation": "When vectors point in the same direction, cos(theta) = 1.0. When orthogonal (90 degrees), cos(theta) = 0.0. When opposite (sign-flipped), cos(theta) = -1.0."
        },
        "level_3_math": {
            "equation": r"\|w\|_2 = \sqrt{\sum_{i=1}^D w_i^2}, \quad \cos(\theta) = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\|_2 \|\mathbf{v}\|_2} = \frac{\sum u_i v_i}{\sqrt{\sum u_i^2} \sqrt{\sum v_i^2}}",
            "variables": [
                (r"\|w\|_2", "L2 norm (Euclidean length) in D-dimensional space"),
                (r"\mathbf{u} \cdot \mathbf{v}", "Inner dot product between vectors u and v"),
                (r"\cos(\theta)", "Cosine of the angle between two vectors (-1.0 <= cos(theta) <= 1.0)")
            ],
            "worked_example": "Let u = [3, 4] and v = [6, 8]. Dot product = 3*6 + 4*8 = 18 + 32 = 50. Norm(u) = 5, Norm(v) = 10. Cos(theta) = 50 / (5 * 10) = 50/50 = 1.0 (perfect alignment). If v = [-3, -4], dot product = -25, Cos(theta) = -25 / (5 * 5) = -1.0 (exact sign-flip)."
        },
        "level_4_technical": {
            "pseudocode": """def vector_math(u, v):
    norm_u = np.sqrt(np.sum(u ** 2))
    norm_v = np.sqrt(np.sum(v ** 2))
    dot_product = np.sum(u * v)
    cos_sim = dot_product / (norm_u * norm_v + 1e-9)
    return norm_u, norm_v, cos_sim""",
            "tradeoffs": "High-dimensional geometry insight: In high dimensions (D = 25,000 parameters), random vectors are almost always orthogonal (cos(theta) ~ 0). Therefore, a strong negative cosine (cos(theta) < -0.8) is a definitive indicator of intentional sign-flipping."
        },
        "level_5_quiz": [
            {
                "question": "What is the cosine similarity between an honest update w and a sign-flipped update -3.0 * w?",
                "options": ["+1.0", "0.0", "-1.0", "+3.0"],
                "correct": 2,
                "explanation": "Because -3.0 * w points in the exact opposite direction, the angle theta is 180 degrees, and cos(180) = -1.0."
            }
        ],
        "how_it_works_in_system": {
            "source_files": ["src/trust/evaluator.py", "src/models/ids_net.py"],
            "role": "Forms the mathematical engine for L2-norm bounding and cosine similarity evaluation in MultiCriteriaTrustEngine.",
            "action_link": "Section 3: Trust & Governance"
        }
    }
}
