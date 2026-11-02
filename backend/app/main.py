from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
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
def list_employees(q:str="",pod_id:int|None=None,page:int=1,page_size:int=100,db:Session=Depends(get_db)):
 query=db.query(Employee).filter(Employee.full_name.ilike(f"%{q}%"))
 if pod_id: query=query.filter_by(pod_id=pod_id)
 return [{"id":e.id,"employee_code":e.employee_code,"full_name":e.full_name,"email":e.email,"job_title":e.job_title,"pod_id":e.pod_id,"pod":e.pod.name if e.pod else None,"active":e.active,"weekly_off_days":e.weekly_off_days,"availability":e.availability,"max_weekly_hours":e.max_weekly_hours} for e in query.offset((page-1)*page_size).limit(min(page_size,200)).all()]
@app.post("/employees",status_code=201)
def create_employee(data:EmployeeIn,db:Session=Depends(get_db)): o=Employee(**data.model_dump());db.add(o);db.commit();db.refresh(o);return {"id":o.id}
@app.get("/employees/{id}")
def get_employee(id:int,db:Session=Depends(get_db)):
 e=one(db,Employee,id); return {"id":e.id,"employee_code":e.employee_code,"full_name":e.full_name,"email":e.email,"job_title":e.job_title,"pod_id":e.pod_id,"active":e.active,"weekly_off_days":e.weekly_off_days,"availability":e.availability,"max_weekly_hours":e.max_weekly_hours}
@app.put("/employees/{id}")
def update_employee(id:int,data:EmployeeIn,db:Session=Depends(get_db)): o=one(db,Employee,id);[setattr(o,k,v) for k,v in data.model_dump().items()];db.commit();return {"id":id}
@app.delete("/employees/{id}")
def deactivate_employee(id:int,db:Session=Depends(get_db)): o=one(db,Employee,id);o.active=False;db.commit();return {"status":"deactivated"}
@app.patch("/employees/{id}/status")
def employee_status(id:int,active:bool,db:Session=Depends(get_db)): o=one(db,Employee,id);o.active=active;db.commit();return {"id":id,"active":active}
@app.get("/pods")
def pods(db:Session=Depends(get_db)): return [{"id":p.id,"name":p.name,"lead_id":p.lead_id,"lead":db.get(Employee,p.lead_id).full_name if p.lead_id and db.get(Employee,p.lead_id) else None,"employee_count":db.query(Employee).filter_by(pod_id=p.id,active=True).count()} for p in db.query(Pod).all()]
@app.post("/pods")
def create_pod(data:PodIn,db:Session=Depends(get_db)): o=Pod(**data.model_dump());db.add(o);db.commit();db.refresh(o);return {"id":o.id}
@app.put("/pods/{id}")
def update_pod(id:int,data:PodIn,db:Session=Depends(get_db)): o=one(db,Pod,id);o.name=data.name;o.lead_id=data.lead_id;db.commit();return {"id":id}
<<<<<<< HEAD
@app.delete("/pods/{id}")
def delete_pod(id:int,db:Session=Depends(get_db)):
 o=one(db,Pod,id)
 for e in db.query(Employee).filter_by(pod_id=id): e.pod_id=None
 for b in db.query(Brand).filter_by(pod_id=id): b.pod_id=None
 db.delete(o);db.commit();return {"status":"removed"}
=======
>>>>>>> 507587b3f44247ef3719d068bdfc140e94acfb7d
@app.get("/pods/{id}")
def get_pod(id:int,db:Session=Depends(get_db)):
 p=one(db,Pod,id); return {"id":p.id,"name":p.name,"lead_id":p.lead_id,"employees":[{"id":e.id,"name":e.full_name} for e in db.query(Employee).filter_by(pod_id=id).all()]}
