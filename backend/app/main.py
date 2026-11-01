from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from .database import Base,engine,get_db,SessionLocal
from .settings import settings
from .models import *
from .schemas import *
from .seed import seed
from .services.roster_engine import generate
from .services.conflict_detector import validate

Base.metadata.create_all(bind=engine)
with SessionLocal() as db: seed(db)
app=FastAPI(title="Smart Roster Management API",version="1.0.0")
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in settings.cors_origins.split(",")],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
def one(db,model,id):
 o=db.get(model,id)
 if not o: raise HTTPException(404,"Record not found")
 return o
@app.get("/health")
def health(): return {"status":"ok"}
@app.get("/dashboard")
def dashboard(db:Session=Depends(get_db)):
 today=date.today(); roster=db.query(Roster).filter_by(year=today.year,month=today.month).first()
 return {"total_employees":db.query(Employee).filter_by(active=True).count(),"total_brands":db.query(Brand).filter_by(active=True).count(),"total_pods":db.query(Pod).count(),"total_processes":db.query(Process).count(),"employees_working_today":db.query(RosterEntry).filter_by(roster_id=roster.id if roster else -1,work_date=today,status="working").count(),"employees_on_leave_today":db.query(LeaveRequest).filter(LeaveRequest.status=="approved",LeaveRequest.start_date<=today,LeaveRequest.end_date>=today).count(),"coverage_gaps":db.query(SchedulingConflict).filter_by(status="open",conflict_type="coverage_gap").count(),"pending_roster_approvals":db.query(Roster).filter_by(status="draft").count()}
@app.get("/employees")
def list_employees(q:str="",pod_id:int|None=None,db:Session=Depends(get_db)):
 query=db.query(Employee).filter(Employee.full_name.ilike(f"%{q}%"))
 if pod_id: query=query.filter_by(pod_id=pod_id)
 return [{"id":e.id,"employee_code":e.employee_code,"full_name":e.full_name,"email":e.email,"pod_id":e.pod_id,"pod":e.pod.name if e.pod else None,"active":e.active,"weekly_off_days":e.weekly_off_days} for e in query.all()]
@app.post("/employees",status_code=201)
def create_employee(data:EmployeeIn,db:Session=Depends(get_db)): o=Employee(**data.model_dump());db.add(o);db.commit();db.refresh(o);return {"id":o.id}
@app.put("/employees/{id}")
def update_employee(id:int,data:EmployeeIn,db:Session=Depends(get_db)): o=one(db,Employee,id);[setattr(o,k,v) for k,v in data.model_dump().items()];db.commit();return {"id":id}
@app.delete("/employees/{id}")
def deactivate_employee(id:int,db:Session=Depends(get_db)): o=one(db,Employee,id);o.active=False;db.commit();return {"status":"deactivated"}
@app.get("/pods")
def pods(db:Session=Depends(get_db)): return [{"id":p.id,"name":p.name,"employee_count":db.query(Employee).filter_by(pod_id=p.id,active=True).count()} for p in db.query(Pod).all()]
@app.post("/pods")
def create_pod(name:str,db:Session=Depends(get_db)): o=Pod(name=name);db.add(o);db.commit();db.refresh(o);return o
@app.get("/brands")
def brands(db:Session=Depends(get_db)): return [{"id":b.id,"name":b.name,"description":b.description,"active":b.active,"process_count":len(b.processes)} for b in db.query(Brand).all()]
@app.post("/brands")
def create_brand(data:BrandIn,db:Session=Depends(get_db)): o=Brand(**data.model_dump());db.add(o);db.commit();db.refresh(o);return o
@app.get("/processes")
def processes(brand_id:int|None=None,db:Session=Depends(get_db)):
 q=db.query(Process);
 if brand_id:q=q.filter_by(brand_id=brand_id)
 return [{"id":p.id,"brand_id":p.brand_id,"brand":p.brand.name,"name":p.name,"minimum_staff":p.minimum_staff,"working_days":p.working_days,"shift":p.shift} for p in q.all()]
