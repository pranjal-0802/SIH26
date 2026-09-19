import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token

client = TestClient(app)

def test_ids_catches_welfare_cross_battalion_snoop():
    token = create_access_token(
        subject="welfare_rogue",
        role="welfare_officer",
        assigned_battalion="42-BSF"
    )

    response = client.get(
        "/api/v1/welfare/alerts?target_battalion=104-CRPF",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403
    detail = response.json()["detail"]
    assert "CROSS_BATTALION_INTRUSION" in detail or "Security Alert" in detail

def test_ids_catches_commander_idor_snoop():
    # Commander assigned to 104-CRPF attempts unauthorized aggregation on 42-BSF
    token = create_access_token(
        subject="cmd_singh",
        role="commander",
        assigned_battalion="104-CRPF"
    )

    response = client.get(
        "/api/v1/commander/cohort-readiness?target_battalion=42-BSF",
        headers={"Authorization": f"Bearer {token}", "X-TOTP-Code": "123456"}
    )

    assert response.status_code == 403
    detail = response.json()["detail"]
    assert "COMMANDER_IDOR_VIOLATION" in detail or "Security Alert" in detail

def test_ids_alerts_endpoint_records_intrusion():
    admin_token = create_access_token(subject="sec_admin", role="admin")
    response = client.get(
        "/api/v1/admin/ids-alerts",
        headers={"Authorization": f"Bearer {admin_token}", "X-TOTP-Code": "123456"}
    )

    assert response.status_code == 200
    alerts = response.json()["alerts"]
    assert len(alerts) > 0
    rogue_logs = [a for a in alerts if "welfare_rogue" in a["actor_id"] or a["anomaly_score"] >= 0.9]
    assert len(rogue_logs) > 0
