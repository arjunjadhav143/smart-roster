import os
os.environ["DATABASE_URL"]="sqlite:///./test_roster.db"
from fastapi.testclient import TestClient
from app.main import app
def test_health_and_seeded_data():
 c=TestClient(app); assert c.get("/health").status_code==200; assert len(c.get("/employees").json())>=30
def test_generation_and_leave_never_worked():
 c=TestClient(app); out=c.post("/rosters/generate",json={"year":2026,"month":11}).json(); assert out["solver_status"] in ["FEASIBLE","INFEASIBLE"]
 if out["solver_status"]=="FEASIBLE":
  entries=c.get(f"/rosters/{out['id']}/entries").json(); assert not any(e["employee_id"]==1 and str(e["work_date"])=="2026-11-08" and e["status"]=="working" for e in entries)

def test_validator_detects_required_process_with_no_entries():
 c=TestClient(app)
 out=c.post("/rosters/generate",json={"year":2027,"month":1}).json()
 if out["solver_status"]=="FEASIBLE":
  entries=c.get(f"/rosters/{out['id']}/entries").json()
  victim=next(e for e in entries if e["status"]=="working")
  c.put(f"/rosters/{out['id']}/entries/{victim['id']}",json={"status":"not_assigned"})
  report=c.post(f"/rosters/{out['id']}/validate").json()
  assert report["valid"] is False
  assert any(x["type"] in ("UNASSIGNED_REQUIRED_PROCESS","COVERAGE_SHORTAGE") for x in report["conflicts"])
