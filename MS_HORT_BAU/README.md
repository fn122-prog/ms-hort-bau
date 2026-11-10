# 🌿 MS HORT BAU — Academic Portal

A zero-friction, mobile-first academic portal for Master of Science (M.S.) students and faculty in the **Department of Horticulture, Bangladesh Agricultural University (BAU), Mymensingh**.

---

## 🎯 Purpose & Scope

- **Zero-Login Access**: Instant access via web browser link on any device without account friction.
- **Class Routine**: Day-by-day weekly schedule with automatic "Today's Schedule" highlight (Course Code + Teacher Initials).
- **Course Vault & Teaching Materials**: Organized links to lecture slides, reference books, and lab manuals backed by Google Drive.
- **Deadlines & Reminders**: Visual countdown board for assignments and term papers with 1-click Google/Apple Calendar integration and notification options.
- **No Room Numbers**: Clean layout focusing strictly on subject and teacher initials.

---

## 📁 Directory Structure

```text
MS_HORT_BAU/
├── data/                  # JSON datasets for routine, materials, and deadlines
│   ├── routine.json       # Weekly class schedule (Course + Teacher Initials)
│   ├── materials.json     # Course-wise Google Drive links (Slides, Books, Handouts)
│   ├── deadlines.json     # Assignment topics, due dates, submission instructions
│   └── faculty.json       # Teacher initials to name reference
├── public/                # Static assets, icons, and styling
├── index.html             # High-speed web portal
└── README.md              # Project documentation
```
