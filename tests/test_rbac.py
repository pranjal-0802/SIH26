import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token

client = TestClient(app)

def test_personnel_cannot_access_welfare_alerts():
    token = create_access_token(subject="rajesh_kumar", role="personnel", pseudo_id="PX-7821")
    response = client.get(
        "/api/v1/welfare/alerts",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
    assert "Access denied" in response.json()["detail"]

def test_commander_cannot_access_welfare_alerts():
    token = create_access_token(subject="cmd_singh", role="commander", assigned_battalion="104-CRPF")
    response = client.get(
        "/api/v1/welfare/alerts",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403

def test_admin_cannot_access_clinical_telemetry():
    token = create_access_token(subject="sec_admin", role="admin")
    response = client.get(
        "/api/v1/welfare/alerts",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403

def test_welfare_officer_can_access_assigned_cohort():
    token = create_access_token(subject="welfare_sharma", role="welfare_officer", assigned_battalion="104-CRPF")
    response = client.get(
        "/api/v1/welfare/alerts",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "allocated_alerts" in data
    assert data["battalion"] == "104-CRPF"