@app.get("/brands")
def brands(db:Session=Depends(get_db)): return [{"id":b.id,"name":b.name,"description":b.description,"active":b.active,"process_count":len(b.processes)} for b in db.query(Brand).all()]
@app.post("/brands")
def create_brand(data:BrandIn,db:Session=Depends(get_db)): o=Brand(**data.model_dump());db.add(o);db.commit();db.refresh(o);return o
@app.put("/brands/{id}")
def update_brand(id:int,data:BrandIn,db:Session=Depends(get_db)): o=one(db,Brand,id);[setattr(o,k,v) for k,v in data.model_dump().items()];db.commit();return {"id":id}
@app.delete("/brands/{id}")
def deactivate_brand(id:int,db:Session=Depends(get_db)): one(db,Brand,id).active=False;db.commit();return {"status":"deactivated"}
@app.get("/processes")
def processes(brand_id:int|None=None,db:Session=Depends(get_db)):
 q=db.query(Process);
 if brand_id:q=q.filter_by(brand_id=brand_id)
 return [{"id":p.id,"brand_id":p.brand_id,"brand":p.brand.name,"name":p.name,"minimum_staff":p.minimum_staff,"working_days":p.working_days,"shift":p.shift} for p in q.all()]
@app.post("/processes")
def create_process(data:ProcessIn,db:Session=Depends(get_db)): o=Process(**data.model_dump());db.add(o);db.commit();db.refresh(o);return o
@app.put("/processes/{id}")
def update_process(id:int,data:ProcessIn,db:Session=Depends(get_db)): o=one(db,Process,id);[setattr(o,k,v) for k,v in data.model_dump().items()];db.commit();return {"id":id}
<<<<<<< HEAD
@app.delete("/processes/{id}")
def delete_process(id:int,db:Session=Depends(get_db)):
 o=one(db,Process,id)
 if db.query(RosterEntry).filter_by(process_id=id).first(): raise HTTPException(409,"Process has roster history and cannot be removed")
 db.query(EmployeeAssignment).filter_by(process_id=id).delete(synchronize_session=False);db.delete(o);db.commit();return {"status":"removed"}
