from collections import defaultdict
from sqlalchemy.orm import Session
from ..models import Roster, RosterEntry, Process, LeaveRequest, SchedulingConflict

def validate(db:Session, roster:Roster):
    db.query(SchedulingConflict).filter_by(roster_id=roster.id).delete()
    conflicts=[]; entries=db.query(RosterEntry).filter_by(roster_id=roster.id).all(); grouped=defaultdict(list)
    for e in entries: grouped[(e.employee_id,e.work_date)].append(e)
    leaves=db.query(LeaveRequest).filter_by(status="approved").all()
    for (employee_id, day), es in grouped.items():
      if len(es)>1: conflicts.append(("overlapping_shift","high",day,employee_id,None,"Employee is assigned to simultaneous responsibilities.","Reassign one responsibility."))
      if any(l.employee_id==employee_id and l.start_date<=day<=l.end_date for l in leaves): conflicts.append(("leave_violation","critical",day,employee_id,None,"Employee is scheduled during approved leave.","Choose an eligible replacement."))
    by_process=defaultdict(list)
    for e in entries:
      if e.status=="working" and e.process_id: by_process[(e.process_id,e.work_date)].append(e)
    for (pid,day), es in by_process.items():
      p=db.get(Process,pid)
      if len(es)<p.minimum_staff: conflicts.append(("coverage_gap","critical",day,None,pid,f"{p.name} requires {p.minimum_staff} staff but has {len(es)}.","Assign a qualified, available employee."))
    for typ,severity,day,eid,pid,desc,suggest in conflicts: db.add(SchedulingConflict(roster_id=roster.id,conflict_type=typ,severity=severity,date=day,employee_id=eid,process_id=pid,description=desc,suggestion=suggest))
    db.commit(); return db.query(SchedulingConflict).filter_by(roster_id=roster.id).all()
