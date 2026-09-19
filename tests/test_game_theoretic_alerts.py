import pytest
from app.analytics.risk_model import calculate_stress_risk
from app.analytics.alert_engine import alert_engine

def test_genuine_distress_prioritized_over_noisy_complaints():
    p1_risk = calculate_stress_risk(
        phq4_score=9.0,
        mood_score=2.5,
        sleep_hours=3.5,
        stress_rating=9.2,
        days_since_leave=210,
        denied_leaves=2,
        deployment_hardship=4.8,
        night_shifts_ratio=0.65,
        sentiment_polarity=-0.82
    )
    p1_eval = alert_engine.evaluate_personnel_signal("PX-7821", p1_risk)

    p2_risk = calculate_stress_risk(
        phq4_score=10.0,
        mood_score=3.0,
        sleep_hours=7.5,
        stress_rating=8.5,
        days_since_leave=22,
        denied_leaves=0,
        deployment_hardship=1.2,
        night_shifts_ratio=0.10,
        sentiment_polarity=-0.45
    )
    p2_eval = alert_engine.evaluate_personnel_signal("PX-4409", p2_risk)

    assert p1_eval["signal_archetype"] == "AUTHENTIC_HIGH_DISTRESS"
    assert p2_eval["signal_archetype"] == "NOISY_UNSUBSTANTIATED"
    assert p1_eval["expected_utility"] > p2_eval["expected_utility"]
    assert p1_eval["p_true_distress"] > p2_eval["p_true_distress"]

def test_stigma_masked_under_reporting_detection():
    p3_risk = calculate_stress_risk(
        phq4_score=1.0,
        mood_score=8.5,
        sleep_hours=4.0,
        stress_rating=2.0,
        days_since_leave=195,
        denied_leaves=3,
        deployment_hardship=4.6,
        night_shifts_ratio=0.70,
        sentiment_polarity=0.10
    )
    p3_eval = alert_engine.evaluate_personnel_signal("PX-1290", p3_risk)

    assert p3_eval["signal_archetype"] == "STIGMA_MASKED_DISTRESS"
    assert p3_eval["p_true_distress"] > 0.60

def test_crisis_hard_override_bypasses_ranking():
    # Personnel with acute suicide / self-harm indication in reflection
    crisis_risk = calculate_stress_risk(
        phq4_score=8.0,
        mood_score=2.0,
        sleep_hours=2.0,
        stress_rating=10.0,
        days_since_leave=40,
        denied_leaves=0,
        deployment_hardship=2.0,
        night_shifts_ratio=0.2,
        sentiment_polarity=-0.9,
        reflection_text="I feel completely hopeless and want to commit suicide."
    )
    assert crisis_risk["is_crisis_override"] is True
    assert crisis_risk["risk_tier"] == "CRITICAL"

    crisis_eval = alert_engine.evaluate_personnel_signal("PX-CRISIS-99", crisis_risk)
    assert crisis_eval["is_crisis"] is True
    assert crisis_eval["expected_utility"] == 999.0
    assert crisis_eval["signal_archetype"] == "CRISIS_IMMEDIATE_OVERRIDE"

    # In cohort prioritization, crisis alert must be at Rank #1 unconditionally
    prioritized = alert_engine.prioritize_cohort_alerts([crisis_eval])
    assert prioritized["allocated_alerts"][0]["pseudo_id"] == "PX-CRISIS-99"
    assert prioritized["allocated_alerts"][0]["allocation_status"] == "CRISIS_DISPATCH_IMMEDIATE"

def test_stateful_resolved_case_filtering():
    evals = []
    for i in range(5):
        risk = {
            "operational_subscore": 0.5,
            "psychometric_subscore": 0.5,
            "composite_risk_score": 0.5,
            "attributions": {"test": 100.0}
        }
        evals.append(alert_engine.evaluate_personnel_signal(f"PX-CASE-{i}", risk))

    # Mark PX-CASE-0 as resolved
    result = alert_engine.prioritize_cohort_alerts(evals, resolved_pseudo_ids={"PX-CASE-0"})
    pseudo_in_queue = [a["pseudo_id"] for a in result["allocated_alerts"]]
    assert "PX-CASE-0" not in pseudo_in_queue
    assert result["resolved_count"] == 1
