from datetime import date
from .models import Pod,Employee,Brand,Process,EmployeeAssignment,LeaveRequest,Holiday,CompOff
def seed(db):
 if db.query(Employee).count(): return
 pods=[Pod(name=n) for n in ["Customer Success","Revenue Operations","Retention","Fulfilment"]]; db.add_all(pods); db.flush()
 employees=[]
 names=["Aarav Sharma","Diya Patel","Vihaan Singh","Ananya Rao","Arjun Mehta","Isha Gupta","Kabir Khan","Meera Nair","Rohan Das","Sana Ali","Aditya Roy","Kavya Iyer","Reyansh Jain","Priya Shah","Dev Malhotra","Neha Kapoor","Ishaan Bose","Tanya Verma","Rahul Joshi","Aditi Menon","Yash Kumar","Nisha Sethi","Manav Arora","Riya Bansal","Siddharth Pal","Pooja Ghosh","Varun Sinha","Maya Pillai","Karan Bhat","Simran Kaur"]
 for i,n in enumerate(names,1): employees.append(Employee(employee_code=f"E{i:03}",full_name=n,email=f"e{i:03}@example.com",pod_id=pods[(i-1)%4].id,weekly_off_days=[6] if i%3 else [5],availability=["morning","evening"] if i%4==0 else ["morning"]))
 db.add_all(employees); db.flush()
 # Leads are real employees.  This compact schema intentionally keeps role
 # management in the forthcoming auth/profile migration, while lead ownership
 # is already database-backed and usable by the API.
 for i,pod in enumerate(pods): pod.lead_id=employees[i].id
 brands=[Brand(name=n,pod_id=pods[i%4].id,description=f"D2C {n} operations") for i,n in enumerate(["Aster","Bloom","Cove","Drift","Ember","Fable","Grove","Halo","Indigo","Juniper"])] ; db.add_all(brands); db.flush()
 procs=[]
 for i,b in enumerate(brands):
  # Eight brands deliberately use one dedicated resource and one process.
  # The final two are multi-resource, demonstrating both split and shared work.
  selected=[("Customer Support" if i%2==0 else "Order Management",[0,1,2,3,4],False)] if i<8 else [("Customer Support",[0,1,2,3,4,5,6],True),("Abandoned Cart",[0,1,2,3,4,5],False),("NDR",[0,1,2,3,4],False)]
  for name,days,hol in selected: procs.append(Process(brand_id=b.id,name=name,working_days=days,include_holidays=hol,minimum_staff=1,shift="morning"))
 db.add_all(procs); db.flush()
 for i,p in enumerate(procs):
  if i<8: db.add(EmployeeAssignment(employee_id=employees[i].id,process_id=p.id))
  else:
   # Multi-resource brands include process specialists and shared coverage.
   for offset in (8,9,16): db.add(EmployeeAssignment(employee_id=employees[(i+offset)%len(employees)].id,process_id=p.id))
<<<<<<< HEAD
 db.add_all([LeaveRequest(employee_id=employees[0].id,start_date=date(2026,11,8),end_date=date(2026,11,8),leave_type="planned",reason="Family event",status="approved"),LeaveRequest(employee_id=employees[3].id,start_date=date(2026,11,15),end_date=date(2026,11,16),leave_type="sick",reason="Medical",status="pending"),CompOff(employee_id=employees[29].id,work_date=date(2026,11,14),reason="Weekend campaign coverage"),Holiday(name="Diwali",date=date(2026,11,8))]); db.commit()
=======
 db.add_all([LeaveRequest(employee_id=employees[0].id,start_date=date(2026,11,8),end_date=date(2026,11,8),leave_type="planned",reason="Family event",status="approved"),LeaveRequest(employee_id=employees[3].id,start_date=date(2026,11,15),end_date=date(2026,11,16),leave_type="sick",reason="Medical",status="pending"),Holiday(name="Diwali",date=date(2026,11,8))]); db.commit()
>>>>>>> 507587b3f44247ef3719d068bdfc140e94acfb7d
