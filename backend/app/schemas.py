from pydantic import BaseModel, Field
from datetime import date


class EmployeeIn(BaseModel):
    employee_code: str
    full_name: str
    email: str
    job_title: str = "Operations Associate"
    pod_id: int | None = None
    max_weekly_hours: int = 48
    weekly_off_days: list[int] = Field(default_factory=list)
    availability: list[str] = Field(default_factory=lambda: ["morning"])


class BrandIn(BaseModel):
    name: str
    description: str = ""
    pod_id: int | None = None
    active: bool = True


class ProcessIn(BaseModel):
    brand_id: int
    name: str
    description: str = ""
    minimum_staff: int = 1
    working_days: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4])
    include_holidays: bool = False
    shift: str = "morning"


class AssignmentIn(BaseModel):
    employee_id: int
    process_id: int
    qualified: bool = True
    priority: int = 1


class LeaveIn(BaseModel):
    employee_id: int
    start_date: date
    end_date: date
    leave_type: str
    reason: str = ""
    status: str = "pending"


class PodIn(BaseModel):
    name: str
    lead_id: int | None = None


class CompOffIn(BaseModel):
    employee_id: int
    work_date: date
    reason: str = ""
    status: str = "approved"


class HolidayIn(BaseModel):
    name: str
    date: date
    brand_id: int | None = None


class GenerateIn(BaseModel):
    year: int
    month: int
    pod_id: int | None = None


class EntryEdit(BaseModel):
    employee_id: int | None = None
    process_id: int | None = None
    status: str | None = None
    shift: str | None = None