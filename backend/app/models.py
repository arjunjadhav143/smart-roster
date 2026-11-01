import enum
from datetime import date, datetime
from sqlalchemy import String, Integer, Boolean, Date, DateTime, ForeignKey, UniqueConstraint, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class Status(str, enum.Enum): active="active"; inactive="inactive"
class RosterStatus(str, enum.Enum): draft="draft"; published="published"; infeasible="infeasible"
class Pod(Base):
    __tablename__="pods"; id: Mapped[int]=mapped_column(primary_key=True); name: Mapped[str]=mapped_column(String(100), unique=True); lead_id: Mapped[int|None]=mapped_column(ForeignKey("employees.id"), nullable=True)
class Employee(Base):
    __tablename__="employees"; id: Mapped[int]=mapped_column(primary_key=True); employee_code: Mapped[str]=mapped_column(String(20), unique=True, index=True); full_name: Mapped[str]=mapped_column(String(120)); email: Mapped[str]=mapped_column(String(150), unique=True); job_title: Mapped[str]=mapped_column(String(100), default="Operations Associate"); pod_id: Mapped[int|None]=mapped_column(ForeignKey("pods.id")); active: Mapped[bool]=mapped_column(Boolean, default=True); max_weekly_hours: Mapped[int]=mapped_column(Integer, default=48); weekly_off_days: Mapped[list]=mapped_column(JSON, default=list); availability: Mapped[list]=mapped_column(JSON, default=lambda:["morning"])
    pod=relationship("Pod", foreign_keys=[pod_id]); assignments=relationship("EmployeeAssignment", back_populates="employee")
class Brand(Base):
    __tablename__="brands"; id: Mapped[int]=mapped_column(primary_key=True); name: Mapped[str]=mapped_column(String(120), unique=True); description: Mapped[str]=mapped_column(Text, default=""); active: Mapped[bool]=mapped_column(Boolean, default=True); pod_id: Mapped[int|None]=mapped_column(ForeignKey("pods.id")); processes=relationship("Process", back_populates="brand")
class Process(Base):
    __tablename__="processes"; id: Mapped[int]=mapped_column(primary_key=True); brand_id: Mapped[int]=mapped_column(ForeignKey("brands.id")); name: Mapped[str]=mapped_column(String(100)); description: Mapped[str]=mapped_column(Text, default=""); minimum_staff: Mapped[int]=mapped_column(Integer, default=1); working_days: Mapped[list]=mapped_column(JSON, default=lambda:[0,1,2,3,4]); include_holidays: Mapped[bool]=mapped_column(Boolean, default=False); shift: Mapped[str]=mapped_column(String(30), default="morning")
    brand=relationship("Brand", back_populates="processes"); assignments=relationship("EmployeeAssignment", back_populates="process")
    __table_args__=(UniqueConstraint("brand_id","name",name="uq_brand_process"),)
class EmployeeAssignment(Base):
    __tablename__="employee_assignments"; id: Mapped[int]=mapped_column(primary_key=True); employee_id: Mapped[int]=mapped_column(ForeignKey("employees.id")); process_id: Mapped[int]=mapped_column(ForeignKey("processes.id")); qualified: Mapped[bool]=mapped_column(Boolean, default=True); priority: Mapped[int]=mapped_column(Integer, default=1)
    employee=relationship("Employee",back_populates="assignments"); process=relationship("Process",back_populates="assignments")
    __table_args__=(UniqueConstraint("employee_id","process_id",name="uq_employee_process"),)
class LeaveRequest(Base):
    __tablename__="leave_requests"; id: Mapped[int]=mapped_column(primary_key=True); employee_id: Mapped[int]=mapped_column(ForeignKey("employees.id")); start_date: Mapped[date]=mapped_column(Date); end_date: Mapped[date]=mapped_column(Date); leave_type: Mapped[str]=mapped_column(String(30)); reason: Mapped[str]=mapped_column(Text,default=""); status: Mapped[str]=mapped_column(String(20),default="pending")
class Holiday(Base):
    __tablename__="public_holidays"; id: Mapped[int]=mapped_column(primary_key=True); name: Mapped[str]=mapped_column(String(120)); date: Mapped[date]=mapped_column(Date, index=True); brand_id: Mapped[int|None]=mapped_column(ForeignKey("brands.id"),nullable=True)
class Roster(Base):
    __tablename__="rosters"; id: Mapped[int]=mapped_column(primary_key=True); year: Mapped[int]=mapped_column(Integer); month: Mapped[int]=mapped_column(Integer); status: Mapped[str]=mapped_column(String(20),default="draft"); solver_status: Mapped[str]=mapped_column(String(30),default=""); created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow); entries=relationship("RosterEntry",back_populates="roster",cascade="all, delete-orphan")
    __table_args__=(UniqueConstraint("year","month",name="uq_roster_month"),)
class RosterEntry(Base):
    __tablename__="roster_entries"; id: Mapped[int]=mapped_column(primary_key=True); roster_id: Mapped[int]=mapped_column(ForeignKey("rosters.id")); employee_id: Mapped[int]=mapped_column(ForeignKey("employees.id")); process_id: Mapped[int|None]=mapped_column(ForeignKey("processes.id"),nullable=True); work_date: Mapped[date]=mapped_column(Date); status: Mapped[str]=mapped_column(String(30)); shift: Mapped[str|None]=mapped_column(String(30),nullable=True)
    roster=relationship("Roster",back_populates="entries"); employee=relationship("Employee"); process=relationship("Process")
class SchedulingConflict(Base):
    __tablename__="scheduling_conflicts"; id: Mapped[int]=mapped_column(primary_key=True); roster_id: Mapped[int]=mapped_column(ForeignKey("rosters.id")); conflict_type: Mapped[str]=mapped_column(String(60)); severity: Mapped[str]=mapped_column(String(20)); date: Mapped[date]=mapped_column(Date); employee_id: Mapped[int|None]=mapped_column(ForeignKey("employees.id"),nullable=True); process_id: Mapped[int|None]=mapped_column(ForeignKey("processes.id"),nullable=True); description: Mapped[str]=mapped_column(Text); suggestion: Mapped[str]=mapped_column(Text); status: Mapped[str]=mapped_column(String(20),default="open")