=======
>>>>>>> 507587b3f44247ef3719d068bdfc140e94acfb7d
@app.get("/assignments")
def assignments(db:Session=Depends(get_db)): return [{"id":a.id,"employee_id":a.employee_id,"employee":a.employee.full_name,"process_id":a.process_id,"process":a.process.name,"brand":a.process.brand.name,"qualified":a.qualified} for a in db.query(EmployeeAssignment).all()]
@app.post("/assignments")
def create_assignment(data:AssignmentIn,db:Session=Depends(get_db)): o=EmployeeAssignment(**data.model_dump());db.add(o);db.commit();db.refresh(o);return o
@app.put("/assignments/{id}")
def update_assignment(id:int,data:AssignmentIn,db:Session=Depends(get_db)): o=one(db,EmployeeAssignment,id);[setattr(o,k,v) for k,v in data.model_dump().items()];db.commit();return {"id":id}
@app.delete("/assignments/{id}")
def delete_assignment(id:int,db:Session=Depends(get_db)): db.delete(one(db,EmployeeAssignment,id));db.commit();return {"status":"removed"}
@app.get("/leaves")
def leaves(db:Session=Depends(get_db)): return [{"id":x.id,"employee_id":x.employee_id,"start_date":x.start_date,"end_date":x.end_date,"leave_type":x.leave_type,"status":x.status} for x in db.query(LeaveRequest).all()]
@app.post("/leaves")
def create_leave(data:LeaveIn,db:Session=Depends(get_db)): o=LeaveRequest(**data.model_dump());db.add(o);db.commit();db.refresh(o);return o
@app.post("/leaves/{id}/approve")
def approve_leave(id:int,db:Session=Depends(get_db)): o=one(db,LeaveRequest,id);o.status="approved";db.commit();return {"status":"approved"}
@app.post("/leaves/{id}/reject")
def reject_leave(id:int,db:Session=Depends(get_db)): o=one(db,LeaveRequest,id);o.status="rejected";db.commit();return {"status":"rejected"}
@app.post("/leaves/{id}/cancel")
def cancel_leave(id:int,db:Session=Depends(get_db)): o=one(db,LeaveRequest,id);o.status="cancelled";db.commit();return {"status":"cancelled"}
<<<<<<< HEAD
@app.delete("/leaves/{id}")
def delete_leave(id:int,db:Session=Depends(get_db)): db.delete(one(db,LeaveRequest,id));db.commit();return {"status":"removed"}
@app.get("/comp-offs")
def comp_offs(db:Session=Depends(get_db)): return [{"id":x.id,"employee_id":x.employee_id,"employee":db.get(Employee,x.employee_id).full_name if db.get(Employee,x.employee_id) else None,"work_date":x.work_date,"reason":x.reason,"status":x.status} for x in db.query(CompOff).order_by(CompOff.work_date).all()]
@app.post("/comp-offs",status_code=201)
def create_comp_off(data:CompOffIn,db:Session=Depends(get_db)): o=CompOff(**data.model_dump());db.add(o);db.commit();db.refresh(o);return {"id":o.id}
@app.put("/comp-offs/{id}")
def update_comp_off(id:int,data:CompOffIn,db:Session=Depends(get_db)): o=one(db,CompOff,id);[setattr(o,k,v) for k,v in data.model_dump().items()];db.commit();return {"id":id}
@app.delete("/comp-offs/{id}")
def delete_comp_off(id:int,db:Session=Depends(get_db)): db.delete(one(db,CompOff,id));db.commit();return {"status":"removed"}
=======
>>>>>>> 507587b3f44247ef3719d068bdfc140e94acfb7d
@app.get("/holidays")
def holidays(db:Session=Depends(get_db)): return [{"id":h.id,"name":h.name,"date":h.date,"brand_id":h.brand_id} for h in db.query(Holiday).order_by(Holiday.date).all()]
@app.post("/holidays")
def create_holiday(data:HolidayIn,db:Session=Depends(get_db)): h=Holiday(**data.model_dump());db.add(h);db.commit();db.refresh(h);return {"id":h.id}
@app.put("/holidays/{id}")
def update_holiday(id:int,data:HolidayIn,db:Session=Depends(get_db)): h=one(db,Holiday,id);[setattr(h,k,v) for k,v in data.model_dump().items()];db.commit();return {"id":id}
@app.delete("/holidays/{id}")
def delete_holiday(id:int,db:Session=Depends(get_db)): db.delete(one(db,Holiday,id));db.commit();return {"status":"removed"}
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
def roster_entries(id:int,db:Session=Depends(get_db)): return [{"id":e.id,"employee_id":e.employee_id,"employee":e.employee.full_name,"pod":e.employee.pod.name if e.employee.pod else None,"process_id":e.process_id,"process":e.process.name if e.process else None,"brand":e.process.brand.name if e.process else None,"work_date":e.work_date,"status":e.status,"shift":e.shift} for e in one(db,Roster,id).entries]
@app.put("/rosters/{id}/entries/{entry_id}")
def edit_entry(id:int,entry_id:int,data:EntryEdit,db:Session=Depends(get_db)):
 e=one(db,RosterEntry,entry_id)
 if e.roster_id!=id: raise HTTPException(400,"Entry does not belong to roster")
 for k,v in data.model_dump(exclude_none=True).items():setattr(e,k,v)
 db.commit(); conflicts=validate(db,one(db,Roster,id));return {"entry_id":e.id,"conflicts":len(conflicts)}
@app.post("/rosters/{id}/validate")
def validate_roster(id:int,db:Session=Depends(get_db)):
 r=one(db,Roster,id); cs=validate(db,r); payload=[{"id":c.id,"type":c.conflict_type,"severity":c.severity,"date":c.date,"employee_id":c.employee_id,"process_id":c.process_id,"description":c.description,"suggestion":c.suggestion,"status":c.status} for c in cs]
 coverage=[x for x in payload if x["type"] in ("COVERAGE_SHORTAGE","UNASSIGNED_REQUIRED_PROCESS","HOLIDAY_COVERAGE_GAP")]
 return {"valid":not any(c.severity in ("critical","high") for c in cs),"total_conflicts":len(cs),"critical":sum(c.severity=="critical" for c in cs),"warnings":sum(c.severity=="warning" for c in cs),"conflicts":payload,"coverage_summary":coverage}
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
  blocked=not e.active or e.id in used or work_date.weekday() in e.weekly_off_days or any(l.employee_id==e.id and l.status=="approved" and l.start_date<=work_date<=l.end_date for l in db.query(LeaveRequest)) or any(c.employee_id==e.id and c.work_date==work_date and c.status=="approved" for c in db.query(CompOff))
  candidates.append({"employee_id":e.id,"name":e.full_name,"eligible":not blocked,"reason":"Qualified, available and unassigned" if not blocked else "Unavailable, on weekly off, leave, comp-off, or already scheduled"})
 return sorted(candidates,key=lambda x:not x["eligible"])