@app.post("/processes")
def create_process(data:ProcessIn,db:Session=Depends(get_db)): o=Process(**data.model_dump());db.add(o);db.commit();db.refresh(o);return o
@app.get("/assignments")
def assignments(db:Session=Depends(get_db)): return [{"id":a.id,"employee_id":a.employee_id,"employee":a.employee.full_name,"process_id":a.process_id,"process":a.process.name,"brand":a.process.brand.name,"qualified":a.qualified} for a in db.query(EmployeeAssignment).all()]
@app.post("/assignments")
def create_assignment(data:AssignmentIn,db:Session=Depends(get_db)): o=EmployeeAssignment(**data.model_dump());db.add(o);db.commit();db.refresh(o);return o
@app.get("/leaves")
def leaves(db:Session=Depends(get_db)): return [{"id":x.id,"employee_id":x.employee_id,"start_date":x.start_date,"end_date":x.end_date,"leave_type":x.leave_type,"status":x.status} for x in db.query(LeaveRequest).all()]
@app.post("/leaves")
def create_leave(data:LeaveIn,db:Session=Depends(get_db)): o=LeaveRequest(**data.model_dump());db.add(o);db.commit();db.refresh(o);return o
@app.post("/leaves/{id}/approve")
def approve_leave(id:int,db:Session=Depends(get_db)): o=one(db,LeaveRequest,id);o.status="approved";db.commit();return {"status":"approved"}
@app.post("/rosters/generate")
def generate_roster(data:GenerateIn,db:Session=Depends(get_db)):
 old=db.query(Roster).filter_by(year=data.year,month=data.month).first()
 if old: db.delete(old);db.commit()
 roster=Roster(year=data.year,month=data.month,status="draft");db.add(roster);db.flush()
 rows,issues,status=generate(db,data.year,data.month,data.pod_id);roster.solver_status=status
 if status=="INFEASIBLE":
  roster.status="infeasible"
  db.commit()
  # Keep the generation response shape stable for consumers and tests.  An
  # infeasible solve is a valid solver result, not an API error.
  return {"id":roster.id,"status":"infeasible","solver_status":status,"issues":issues}
 db.add_all([RosterEntry(roster_id=roster.id,employee_id=e,process_id=p,work_date=d,status=s,shift=sh) for e,p,d,s,sh in rows]);db.commit(); conflicts=validate(db,roster)
 return {"id":roster.id,"status":roster.status,"solver_status":status,"entries":len(rows),"conflicts":len(conflicts)}
@app.get("/rosters")
def rosters(db:Session=Depends(get_db)): return [{"id":r.id,"year":r.year,"month":r.month,"status":r.status,"solver_status":r.solver_status,"entry_count":len(r.entries)} for r in db.query(Roster).order_by(Roster.year.desc(),Roster.month.desc()).all()]
@app.get("/rosters/{id}/entries")
def roster_entries(id:int,db:Session=Depends(get_db)): return [{"id":e.id,"employee_id":e.employee_id,"employee":e.employee.full_name,"process_id":e.process_id,"process":e.process.name if e.process else None,"brand":e.process.brand.name if e.process else None,"work_date":e.work_date,"status":e.status,"shift":e.shift} for e in one(db,Roster,id).entries]
@app.put("/rosters/{id}/entries/{entry_id}")
def edit_entry(id:int,entry_id:int,data:EntryEdit,db:Session=Depends(get_db)):
 e=one(db,RosterEntry,entry_id)
 if e.roster_id!=id: raise HTTPException(400,"Entry does not belong to roster")
 for k,v in data.model_dump(exclude_none=True).items():setattr(e,k,v)
 db.commit(); conflicts=validate(db,one(db,Roster,id));return {"entry_id":e.id,"conflicts":len(conflicts)}
@app.post("/rosters/{id}/validate")
def validate_roster(id:int,db:Session=Depends(get_db)): return {"conflicts":[{"id":c.id,"type":c.conflict_type,"severity":c.severity,"date":c.date,"description":c.description,"suggestion":c.suggestion} for c in validate(db,one(db,Roster,id))]}
@app.post("/rosters/{id}/publish")
def publish(id:int,db:Session=Depends(get_db)):
 r=one(db,Roster,id);conflicts=validate(db,r)
 if any(c.severity in ("critical","high") for c in conflicts):raise HTTPException(409,"Cannot publish roster with critical/high conflicts")
 r.status="published";db.commit();return {"status":"published"}
@app.get("/conflicts")
def conflicts(roster_id:int|None=None,db:Session=Depends(get_db)):
 q=db.query(SchedulingConflict)
 if roster_id:q=q.filter_by(roster_id=roster_id)
 return [{"id":c.id,"type":c.conflict_type,"severity":c.severity,"date":c.date,"description":c.description,"suggestion":c.suggestion,"status":c.status} for c in q.all()]
@app.post("/rosters/{id}/recommend-backup")
def recommend(id:int,process_id:int,work_date:date,db:Session=Depends(get_db)):
 current=one(db,Roster,id); used={e.employee_id for e in current.entries if e.work_date==work_date and e.status=="working"}; candidates=[]
 for a in db.query(EmployeeAssignment).filter_by(process_id=process_id,qualified=True):
  e=a.employee
  blocked=not e.active or e.id in used or work_date.weekday() in e.weekly_off_days or any(l.employee_id==e.id and l.status=="approved" and l.start_date<=work_date<=l.end_date for l in db.query(LeaveRequest))
  candidates.append({"employee_id":e.id,"name":e.full_name,"eligible":not blocked,"reason":"Qualified, available and unassigned" if not blocked else "Unavailable, on weekly off, leave, or already scheduled"})
 return sorted(candidates,key=lambda x:not x["eligible"])
