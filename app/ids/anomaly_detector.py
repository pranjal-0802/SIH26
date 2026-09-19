import time
from typing import Optional, Tuple, Dict, List
from collections import defaultdict

class AccessPatternIDS:
    """
    Real-time Access-Pattern Intrusion Detection System (IDS).
    Monitors data access patterns, velocity, and scope adherence.
    """
    def __init__(self):
        # Sliding window query timestamps: actor_id -> list of float timestamps
        self._query_history: Dict[str, List[float]] = defaultdict(list)
        # Sliding window re-identification counts: actor_id -> list of timestamps
        self._reid_history: Dict[str, List[float]] = defaultdict(list)
        
        # Configuration thresholds
        self.VELOCITY_WINDOW_SECONDS = 10.0
        self.MAX_QUERIES_PER_WINDOW = 12
        self.MAX_REIDENTIFICATIONS_PER_HOUR = 3

    def inspect_access(
        self,
        actor_id: str,
        actor_role: str,
        assigned_battalion: Optional[str],
        target_battalion: Optional[str],
        action: str,
        endpoint: str
    ) -> Tuple[bool, float, str]:
        """
        Evaluates an access attempt against zero-trust policy baselines.
        Returns: (is_threat: bool, anomaly_score: float, reason: str)
        """
        now = time.time()
        
        # 1. SCOPE VIOLATION: Welfare Officer attempting cross-unit access
        if actor_role.lower() == "welfare_officer" and target_battalion:
            if assigned_battalion and assigned_battalion != target_battalion:
                return (
                    True, 
                    0.98, 
                    f"CROSS_BATTALION_INTRUSION: Welfare Officer assigned to '{assigned_battalion}' attempted unauthorized access to '{target_battalion}'."
                )

        # 2. PRIVILEGE & SCOPE PROBE: Commander queries
        if actor_role.lower() == "commander":
            # 2a. Probing individual records
            if "personnel" in endpoint.lower() and "aggregate" not in endpoint.lower():
                return (
                    True,
                    0.99,
                    "COMMANDER_PROBE_VIOLATION: Commander attempted individual-level query pathway."
                )
            # 2b. IDOR check: querying outside assigned battalion without corps-level authority
            if target_battalion and assigned_battalion and assigned_battalion not in ("CORPS_COMMAND", "THEATER_HQ"):
                if assigned_battalion != target_battalion:
                    return (
                        True,
                        0.96,
                        f"COMMANDER_IDOR_VIOLATION: Commander assigned to '{assigned_battalion}' attempted unauthorized cross-unit aggregation on '{target_battalion}'."
                    )

        # 3. VELOCITY SPIKE DETECTION (Automated Scraping / Bulk Harvest)
        history = self._query_history[actor_id]
        # Prune old queries
        cutoff = now - self.VELOCITY_WINDOW_SECONDS
        history = [t for t in history if t > cutoff]
        history.append(now)
        self._query_history[actor_id] = history
        
        if len(history) > self.MAX_QUERIES_PER_WINDOW:
            score = min(0.95, 0.70 + (len(history) - self.MAX_QUERIES_PER_WINDOW) * 0.05)
            return (
                True,
                score,
                f"VELOCITY_BURST_DETECTED: {len(history)} queries in {self.VELOCITY_WINDOW_SECONDS}s (Threshold: {self.MAX_QUERIES_PER_WINDOW})."
            )

        # 4. RE-IDENTIFICATION VELOCITY ANOMALY
        if action == "BREAK_GLASS_REIDENTIFY":
            reid_list = self._reid_history[actor_id]
            reid_cutoff = now - 3600.0
            reid_list = [t for t in reid_list if t > reid_cutoff]
            reid_list.append(now)
            self._reid_history[actor_id] = reid_list
            
            if len(reid_list) > self.MAX_REIDENTIFICATIONS_PER_HOUR:
                return (
                    True,
                    0.92,
                    f"REIDENTIFICATION_SPIKE: {len(reid_list)} break-glass attempts within 1 hour."
                )

        # Baseline benign event
        return (False, 0.05, "NORMAL: Access within authorized operational bounds.")

# Singleton IDS instance
ids_engine = AccessPatternIDS()

