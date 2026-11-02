from calendar import monthrange
from datetime import date, timedelta
from ortools.sat.python import cp_model
from sqlalchemy.orm import Session
from ..models import Employee, Process, EmployeeAssignment, LeaveRequest, Holiday

def generate(db: Session, year:int, month:int, pod_id:int|None=None):
    """CP-SAT model: every required process/day is staffed by qualified, available staff, once/day."""
    employees=db.query(Employee).filter_by(active=True).all()
    if pod_id: employees=[e for e in employees if e.pod_id==pod_id]
    processes=db.query(Process).join(Process.brand).all(); days=[date(year,month,d) for d in range(1,monthrange(year,month)[1]+1)]
    assignments=db.query(EmployeeAssignment).filter(EmployeeAssignment.qualified==True).all()
    eligible={(a.employee_id,a.process_id) for a in assignments}
    leaves=db.query(LeaveRequest).filter_by(status="approved").all()
    leave_dates={(l.employee_id, d) for l in leaves for d in days if l.start_date<=d<=l.end_date}
    holidays=db.query(Holiday).all()
    holiday_dates={(h.date,h.brand_id) for h in holidays}
    model=cp_model.CpModel(); x={}; required=[]; weekly_off_penalties=[]
    for p in processes:
      for d in days:
        holiday=(d,p.brand_id) in holiday_dates or (d,None) in holiday_dates
        if d.weekday() not in p.working_days or (holiday and not p.include_holidays): continue
        # Weekly offs are preferences, not absolute unavailability. Required
        # brand/process coverage is mandatory and may override a preference.
        candidates=[e for e in employees if (e.id,p.id) in eligible and p.shift in e.availability and (e.id,d) not in leave_dates]
        vars=[]
        for e in candidates:
          x[e.id,p.id,d]=model.NewBoolVar(f"e{e.id}_p{p.id}_{d}")
          vars.append(x[e.id,p.id,d])
          if d.weekday() in e.weekly_off_days: weekly_off_penalties.append(x[e.id,p.id,d])
        model.Add(sum(vars)>=p.minimum_staff); required.append((p,d,len(candidates)))
    # no double booking; max working days approximates max weekly hours / 8 in rolling calendar weeks
    for e in employees:
      for d in days: model.Add(sum(v for (eid,_,dd),v in x.items() if eid==e.id and dd==d)<=1)
      for week_start in days:
        week_end=week_start+timedelta(days=6)
        model.Add(sum(v for (eid,_,dd),v in x.items() if eid==e.id and week_start<=dd<=week_end)*8<=e.max_weekly_hours)
    # Staff only required coverage first, then minimize work placed on a
    # preferred weekly-off day. Mandatory coverage always wins.
    model.Minimize(sum(x.values()) * 100 + sum(weekly_off_penalties))
    solver=cp_model.CpSolver(); solver.parameters.max_time_in_seconds=15; outcome=solver.Solve(model)
    infeasible=[]
    if outcome not in (cp_model.OPTIMAL,cp_model.FEASIBLE):
      for p,d,count in required:
        if count<p.minimum_staff: infeasible.append({"date":str(d),"process_id":p.id,"brand":p.brand.name,"process":p.name,"required":p.minimum_staff,"available":count,"reason":"Insufficient qualified, available employees"})
      return [], infeasible, "INFEASIBLE"
    rows=[]
    for (eid,pid,d),v in x.items():
      if solver.Value(v): rows.append((eid,pid,d,"working",db.get(Process,pid).shift))
    return rows, [], "FEASIBLE"
