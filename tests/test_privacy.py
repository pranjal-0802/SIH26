import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token
from app.analytics.privacy import apply_k_anonymity_guard, add_laplace_noise, sanitize_cohort_aggregate, dp_budget_tracker
from app.config import settings

def test_k_anonymity_guard_logic():
    small_cohort = ["p1", "p2", "p3", "p4"]
    result_small = apply_k_anonymity_guard(small_cohort, min_k=5)
    assert result_small["suppressed"] is True
    assert result_small["data"] is None

    valid_cohort = ["p1", "p2", "p3", "p4", "p5"]
    result_valid = apply_k_anonymity_guard(valid_cohort, min_k=5)
    assert result_valid["suppressed"] is False
    assert len(result_valid["data"]) == 5

def test_differential_privacy_noise():
    true_val = 50.0
    noisy_samples = [add_laplace_noise(true_val, sensitivity=1.0, epsilon=0.5) for _ in range(50)]
    
    assert any(n != true_val for n in noisy_samples)
    mean_val = sum(noisy_samples) / len(noisy_samples)
    assert abs(mean_val - true_val) < 2.0

def test_dp_budget_exhaustion_graceful_degradation():
    # Exhaust budget for a dummy cohort
    cohort_tag = "TEST-DP-COHORT"
    dp_budget_tracker._expenditures[cohort_tag] = []
    
    # Consume entire budget
    for _ in range(15):
        dp_budget_tracker.check_and_consume_budget(cohort_tag, 1.0)
        
    metrics = {"avg_stress": 55.0, "leave_deficit": 40.0}
    res = sanitize_cohort_aggregate(metrics, cohort_size=10, battalion_code=cohort_tag)
    
    # Under graceful degradation, query is not blocked; it applies extra noise
    assert res["status"] == "ANONYMIZED_COMPLIANT"
    assert res["dp_budget_status"] == "BUDGET_EXHAUSTED_EXTRA_NOISE"
    assert res["metrics"] is not None

def test_commander_endpoint_requires_totp_mfa(client):
    token = create_access_token(subject="cmd_singh", role="commander", assigned_battalion="104-CRPF")
    
    # Missing X-TOTP-Code header
    res_no_totp = client.get(
        "/api/v1/commander/cohort-readiness?target_battalion=104-CRPF",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_no_totp.status_code == 403
    assert "Multi-Factor Authentication Required" in res_no_totp.json()["detail"]

def test_commander_endpoint_k_anonymity_suppression(client):
    token = create_access_token(subject="cmd_singh", role="commander", assigned_battalion="104-CRPF")
    headers = {"Authorization": f"Bearer {token}", "X-TOTP-Code": "123456"}
    
    # 1. Query large cohort (104-CRPF, size >= 5)
    res_large = client.get(
        "/api/v1/commander/cohort-readiness?target_battalion=104-CRPF",
        headers=headers
    )
    assert res_large.status_code == 200
    assert res_large.json()["status"] == "ANONYMIZED_COMPLIANT"
    assert "strategic_metrics" in res_large.json()
    assert "dp_budget_status" in res_large.json()

    # 2. Query small cohort (88-ITBP, size 3 < 5) via authorized commander cmd_itbp
    token_itbp = create_access_token(subject="cmd_itbp", role="commander", assigned_battalion="88-ITBP")
    res_small = client.get(
        "/api/v1/commander/cohort-readiness?target_battalion=88-ITBP",
        headers={"Authorization": f"Bearer {token_itbp}", "X-TOTP-Code": "123456"}
    )
    assert res_small.status_code == 200
    assert res_small.json()["status"] == "SUPPRESSED"
    assert "below the minimum privacy threshold" in res_small.json()["message"]
    assert res_small.json()["metrics"] is None
