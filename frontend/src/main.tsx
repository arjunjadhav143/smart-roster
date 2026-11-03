import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  LayoutDashboard,
  CalendarDays,
  Users,
  Building2,
  AlertTriangle,
  RefreshCw,
} from "lucide-react";
import "./styles.css";

const api = import.meta.env.VITE_API_URL || "http://localhost:8000";

const request = async (path: string, init?: RequestInit) => {
  const r = await fetch(api + path, init);

  if (!r.ok) {
    throw new Error(await r.text());
  }

  return r.json();
};

const get = (path: string) => request(path);

type Entry = {
  id: number;
  employee_id: number;
  employee: string;
  pod?: string;
  process?: string;
  brand?: string;
  process_id?: number;
  work_date: string;
  status: string;
  shift?: string;
};

function App() {
  const [page, setPage] = useState("Overview");
  const [dash, setDash] = useState<any>();
  const [items, setItems] = useState<any[]>([]);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [roster, setRoster] = useState<any>();
  const [entries, setEntries] = useState<Entry[]>([]);

  const load = async () => {
    try {
      setNotice("");

      if (page === "Overview") {
        setDash(await get("/dashboard"));
        return;
      }

      if (page === "Monthly Roster") {
        const rs = await get("/rosters");

        setItems(rs);

        if (rs[0]) {
          setRoster(rs[0]);
          setEntries(await get(`/rosters/${rs[0].id}/entries`));
        } else {
          setRoster(undefined);
          setEntries([]);
        }

        return;
      }

      const paths: Record<string, string> = {
        Employees: "employees",
        Brands: "brands",
        Processes: "processes",
        "Pods & Teams": "pods",
        Assignments: "assignments",
        "Leave Management": "leaves",
        "Comp Offs": "comp-offs",
        Holidays: "holidays",
        "Conflicts & Alerts": "conflicts",
      };

      if (paths[page]) {
        setItems(await get("/" + paths[page]));
      }
    } catch (e) {
      setNotice(
        `Cannot connect to API (${api}). Check that the backend is running and CORS is configured.`
      );
    }
  };

  useEffect(() => {
    void load();
  }, [page]);

  const generate = async () => {
    setBusy(true);

    try {
      const n = new Date();

      const out = await request("/rosters/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          year: n.getFullYear(),
          month: n.getMonth() + 1,
        }),
      });

      setNotice(
        out.status === "infeasible"
          ? `Roster is infeasible: ${
              out.issues?.length || 0
            } requirement(s) cannot be staffed.`
          : `Draft created: ${out.entries} assignments, ${out.conflicts} conflict(s).`
      );

      await load();
    } catch (e: any) {
      setNotice(`Generation failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  const nav: [string, any][] = [
    ["Overview", LayoutDashboard],
    ["Monthly Roster", CalendarDays],
    ["Employees", Users],
    ["Brands", Building2],
    ["Processes", Building2],
    ["Pods & Teams", Users],
    ["Assignments", Users],
    ["Leave Management", CalendarDays],
    ["Comp Offs", CalendarDays],
    ["Holidays", CalendarDays],
    ["Conflicts & Alerts", AlertTriangle],
  ];

  return (
    <div className="app">
      <aside>
        <div className="logo">
          roster<span>flow</span>
        </div>

        <small>OPERATIONS PLATFORM</small>

        {nav.map(([name, Icon]) => (
          <button
            key={name}
            className={page === name ? "active" : ""}
            onClick={() => setPage(name)}
          >
            <Icon size={18} />
            {name}
          </button>
        ))}
      </aside>

      <main>
        <header>
          <div>
            <p className="eyebrow">WORKFORCE INTELLIGENCE</p>
            <h1>{page}</h1>
          </div>

          <div className="header-actions">
            <button onClick={() => void load()}>
              <RefreshCw size={16} />
              Refresh
            </button>

            {page === "Monthly Roster" && (
              <button
                className="primary"
                disabled={busy}
                onClick={() => void generate()}
              >
                {busy ? "Generating…" : "Generate current month"}
              </button>
            )}
          </div>
        </header>

        {notice && (
          <div className="notice">
            {notice}
            <button onClick={() => setNotice("")}>×</button>
          </div>
        )}

        {page === "Overview" ? (
          <Overview d={dash} />
        ) : page === "Monthly Roster" ? (
          <RosterCalendar
            roster={roster}
            entries={entries}
            reload={load}
            notice={setNotice}
          />
        ) : (
          <Manager
            title={page}
            rows={items}
            reload={load}
            notice={setNotice}
          />
        )}
      </main>
    </div>
  );
}

function Overview({ d }: { d: any }) {
  if (!d) {
    return (
      <section className="panel">
        <p>Loading operations metrics…</p>
      </section>
    );
  }

  const cards = [
    ["Total Employees", d.total_employees],
    ["Brands", d.total_brands],
    ["Operational Pods", d.total_pods],
    ["Processes", d.total_processes],
    ["Working Today", d.employees_working_today],
    ["On Approved Leave", d.employees_on_leave_today],
    ["Coverage Gaps", d.coverage_gaps],
    ["Pending Drafts", d.pending_roster_approvals],
  ];

  return (
    <>
      <section className="cards">
        {cards.map(([name, value]) => (
          <article key={String(name)}>
            <span>{name}</span>
            <strong>{value}</strong>
          </article>
        ))}
      </section>

      <section className="panel">
        <h2>Live operational data</h2>
        <p>
          Metrics are calculated from database records. Generate and validate a
          draft before publication; server-side validation remains
          authoritative.
        </p>
      </section>
    </>
  );
}

function RosterCalendar({
  roster,
  entries,
  reload,
  notice,
}: {
  roster: any;
  entries: Entry[];
  reload: () => Promise<void>;
  notice: (x: string) => void;
}) {
  const [filter, setFilter] = useState("");
  const [scope, setScope] = useState("company");
  const [selected, setSelected] = useState<Entry | null>(null);
  const [status, setStatus] = useState("working");
  const [backups, setBackups] = useState<any[]>([]);

  // Get available values for the selected view
const getScopeValues = (selectedScope: string) => {
  const values = entries.map((e) => {
    if (selectedScope === "pod") return e.pod;
    if (selectedScope === "brand") return e.brand;
    if (selectedScope === "process") return e.process;
    if (selectedScope === "employee") return e.employee;
    return null;
  });

  return Array.from(new Set(values.filter(Boolean)))
    .map(String)
    .sort();
};

const scopeValues = useMemo(
  () => getScopeValues(scope),
  [entries, scope]
);

// Filter roster entries according to selected view
const scoped = useMemo(() => {
  if (scope === "company") return entries;

  if (!filter) return entries;

  return entries.filter((e) => {
    let value = "";

    if (scope === "pod") value = e.pod || "";
    if (scope === "brand") value = e.brand || "";
    if (scope === "process") value = e.process || "";
    if (scope === "employee") value = e.employee || "";

    return String(value) === filter;
  });
}, [entries, scope, filter]);

// Display employees belonging to the filtered roster
const employees = useMemo(
  () =>
    Array.from(
      new Map(
        scoped.map((e) => [e.employee_id, e.employee])
      ).entries()
    ),
  [scoped]
);

  const days = useMemo(
    () =>
      roster
        ? Array.from(
            {
              length: new Date(
                roster.year,
                roster.month,
                0
              ).getDate(),
            },
            (_, i) =>
              `${roster.year}-${String(roster.month).padStart(2, "0")}-${String(
                i + 1
              ).padStart(2, "0")}`
          )
        : [],
    [roster]
  );

  const edit = async () => {
    if (!selected || !roster) return;

    try {
      await request(
        `/rosters/${roster.id}/entries/${selected.id}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ status }),
        }
      );

      const check = await request(
        `/rosters/${roster.id}/validate`,
        {
          method: "POST",
        }
      );

      notice(
        `Change saved and revalidated: ${check.total_conflicts} conflict(s), ${check.critical} critical.`
      );

      setSelected(null);
      setBackups([]);

      await reload();
    } catch (e: any) {
      notice(`Change could not be saved: ${e.message}`);
    }
  };

  const validate = async () => {
    if (!roster) return;

    try {
      const r = await request(
        `/rosters/${roster.id}/validate`,
        {
          method: "POST",
        }
      );

      notice(
        r.valid
          ? "Roster is valid."
          : `Roster has ${r.total_conflicts} conflict(s), including ${r.critical} critical.`
      );
    } catch (e: any) {
      notice(`Validation failed: ${e.message}`);
    }
  };

  const publish = async () => {
    if (!roster) return;

    try {
      await request(`/rosters/${roster.id}/publish`, {
        method: "POST",
      });

      notice("Roster published.");

      await reload();
    } catch (e: any) {
      notice(`Publishing blocked: ${e.message}`);
    }
  };

  const recommend = async () => {
    if (!selected?.process_id) return;

    try {
      setBackups(
        await request(
          `/rosters/${roster.id}/recommend-backup?process_id=${selected.process_id}&work_date=${selected.work_date}`,
          {
            method: "POST",
          }
        )
      );
    } catch (e: any) {
      notice(`Could not find backups: ${e.message}`);
    }
  };

  const exportCsv = () => {
    if (!roster) return;

    const header = [
      "Employee",
      "Pod",
      "Brand",
      "Process",
      "Date",
      "Status",
      "Shift",
    ];

    const quote = (v: any) =>
      `"${String(v ?? "").replaceAll('"', '""')}"`;

    const csv = [
      header,
      ...entries.map((e) => [
        e.employee,
        e.pod,
        e.brand,
        e.process,
        e.work_date,
        e.status,
        e.shift,
      ]),
    ]
      .map((row) => row.map(quote).join(","))
      .join("\n");

    const url = URL.createObjectURL(
      new Blob([csv], { type: "text/csv" })
    );

    const a = document.createElement("a");
    a.href = url;
    a.download = `roster-${roster.year}-${String(
      roster.month
    ).padStart(2, "0")}.csv`;

    a.click();

    URL.revokeObjectURL(url);
  };

  if (!roster) {
    return (
      <section className="panel">
        <h2>No roster yet</h2>
        <p>
          Generate a monthly draft to open the calendar and editor.
        </p>
      </section>
    );
  }

  return (
    <>
      <section className="panel toolbar">
        <strong>
          {roster.year}-{String(roster.month).padStart(2, "0")} ·{" "}
          {roster.status}
        </strong>

        <select
  aria-label="Roster view"
  value={scope}
  onChange={(e) => {
    const nextScope = e.target.value;

    setScope(nextScope);

    // Automatically select the first available group
    const values = getScopeValues(nextScope);

    setFilter(
      nextScope === "company"
        ? ""
        : values[0] || ""
    );
  }}
>
  <option value="company">Company-wide view</option>
  <option value="pod">Pod-wise view</option>
  <option value="brand">Brand-wise view</option>
  <option value="process">Process-wise view</option>
  <option value="employee">Employee-wise view</option>
</select>

{scope !== "company" && (
  <select
    aria-label="Select roster group"
    value={filter}
    onChange={(e) => setFilter(e.target.value)}
  >
    <option value="">All {scope}s</option>

    {scopeValues.map((value) => (
      <option key={value} value={value}>
        {value}
      </option>
    ))}
  </select>
)}

        <button onClick={() => void validate()}>
          Validate
        </button>

        <button onClick={exportCsv}>
          Export CSV
        </button>

        {roster.status !== "published" && (
          <button
            className="primary"
            onClick={() => void publish()}
          >
            Publish roster
          </button>
        )}
      </section>

      <section className="panel calendar-wrap">
        <p className="hint">
          Switch between company, pod, brand, process and employee
          views. Click any roster entry to edit it or find backup
          resources.
        </p>

        <table className="calendar">
          <thead>
            <tr>
              <th>Employee</th>

              {days.map((day) => (
                <th key={day}>
                  {day.slice(8)}
                  <small>
                    {new Date(day + "T12:00:00").toLocaleDateString(
                      undefined,
                      {
                        weekday: "short",
                      }
                    )}
                  </small>
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {employees.map(([id, name]) => (
              <tr key={String(id)}>
                <th>{String(name)}</th>

                {days.map((day) => {
                  const rows = scoped.filter(
                    (x) =>
                      x.employee_id === id &&
                      String(x.work_date).slice(0, 10) === day
                  );

                  const entry = rows[0];

                  return (
                    <td
                      key={day}
                      className={`cell ${
                        entry?.status || "empty"
                      }`}
                      onClick={() => {
                        if (entry) {
                          setSelected(entry);
                          setStatus(entry.status);
                          setBackups([]);
                        }
                      }}
                    >
                      {entry ? (
                        <>
                          <b>
                            {entry.status === "working"
                              ? "Working"
                              : entry.status}
                          </b>

                          <span>
                            {entry.brand || ""}
                            {entry.process
                              ? ` · ${entry.process}`
                              : ""}
                          </span>
                        </>
                      ) : (
                        <span>—</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {selected && (
        <div className="modal-backdrop">
          <section className="modal form-modal">
            <h2>Edit roster entry</h2>

            <p>
              <strong>{selected.employee}</strong>
              <br />
              {selected.work_date}
              <br />
              {selected.brand} / {selected.process}
            </p>

            <label>
              Status

              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                <option value="working">Working</option>
                <option value="weekly_off">Weekly Off</option>
                <option value="leave">Leave</option>
                <option value="not_assigned">
                  Not assigned
                </option>
              </select>
            </label>

            <button
              className="btn btn-warning"
              onClick={() => void recommend()}
            >
              Find backup resources
            </button>

            {backups.length > 0 && (
              <ul>
                {backups.slice(0, 4).map((b) => (
                  <li key={b.employee_id}>
                    <strong>{b.name}</strong> — {b.reason}
                  </li>
                ))}
              </ul>
            )}

            <p className="hint">
              Saving triggers independent full-roster validation.
              Publishing remains blocked by critical conflicts.
            </p>

            <div className="form-actions">
              <button
                onClick={() => {
                  setSelected(null);
                  setBackups([]);
                }}
              >
                Cancel
              </button>

              <button
                className="primary"
                onClick={() => void edit()}
              >
                Save & revalidate
              </button>
            </div>
          </section>
        </div>
      )}
    </>
  );
}

type Field = {
  key: string;
  label: string;
  type?: "text" | "number" | "date" | "checkbox" | "select";
  required?: boolean;
  options?: {
    label: string;
    value: any;
  }[];
};

const endpoint: Record<string, string> = {
  Employees: "employees",
  Brands: "brands",
  Processes: "processes",
  "Pods & Teams": "pods",
  Assignments: "assignments",
  "Leave Management": "leaves",
  "Comp Offs": "comp-offs",
  Holidays: "holidays",
};

const labels = (
  rows: any[],
  name: (row: any) => string
) =>
  rows.map((x) => ({
    value: x.id,
    label: name(x),
  }));

function fieldsFor(
  title: string,
  data: {
    employees: any[];
    pods: any[];
    brands: any[];
    processes: any[];
  }
): Field[] {
  const employee = labels(
    data.employees,
    (x) => x.full_name
  );

  const pod = [
    {
      value: "",
      label: "No pod",
    },
    ...labels(data.pods, (x) => x.name),
  ];

  const brand = labels(
    data.brands,
    (x) => x.name
  );

  const process = labels(
    data.processes,
    (x) => `${x.brand || ""} · ${x.name}`
  );

  if (title === "Employees") {
    return [
      {
        key: "employee_code",
        label: "Employee code",
        required: true,
      },
      {
        key: "full_name",
        label: "Full name",
        required: true,
      },
      {
        key: "email",
        label: "Email",
        required: true,
      },
      {
        key: "job_title",
        label: "Job title",
      },
      {
        key: "pod_id",
        label: "Pod",
        type: "select",
        options: pod,
      },
      {
        key: "max_weekly_hours",
        label: "Max weekly hours",
        type: "number",
      },
      {
        key: "weekly_off_days",
        label: "Weekly off days (0-6, comma separated)",
      },
      {
        key: "availability",
        label: "Available shifts (comma separated)",
      },
    ];
  }

  if (title === "Brands") {
    return [
      {
        key: "name",
        label: "Brand name",
        required: true,
      },
      {
        key: "description",
        label: "Description",
      },
      {
        key: "pod_id",
        label: "Owning pod",
        type: "select",
        options: pod,
      },
    ];
  }

  if (title === "Processes") {
    return [
      {
        key: "brand_id",
        label: "Brand",
        type: "select",
        required: true,
        options: brand,
      },
      {
        key: "name",
        label: "Process name",
        required: true,
      },
      {
        key: "description",
        label: "Description",
      },
      {
        key: "minimum_staff",
        label: "Minimum staff",
        type: "number",
      },
      {
        key: "working_days",
        label: "Working days (0-6, comma separated)",
      },
      {
        key: "include_holidays",
        label: "Include public holidays",
        type: "checkbox",
      },
      {
        key: "shift",
        label: "Shift",
      },
    ];
  }

  if (title === "Pods & Teams") {
    return [
      {
        key: "name",
        label: "Pod name",
        required: true,
      },
      {
        key: "lead_id",
        label: "Pod lead",
        type: "select",
        options: [
          {
            value: "",
            label: "No lead",
          },
          ...employee,
        ],
      },
    ];
  }

  if (title === "Assignments") {
    return [
      {
        key: "employee_id",
        label: "Employee",
        type: "select",
        required: true,
        options: employee,
      },
      {
        key: "process_id",
        label: "Process",
        type: "select",
        required: true,
        options: process,
      },
      {
        key: "qualified",
        label: "Qualified",
        type: "checkbox",
      },
      {
        key: "priority",
        label: "Priority",
        type: "number",
      },
    ];
  }

  if (title === "Leave Management") {
    return [
      {
        key: "employee_id",
        label: "Employee",
        type: "select",
        required: true,
        options: employee,
      },
      {
        key: "start_date",
        label: "Start date",
        type: "date",
        required: true,
      },
      {
        key: "end_date",
        label: "End date",
        type: "date",
        required: true,
      },
      {
        key: "leave_type",
        label: "Leave type",
        required: true,
      },
      {
        key: "reason",
        label: "Reason",
      },
      {
        key: "status",
        label: "Status",
        type: "select",
        options: [
          {
            value: "pending",
            label: "Pending",
          },
          {
            value: "approved",
            label: "Approved",
          },
          {
            value: "rejected",
            label: "Rejected",
          },
          {
            value: "cancelled",
            label: "Cancelled",
          },
        ],
      },
    ];
  }

  if (title === "Comp Offs") {
    return [
      {
        key: "employee_id",
        label: "Employee",
        type: "select",
        required: true,
        options: employee,
      },
      {
        key: "work_date",
        label: "Work date",
        type: "date",
        required: true,
      },
      {
        key: "reason",
        label: "Reason",
      },
      {
        key: "status",
        label: "Status",
        type: "select",
        options: [
          {
            value: "approved",
            label: "Approved",
          },
          {
            value: "cancelled",
            label: "Cancelled",
          },
        ],
      },
    ];
  }

  if (title === "Holidays") {
    return [
      {
        key: "name",
        label: "Holiday name",
        required: true,
      },
      {
        key: "holiday_date",
        label: "Holiday date",
        type: "date",
        required: true,
      },
      {
        key: "brand_id",
        label: "Brand",
        type: "select",
        options: [
          {
            value: "",
            label: "Global holiday",
          },
          ...brand,
        ],
      },
    ];
  }

  return [];
}

function formValue(v: any) {
  return Array.isArray(v) ? v.join(",") : v ?? "";
}

function payloadFor(title: string, values: any) {
  const p: Record<string, any> = {};

  Object.keys(values).forEach((key) => {
    const value = values[key];

    if (
      ["weekly_off_days", "working_days"].includes(key)
    ) {
      p[key] = String(value)
        .split(",")
        .map((x: string) => Number(x.trim()))
        .filter(
          (x: number) =>
            Number.isInteger(x) &&
            x >= 0 &&
            x <= 6
        );
    } else if (key === "availability") {
      p[key] = String(value)
        .split(",")
        .map((x: string) => x.trim())
        .filter(Boolean);
    } else if (
      [
        "pod_id",
        "lead_id",
        "brand_id",
        "employee_id",
        "process_id",
        "minimum_staff",
        "max_weekly_hours",
        "priority",
      ].includes(key)
    ) {
      p[key] =
        value === "" || value === null
          ? null
          : Number(value);
    } else {
      p[key] = value;
    }
  });

  if (title === "Employees") {
    p.max_weekly_hours ??= 48;
    p.job_title ||= "Operations Associate";
    p.availability ??= ["morning"];
    p.weekly_off_days ??= [5, 6];
  }

  if (title === "Processes") {
    p.minimum_staff ??= 1;
    p.working_days ??= [0, 1, 2, 3, 4];
    p.shift ||= "morning";
    p.include_holidays ??= false;
  }

  if (title === "Assignments") {
    p.priority ??= 1;
    p.qualified ??= false;
  }

  if (title === "Holidays") {
    if (p.brand_id === null) {
      p.brand_id = null;
    }
  }

  return p;
}

function singularTitle(title: string) {
  const map: Record<string, string> = {
    Employees: "employee",
    Brands: "brand",
    Processes: "process",
    "Pods & Teams": "pod",
    Assignments: "assignment",
    "Leave Management": "leave",
    "Comp Offs": "comp-off",
    Holidays: "holiday",
    "Conflicts & Alerts": "conflict",
  };

  return map[title] || title;
}

function Manager({
  title,
  rows,
  reload,
  notice,
}: {
  title: string;
  rows: any[];
  reload: () => Promise<void>;
  notice: (x: string) => void;
}) {
  const [editing, setEditing] =
    useState<any | null>(null);

  const [data, setData] = useState({
    employees: [],
    pods: [],
    brands: [],
    processes: [],
  } as any);

  const [saving, setSaving] = useState(false);

  const editable = Boolean(endpoint[title]);

  useEffect(() => {
    if (!editable) return;

    Promise.all([
      get("/employees"),
      get("/pods"),
      get("/brands"),
      get("/processes"),
    ])
      .then(
        ([
          employees,
          pods,
          brands,
          processes,
        ]) => {
          setData({
            employees,
            pods,
            brands,
            processes,
          });
        }
      )
      .catch(() => {});
  }, [title, editable]);

  const fs = editable
    ? fieldsFor(title, data)
    : [];

  const open = (row?: any) => {
    if (row) {
      setEditing({
        ...row,
      });

      return;
    }

    const initial: Record<string, any> = {};

    fs.forEach((field) => {
      if (field.type === "checkbox") {
        initial[field.key] =
          field.key === "qualified" ||
          field.key === "include_holidays"
            ? false
            : false;
      } else if (
        field.key === "max_weekly_hours"
      ) {
        initial[field.key] = 48;
      } else if (
        field.key === "minimum_staff"
      ) {
        initial[field.key] = 1;
      } else if (field.key === "priority") {
        initial[field.key] = 1;
      } else if (field.key === "status") {
        if (title === "Leave Management") {
          initial[field.key] = "pending";
        } else {
          initial[field.key] = "approved";
        }
      } else {
        initial[field.key] = "";
      }
    });

    setEditing(initial);
  };

  const save = async () => {
    if (!editing) return;

    setSaving(true);

    try {
      const body = payloadFor(
        title,
        editing
      );

      await request(
        `/${endpoint[title]}${
          editing.id ? `/${editing.id}` : ""
        }`,
        {
          method: editing.id
            ? "PUT"
            : "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify(body),
        }
      );

      setEditing(null);

      notice(
        `${singularTitle(title)} ${
          editing.id
            ? "updated"
            : "created"
        } successfully.`
      );

      await reload();
    } catch (e: any) {
      notice(
        `Could not save ${singularTitle(
          title
        )}: ${e.message}`
      );
    } finally {
      setSaving(false);
    }
  };

  const remove = async (row: any) => {
    const entity = singularTitle(title);

    const confirmed = confirm(
      `Are you sure you want to ${
        title === "Employees" ||
        title === "Brands"
          ? "deactivate"
          : "delete"
      } this ${entity}?`
    );

    if (!confirmed) return;

    try {
      await request(
        `/${endpoint[title]}/${row.id}`,
        {
          method: "DELETE",
        }
      );

      notice(
        title === "Employees"
          ? "Employee deactivated successfully."
          : title === "Brands"
          ? "Brand deactivated successfully."
          : `${entity} deleted successfully.`
      );

      await reload();
    } catch (e: any) {
      notice(
        `Could not remove ${entity}: ${e.message}`
      );
    }
  };

  const changeEmployeeStatus = async (
    row: any,
    active: boolean
  ) => {
    try {
      await request(
        `/employees/${row.id}/status`,
        {
          method: "PATCH",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            active,
          }),
        }
      );

      notice(
        active
          ? "Employee reactivated successfully."
          : "Employee deactivated successfully."
      );

      await reload();
    } catch (e: any) {
      notice(
        `Could not update employee status: ${e.message}`
      );
    }
  };

  const leaveAction = async (
    row: any,
    action: string
  ) => {
    try {
      await request(
        `/leaves/${row.id}/${action}`,
        {
          method: "POST",
        }
      );

      notice(
        `Leave ${action}ed successfully.`
      );

      await reload();
    } catch (e: any) {
      notice(
        `Could not update leave: ${e.message}`
      );
    }
  };

  const cols = rows.length
    ? Object.keys(rows[0]).filter(
        (key) =>
          ![
            "id",
            "employee_id",
            "process_id",
            "brand_id",
            "pod_id",
            "lead_id",
          ].includes(key)
      )
    : [];

  return (
    <>
      <section className="panel">
        <div className="panel-title">
          <div>
            <h2>
              {title}{" "}
              <em>
                {rows.length} records
              </em>
            </h2>

            <p>
              {editable
                ? "Create, edit, and manage live operational records."
                : "Conflict records are generated by the validator and cannot be manually edited."}
            </p>
          </div>

          {editable && (
            <button
              className="primary"
              onClick={() => open()}
            >
              + Add{" "}
              {singularTitle(title)}
            </button>
          )}
        </div>

        {rows.length ? (
          <div className="tablewrap">
            <table>
              <thead>
                <tr>
                  {cols.map((column) => (
                    <th key={column}>
                      {column
                        .replaceAll(
                          "_",
                          " "
                        )
                        .replace(
                          /^\w/,
                          (c) =>
                            c.toUpperCase()
                        )}
                    </th>
                  ))}

                  {editable && (
                    <th>Actions</th>
                  )}
                </tr>
              </thead>

              <tbody>
                {rows.map((row, index) => (
                  <tr
                    key={
                      row.id ??
                      index
                    }
                  >
                    {cols.map((column) => (
                      <td
                        key={column}
                      >
                        {typeof row[
                          column
                        ] ===
                        "object"
                          ? JSON.stringify(
                              row[
                                column
                              ]
                            )
                          : String(
                              row[
                                column
                              ] ??
                                "—"
                            )}
                      </td>
                    ))}

                    {editable && (
                      <td className="row-actions">
                        <button
                          onClick={() =>
                            open(row)
                          }
                        >
                          Edit
                        </button>

                        {title ===
                          "Employees" && (
                          <>
                            {row.active ===
                            false ? (
                              <button
                                className="btn-success"
                                onClick={() =>
                                  void changeEmployeeStatus(
                                    row,
                                    true
                                  )
                                }
                              >
                                Reactivate
                              </button>
                            ) : (
                              <button
                                className="btn-warning"
                                onClick={() =>
                                  void changeEmployeeStatus(
                                    row,
                                    false
                                  )
                                }
                              >
                                Deactivate
                              </button>
                            )}
                          </>
                        )}

                        {title ===
                          "Leave Management" &&
                          row.status ===
                            "pending" && (
                            <>
                              <button
                                className="btn-success"
                                onClick={() =>
                                  void leaveAction(
                                    row,
                                    "approve"
                                  )
                                }
                              >
                                Approve
                              </button>

                              <button
                                className="btn-warning"
                                onClick={() =>
                                  void leaveAction(
                                    row,
                                    "reject"
                                  )
                                }
                              >
                                Reject
                              </button>
                            </>
                          )}

                        {title ===
                          "Leave Management" &&
                          row.status !==
                            "cancelled" && (
                            <button
                              className="btn-warning"
                              onClick={() =>
                                void leaveAction(
                                  row,
                                  "cancel"
                                )
                              }
                            >
                              Cancel
                            </button>
                          )}

                        <button
                          className="danger"
                          onClick={() =>
                            void remove(row)
                          }
                        >
                          {title ===
                          "Employees"
                            ? "Deactivate"
                            : title ===
                              "Brands"
                            ? "Deactivate"
                            : "Delete"}
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <h3>No records found</h3>

            {editable && (
              <p>
                Click{" "}
                <strong>
                  + Add{" "}
                  {singularTitle(
                    title
                  )}
                </strong>{" "}
                to create the first
                record.
              </p>
            )}
          </div>
        )}
      </section>

      {editing && (
        <div className="modal-backdrop">
          <section className="modal form-modal">
            <div className="form-modal-header">
              <h2>
                {editing.id
                  ? "Edit"
                  : "Add"}{" "}
                {singularTitle(title)}
              </h2>

              <button
                className="close-btn"
                onClick={() =>
                  setEditing(null)
                }
              >
                ×
              </button>
            </div>

            <div className="form-grid">
              {fs.map((field) => (
                <label
                  key={field.key}
                  className={
                    field.type ===
                    "checkbox"
                      ? "checkbox-field"
                      : ""
                  }
                >
                  {field.type ===
                  "checkbox" ? (
                    <>
                      <input
                        type="checkbox"
                        checked={Boolean(
                          editing[
                            field.key
                          ]
                        )}
                        onChange={(e) =>
                          setEditing({
                            ...editing,
                            [field.key]:
                              e.target
                                .checked,
                          })
                        }
                      />

                      <span>
                        {field.label}
                      </span>
                    </>
                  ) : (
                    <>
                      <span>
                        {field.label}
                      </span>

                      {field.type ===
                      "select" ? (
                        <select
                          required={
                            field.required
                          }
                          value={formValue(
                            editing[
                              field.key
                            ]
                          )}
                          onChange={(e) =>
                            setEditing({
                              ...editing,
                              [field.key]:
                                e.target
                                  .value,
                            })
                          }
                        >
                          {field.options?.map(
                            (option) => (
                              <option
                                key={String(
                                  option.value
                                )}
                                value={
                                  option.value
                                }
                              >
                                {
                                  option.label
                                }
                              </option>
                            )
                          )}
                        </select>
                      ) : (
                        <input
                          required={
                            field.required
                          }
                          type={
                            field.type ||
                            "text"
                          }
                          value={formValue(
                            editing[
                              field.key
                            ]
                          )}
                          onChange={(e) =>
                            setEditing({
                              ...editing,
                              [field.key]:
                                e.target
                                  .value,
                            })
                          }
                        />
                      )}
                    </>
                  )}
                </label>
              ))}
            </div>

            <div className="form-actions">
              <button
                onClick={() =>
                  setEditing(null)
                }
              >
                Cancel
              </button>

              <button
                className="primary"
                disabled={saving}
                onClick={() =>
                  void save()
                }
              >
                {saving
                  ? "Saving…"
                  : editing.id
                  ? "Update"
                  : "Create"}
              </button>
            </div>
          </section>
        </div>
      )}
    </>
  );
}

createRoot(
  document.getElementById("root")!
).render(<App />);