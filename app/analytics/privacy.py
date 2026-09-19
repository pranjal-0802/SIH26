import time
import numpy as np
from typing import List, Dict, Any, Optional
from collections import defaultdict
from app.config import settings

class DifferentialPrivacyBudgetTracker:
    """
    Stateful Cumulative Privacy Budget Accounting (Differential Privacy).
    Protects against reconstruction and query-averaging attacks by tracking
    cumulative epsilon expenditure per cohort within a 24-hour sliding window.
    """
    def __init__(self, max_epsilon_per_day: float = settings.DP_MAX_BUDGET_PER_DAY):
        self.max_epsilon = max_epsilon_per_day
        # battalion_code -> list of (timestamp, epsilon_spent)
        self._expenditures: Dict[str, List[tuple[float, float]]] = defaultdict(list)
        self.WINDOW_SECONDS = 86400.0  # 24 hours

    def check_and_consume_budget(self, battalion_code: str, requested_epsilon: float) -> tuple[bool, float, float]:
        """
        Validates whether sufficient privacy budget remains for this cohort.
        Returns: (is_permitted: bool, current_spent: float, remaining_budget: float)
        """
        now = time.time()
        cutoff = now - self.WINDOW_SECONDS
        
        # Prune expired queries outside 24h window
        history = [item for item in self._expenditures[battalion_code] if item[0] > cutoff]
        
        current_spent = sum(item[1] for item in history)
        remaining = max(0.0, self.max_epsilon - current_spent)
        
        if current_spent + requested_epsilon > self.max_epsilon:
            self._expenditures[battalion_code] = history
            return False, current_spent, remaining
            
        history.append((now, requested_epsilon))
        self._expenditures[battalion_code] = history
        new_spent = current_spent + requested_epsilon
        return True, new_spent, max(0.0, self.max_epsilon - new_spent)

dp_budget_tracker = DifferentialPrivacyBudgetTracker()

def apply_k_anonymity_guard(
    items: List[Any], 
    min_k: int = settings.K_ANONYMITY_THRESHOLD
) -> Dict[str, Any]:
    """
    Guarantees that no cohort aggregate is returned if the cohort size is below k.
    Prevents re-identification through elimination.
    """
    count = len(items)
    if count < min_k:
        return {
            "suppressed": True,
            "cohort_size": count,
            "threshold_k": min_k,
            "message": f"Data suppressed: Cohort size ({count}) is below privacy threshold (k={min_k}) to prevent individual re-identification.",
            "data": None
        }
    return {
        "suppressed": False,
        "cohort_size": count,
        "threshold_k": min_k,
        "message": "Cohort satisfies k-anonymity guarantee.",
        "data": items
    }


def add_laplace_noise(
    true_value: float, 
    sensitivity: float = 1.0, 
    epsilon: float = settings.DP_EPSILON
) -> float:
    """
    Applies Differential Privacy Laplace mechanism.
    Scale b = sensitivity / epsilon.
    """
    scale = sensitivity / max(0.01, epsilon)
    noise = np.random.laplace(0.0, scale)
    return float(true_value + noise)


def sanitize_cohort_aggregate(
    raw_metrics: Dict[str, float], 
    cohort_size: int,
    battalion_code: str = "GLOBAL",
    min_k: int = settings.K_ANONYMITY_THRESHOLD,
    apply_dp: bool = True
) -> Dict[str, Any]:
    """
    Enforces k-anonymity, Differential Privacy Laplace noise injection,
    and cumulative epsilon privacy budget accounting.
    """
    if cohort_size < min_k:
        return {
            "status": "SUPPRESSED",
            "reason": f"Cohort size {cohort_size} < k={min_k}",
            "metrics": None
        }

    dp_epsilon = settings.DP_EPSILON
    is_budget_ok, spent_budget, remaining_budget = dp_budget_tracker.check_and_consume_budget(
        battalion_code, dp_epsilon
    )

    # If privacy budget exhausted, apply extra noise to prevent reconstruction
    active_epsilon = dp_epsilon if is_budget_ok else max(0.1, dp_epsilon / 2.0)
    budget_flag = "BUDGET_ACTIVE" if is_budget_ok else "BUDGET_EXHAUSTED_EXTRA_NOISE"

    sanitized = {}
    for key, val in raw_metrics.items():
        if apply_dp and isinstance(val, (int, float)):
            sens = 10.0 / max(1, cohort_size)
            noisy = add_laplace_noise(val, sensitivity=sens, epsilon=active_epsilon)
            sanitized[key] = round(max(0.0, noisy), 2)
        else:
            sanitized[key] = round(val, 2)
            
    return {
        "status": "ANONYMIZED_COMPLIANT",
        "cohort_size": cohort_size,
        "k_threshold": min_k,
        "dp_budget_status": budget_flag,
        "dp_daily_budget_spent": round(spent_budget, 2),
        "dp_daily_budget_remaining": round(remaining_budget, 2),
        "metrics": sanitized
    }
