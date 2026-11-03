"""Independent roster validation; requirements never come from existing entries."""

from collections import defaultdict
from calendar import monthrange
from datetime import date, timedelta
from sqlalchemy.orm import Session

from ..models import (
    Roster,
    RosterEntry,
    Process,
    LeaveRequest,
    Holiday,
    Employee,
    EmployeeAssignment,
    SchedulingConflict,
    CompOff,
)

CRITICAL = {
    "COVERAGE_SHORTAGE",
    "UNASSIGNED_REQUIRED_PROCESS",
    "APPROVED_LEAVE_VIOLATION",
    "APPROVED_COMP_OFF_VIOLATION",
    "EMPLOYEE_DOUBLE_BOOKING",
    "SHIFT_OVERLAP",
    "WEEKLY_HOURS_EXCEEDED",
    "UNQUALIFIED_ASSIGNMENT",
    "INVALID_PROCESS_ASSIGNMENT",
    "HOLIDAY_COVERAGE_GAP",
}


def add(items, typ, day, eid=None, pid=None, desc="", suggestion=""):
    items.append((
        typ,
        "critical" if typ in CRITICAL else "warning",
        day,
        eid,
        pid,
        desc,
        suggestion,
    ))


def validate(db: Session, roster: Roster):

    db.query(SchedulingConflict).filter_by(
        roster_id=roster.id
    ).delete(synchronize_session=False)

    entries = db.query(RosterEntry).filter_by(
        roster_id=roster.id
    ).all()

    processes = (
        db.query(Process)
        .join(Process.brand)
        .filter(Process.brand.has(active=True))
        .all()
    )

    process_by_id = {p.id: p for p in processes}
    employees = {e.id: e for e in db.query(Employee).all()}

    qualifications = {
        (a.employee_id, a.process_id): a.qualified
        for a in db.query(EmployeeAssignment).all()
    }

    leaves = db.query(LeaveRequest).all()
    comp_offs = db.query(CompOff).all()
    holidays = db.query(Holiday).all()

    issues = []

    by_employee_day = defaultdict(list)
    by_process_day = defaultdict(list)

    for entry in entries:

        by_employee_day[
            entry.employee_id,
            entry.work_date
        ].append(entry)

        if entry.status == "working" and entry.process_id:
            by_process_day[
                entry.process_id,
                entry.work_date
            ].append(entry)

    # Employee-level validation
    for (eid, day), rows in by_employee_day.items():

        working = [
            r for r in rows
            if r.status == "working"
        ]

        employee = employees.get(eid)

        if len(working) > 1:
            add(
                issues,
                "EMPLOYEE_DOUBLE_BOOKING",
                day,
                eid,
                desc="Employee has more than one working assignment on the same date.",
                suggestion="Reassign one responsibility.",
            )

        for row in working:

            p = process_by_id.get(row.process_id)

            if not p:
                add(
                    issues,
                    "INVALID_PROCESS_ASSIGNMENT",
                    day,
                    eid,
                    row.process_id,
                    "The roster references a missing or inactive process.",
                    "Select an active process.",
                )
                continue

            if (
                not employee
                or not employee.active
                or not qualifications.get((eid, p.id), False)
            ):
                add(
                    issues,
                    "UNQUALIFIED_ASSIGNMENT",
                    day,
                    eid,
                    p.id,
                    "Employee is not an active qualified assignee for this process.",
                    "Select a qualified replacement.",
                )

            if employee and p.shift not in (employee.availability or []):
                add(
                    issues,
                    "SHIFT_OVERLAP",
                    day,
                    eid,
                    p.id,
                    "Employee is unavailable for the assigned shift.",
                    "Use a compatible shift or replacement.",
                )

            # Leave validation
            for leave in leaves:

                if (
                    leave.employee_id == eid
                    and leave.start_date <= day <= leave.end_date
                ):

                    if leave.status == "approved":
                        add(
                            issues,
                            "APPROVED_LEAVE_VIOLATION",
                            day,
                            eid,
                            p.id,
                            "Employee is scheduled during approved leave.",
                            "Choose an eligible replacement.",
                        )

                    elif leave.status == "pending":
                        add(
                            issues,
                            "NO_AVAILABLE_EMPLOYEE",
                            day,
                            eid,
                            p.id,
                            "Employee has a pending leave request on this date.",
                            "Review leave risk before publishing.",
                        )

            # Comp Off validation
            if any(
                c.employee_id == eid
                and c.work_date == day
                and c.status == "approved"
                for c in comp_offs
            ):
                add(
                    issues,
                    "APPROVED_COMP_OFF_VIOLATION",
                    day,
                    eid,
                    p.id,
                    "Employee is scheduled during an approved compensatory off.",
                    "Choose an eligible replacement.",
                )

    # Weekly working hours validation
    for eid, employee in employees.items():

        for n in range(
            1,
            monthrange(roster.year, roster.month)[1] + 1
        ):

            start = date(roster.year, roster.month, n)
            end = start + timedelta(days=6)

            hours = 8 * sum(
                any(r.status == "working" for r in rows)
                for (emp, day), rows in by_employee_day.items()
                if emp == eid and start <= day <= end
            )

            if hours > employee.max_weekly_hours:
                add(
                    issues,
                    "WEEKLY_HOURS_EXCEEDED",
                    start,
                    eid,
                    desc=f"Scheduled {hours} hours in a rolling seven-day period.",
                    suggestion="Reassign work or adjust the schedule.",
                )
                break

    # Full process and date coverage validation
    for p in processes:

        for n in range(
            1,
            monthrange(roster.year, roster.month)[1] + 1
        ):

            day = date(roster.year, roster.month, n)

            holiday = any(
                h.date == day
                and h.brand_id in (None, p.brand_id)
                for h in holidays
            )

            if (
                day.weekday() not in (p.working_days or [])
                or (holiday and not p.include_holidays)
            ):
                continue

            valid = []

            for entry in by_process_day[p.id, day]:

                employee = employees.get(entry.employee_id)

                blocked = (
                    not employee
                    or not employee.active
                    or not qualifications.get(
                        (entry.employee_id, p.id), False
                    )
                    or p.shift not in (employee.availability or [])
                    or any(
                        l.employee_id == entry.employee_id
                        and l.status == "approved"
                        and l.start_date <= day <= l.end_date
                        for l in leaves
                    )
                    or any(
                        c.employee_id == entry.employee_id
                        and c.work_date == day
                        and c.status == "approved"
                        for c in comp_offs
                    )
                )

                if not blocked:
                    valid.append(entry)

            actual = len(valid)

            if actual < p.minimum_staff:

                typ = (
                    "HOLIDAY_COVERAGE_GAP"
                    if holiday and p.include_holidays
                    else (
                        "UNASSIGNED_REQUIRED_PROCESS"
                        if actual == 0
                        else "COVERAGE_SHORTAGE"
                    )
                )

                add(
                    issues,
                    typ,
                    day,
                    pid=p.id,
                    desc=(
                        f"{p.brand.name} – {p.name}: "
                        f"required staffing {p.minimum_staff}, "
                        f"valid staffing {actual}, "
                        f"shortage {p.minimum_staff - actual}."
                    ),
                    suggestion=(
                        "Assign a qualified, available employee "
                        "or record an authorized exception."
                    ),
                )

    # Save conflicts to database
    for typ, severity, day, eid, pid, desc, suggestion in issues:

        db.add(
            SchedulingConflict(
                roster_id=roster.id,
                conflict_type=typ,
                severity=severity,
                date=day,
                employee_id=eid,
                process_id=pid,
                description=desc,
                suggestion=suggestion,
            )
        )

    db.commit()

    return (
        db.query(SchedulingConflict)
        .filter_by(roster_id=roster.id)
        .order_by(SchedulingConflict.date)
        .all()
    )