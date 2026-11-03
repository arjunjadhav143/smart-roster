from datetime import date

from .models import (
    Pod,
    Employee,
    Brand,
    Process,
    EmployeeAssignment,
    LeaveRequest,
    Holiday,
    CompOff,
)


def seed(db):
    if db.query(Employee).count():
        return

    # Create pods
    pods = [
        Pod(name=name)
        for name in [
            "Customer Success",
            "Revenue Operations",
            "Retention",
            "Fulfilment",
        ]
    ]

    db.add_all(pods)
    db.flush()

    # Create 30 employees
    names = [
        "Aarav Sharma", "Diya Patel", "Vihaan Singh",
        "Ananya Rao", "Arjun Mehta", "Isha Gupta",
        "Kabir Khan", "Meera Nair", "Rohan Das",
        "Sana Ali", "Aditya Roy", "Kavya Iyer",
        "Reyansh Jain", "Priya Shah", "Dev Malhotra",
        "Neha Kapoor", "Ishaan Bose", "Tanya Verma",
        "Rahul Joshi", "Aditi Menon", "Yash Kumar",
        "Nisha Sethi", "Manav Arora", "Riya Bansal",
        "Siddharth Pal", "Pooja Ghosh", "Varun Sinha",
        "Maya Pillai", "Karan Bhat", "Simran Kaur",
    ]

    employees = []

    for i, name in enumerate(names, 1):
        employees.append(
            Employee(
                employee_code=f"E{i:03}",
                full_name=name,
                email=f"e{i:03}@example.com",
                pod_id=pods[(i - 1) % 4].id,
                weekly_off_days=[6] if i % 3 else [5],
                availability=(
                    ["morning", "evening"]
                    if i % 4 == 0
                    else ["morning"]
                ),
            )
        )

    db.add_all(employees)
    db.flush()

    # Assign pod leads
    for i, pod in enumerate(pods):
        pod.lead_id = employees[i].id

    # Create 10 brands
    brand_names = [
        "Aster", "Bloom", "Cove", "Drift", "Ember",
        "Fable", "Grove", "Halo", "Indigo", "Juniper",
    ]

    brands = [
        Brand(
            name=name,
            pod_id=pods[i % 4].id,
            description=f"D2C {name} operations",
        )
        for i, name in enumerate(brand_names)
    ]

    db.add_all(brands)
    db.flush()

    # Create processes
    processes = []

    for i, brand in enumerate(brands):

        if i < 8:
            selected = [
                (
                    "Customer Support" if i % 2 == 0
                    else "Order Management",
                    [0, 1, 2, 3, 4],
                    False,
                )
            ]

        else:
            selected = [
                ("Customer Support", [0, 1, 2, 3, 4, 5, 6], True),
                ("Abandoned Cart", [0, 1, 2, 3, 4, 5], False),
                ("NDR", [0, 1, 2, 3, 4], False),
            ]

        for name, days, holiday in selected:
            processes.append(
                Process(
                    brand_id=brand.id,
                    name=name,
                    working_days=days,
                    include_holidays=holiday,
                    minimum_staff=1,
                    shift="morning",
                )
            )

    db.add_all(processes)
    db.flush()

    # Create employee assignments
    for i, process in enumerate(processes):

        if i < 8:
            db.add(
                EmployeeAssignment(
                    employee_id=employees[i].id,
                    process_id=process.id,
                )
            )

        else:
            for offset in (8, 9, 16):
                db.add(
                    EmployeeAssignment(
                        employee_id=employees[
                            (i + offset) % len(employees)
                        ].id,
                        process_id=process.id,
                    )
                )

    # Create sample leaves, comp-offs and holidays
    db.add_all([
        LeaveRequest(
            employee_id=employees[0].id,
            start_date=date(2026, 11, 8),
            end_date=date(2026, 11, 8),
            leave_type="planned",
            reason="Family event",
            status="approved",
        ),

        LeaveRequest(
            employee_id=employees[3].id,
            start_date=date(2026, 11, 15),
            end_date=date(2026, 11, 16),
            leave_type="sick",
            reason="Medical",
            status="pending",
        ),

        CompOff(
            employee_id=employees[29].id,
            work_date=date(2026, 11, 14),
            reason="Weekend campaign coverage",
        ),

        Holiday(
            name="Diwali",
            date=date(2026, 11, 8),
        ),
    ])

    db.commit()