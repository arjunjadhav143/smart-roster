from datetime import date
from .models import Pod,Employee,Brand,Process,EmployeeAssignment,LeaveRequest,Holiday
def seed(db):
 if db.query(Employee).count(): return
 pods=[Pod(name=n) for n in ["Customer Success","Revenue Operations","Retention","Fulfilment"]]; db.add_all(pods); db.flush()
 employees=[]
 names=["Aarav Sharma","Diya Patel","Vihaan Singh","Ananya Rao","Arjun Mehta","Isha Gupta","Kabir Khan","Meera Nair","Rohan Das","Sana Ali","Aditya Roy","Kavya Iyer","Reyansh Jain","Priya Shah","Dev Malhotra","Neha Kapoor","Ishaan Bose","Tanya Verma","Rahul Joshi","Aditi Menon","Yash Kumar","Nisha Sethi","Manav Arora","Riya Bansal","Siddharth Pal","Pooja Ghosh","Varun Sinha","Maya Pillai","Karan Bhat","Simran Kaur"]
 for i,n in enumerate(names,1): employees.append(Employee(employee_code=f"E{i:03}",full_name=n,email=f"e{i:03}@example.com",pod_id=pods[(i-1)%4].id,weekly_off_days=[6] if i%3 else [5],availability=["morning","evening"] if i%4==0 else ["morning"]))
 db.add_all(employees); db.flush()
 brands=[Brand(name=n,pod_id=pods[i%4].id,description=f"D2C {n} operations") for i,n in enumerate(["Aster","Bloom","Cove","Drift","Ember","Fable","Grove","Halo","Indigo","Juniper"])] ; db.add_all(brands); db.flush()
 procs=[]
 for i,b in enumerate(brands):
  selected=[("Customer Support",[0,1,2,3,4,5,6] if i%3==0 else [0,1,2,3,4],True if i%3==0 else False),("Abandoned Cart",[0,1,2,3,4,5],False),("NDR",[0,1,2,3,4],False)]
  for name,days,hol in selected: procs.append(Process(brand_id=b.id,name=name,working_days=days,include_holidays=hol,minimum_staff=1,shift="morning"))
 db.add_all(procs); db.flush()
 for i,p in enumerate(procs):
  # Every process has 2 qualification backups, enough for a generally feasible month
  for offset in (0,7): db.add(EmployeeAssignment(employee_id=employees[(i+offset)%len(employees)].id,process_id=p.id))
 db.add_all([LeaveRequest(employee_id=employees[0].id,start_date=date(2026,11,8),end_date=date(2026,11,8),leave_type="planned",reason="Family event",status="approved"),LeaveRequest(employee_id=employees[3].id,start_date=date(2026,11,15),end_date=date(2026,11,16),leave_type="sick",reason="Medical",status="pending"),Holiday(name="Diwali",date=date(2026,11,8))]); db.commit()
