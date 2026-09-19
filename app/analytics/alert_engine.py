from typing import List, Dict, Any, Optional, Set
from app.config import settings

class GameTheoreticAlertEngine:
    """
    Game-Theoretic Alert Prioritization Engine for Defense Welfare.
    
    Models:
    1. Welfare Officer attention as a strictly bounded scarce resource (Capacity C).
    2. Personnel reporting behavior as strategic / noisy signals (stigma under-reporting vs noisy spikes).
    3. Life-Safety Crisis Override: Bypasses algorithmic queue for acute self-harm indicators.
    4. Optimization: Maximize expected force welfare while penalizing false-positive stigmatization.
    """
    def __init__(
        self,
        officer_capacity: int = settings.OFFICER_WEEKLY_CAPACITY,
        u_intervene: float = settings.TRUE_POSITIVE_GAIN,
        c_stigma: float = settings.STIGMA_PENALTY_WEIGHT,
        c_fatigue: float = 0.25
    ):
        self.capacity_c = officer_capacity
        self.u_intervene = u_intervene
        self.c_stigma = c_stigma
        self.c_fatigue = c_fatigue

    def evaluate_personnel_signal(
        self,
        pseudo_id: str,
        risk_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculates strategic signal state, Bayesian true distress probability,
        and expected intervention utility.
        """
        # 0. CHECK CRISIS HARD-OVERRIDE (Ethical Non-Negotiable: Algorithms must never delay life safety)
        if risk_data.get("is_crisis_override"):
            return {
                "pseudo_id": pseudo_id,
                "composite_risk": 1.0,
                "operational_subscore": 1.0,
                "psychometric_subscore": 1.0,
                "signal_archetype": "CRISIS_IMMEDIATE_OVERRIDE",
                "strategic_rationale": (
                    f"ACUTE CRISIS DISPATCH: {risk_data.get('crisis_reason')} "
                    "Algorithm bypassed: immediate confidential welfare officer contact mandated."
                ),
                "p_true_distress": 1.0,
                "expected_utility": 999.0,  # Unconditionally forces top rank
                "is_crisis": True,
                "attributions": risk_data.get("attributions", {})
            }

        op = risk_data["operational_subscore"]
        psy = risk_data["psychometric_subscore"]
        composite = risk_data["composite_risk_score"]

        # 1. Detect Strategic Persona / Signaling Distortion
        if op >= 0.55 and psy <= 0.30:
            # Case: Stigma-masked under-reporting (High hardship, hides distress to protect weapon/career)
            signal_archetype = "STIGMA_MASKED_DISTRESS"
            # Bayesian update: objective operational burden is high; boost true distress probability
            p_true_distress = min(0.95, (op * 0.70) + (psy * 0.30) + 0.25)
            strategic_rationale = (
                "Strategic Under-Reporting Detected: Severe operational stressors present "
                "(deployment/leave deficit) but suppressed self-report, indicating career stigma anxiety."
            )
        elif psy >= 0.50 and op <= 0.25:
            # Case: Noisy / gaming / transient spike (Complaints without operational corroboration)
            signal_archetype = "NOISY_UNSUBSTANTIATED"
            # Bayesian update: discount due to lack of objective operational stressors
            p_true_distress = max(0.15, (psy * 0.35) + (op * 0.65))
            strategic_rationale = (
                "Strategic Noise / Low Corroboration: Elevated self-report without corresponding "
                "operational hardship. Prioritization lowered to prevent welfare officer fatigue."
            )
        elif op >= 0.50 and psy >= 0.50:
            # Case: Authentic high distress with full corroboration
            signal_archetype = "AUTHENTIC_HIGH_DISTRESS"
            p_true_distress = min(0.99, (op * 0.50) + (psy * 0.50) + 0.10)
            strategic_rationale = (
                "Authentic Multi-Factor Distress: Self-report is strongly corroborated by "
                "severe operational deployment metrics."
            )
        else:
            signal_archetype = "BASELINE_EQUILIBRIUM"
            p_true_distress = composite
            strategic_rationale = "Signals within standard operational variance."

        p_true_distress = round(p_true_distress, 4)

        # 2. Game-Theoretic Expected Utility Calculation:
        # EU = P(True Distress) * U_gain - (1 - P(True Distress)) * Cost_stigma - Cost_fatigue
        expected_utility = (
            p_true_distress * self.u_intervene -
            (1.0 - p_true_distress) * self.c_stigma -
            self.c_fatigue
        )
        expected_utility = round(expected_utility, 3)

        return {
            "pseudo_id": pseudo_id,
            "composite_risk": composite,
            "operational_subscore": op,
            "psychometric_subscore": psy,
            "signal_archetype": signal_archetype,
            "strategic_rationale": strategic_rationale,
            "p_true_distress": p_true_distress,
            "expected_utility": expected_utility,
            "is_crisis": False,
            "attributions": risk_data.get("attributions", {})
        }

    def prioritize_cohort_alerts(
        self, 
        evaluations: List[Dict[str, Any]],
        resolved_pseudo_ids: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """
        Ranks alerts by Expected Game-Theoretic Utility subject to bounded officer capacity C.
        Crisis overrides bypass queue to top.
        Resolved cases are filtered out to keep queue stateful.
        """
        resolved_set = resolved_pseudo_ids or set()
        
        # Filter out resolved cases
        active_evals = [e for e in evaluations if e["pseudo_id"] not in resolved_set]
        
        # Sort by expected utility descending (Crisis overrides have utility 999.0)
        ranked = sorted(active_evals, key=lambda x: x["expected_utility"], reverse=True)

        allocated_alerts = []
        deferred_alerts = []

        for idx, alert in enumerate(ranked):
            item = dict(alert)
            item["priority_rank"] = idx + 1
            
            # Crisis override is ALWAYS allocated regardless of capacity limits
            if item.get("is_crisis"):
                item["allocation_status"] = "CRISIS_DISPATCH_IMMEDIATE"
                item["action_urgency"] = "CRITICAL_ACTION_REQUIRED"
                allocated_alerts.append(item)
            elif len(allocated_alerts) < self.capacity_c and item["expected_utility"] > 0.0:
                item["allocation_status"] = "ALLOCATED_FOR_INTERVENTION"
                item["action_urgency"] = "IMMEDIATE_ACTION" if idx < 3 else "SCHEDULED_REVIEW"
                allocated_alerts.append(item)
            else:
                item["allocation_status"] = "DEFERRED_MONITORING"
                item["action_urgency"] = "MONITOR_TREND"
                deferred_alerts.append(item)

        total_cases = len(active_evals)
        capacity_utilization = round((len(allocated_alerts) / max(1, self.capacity_c)) * 100.0, 1)

        return {
            "officer_capacity_c": self.capacity_c,
            "allocated_count": len(allocated_alerts),
            "deferred_count": len(deferred_alerts),
            "resolved_count": len(resolved_set),
            "total_cohort_evaluated": total_cases,
            "capacity_utilization_pct": min(100.0, capacity_utilization),
            "allocated_alerts": allocated_alerts,
            "deferred_alerts": deferred_alerts
        }

alert_engine = GameTheoreticAlertEngine()
