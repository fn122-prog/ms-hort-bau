# 📊 Google Sheet Backend Guide for MS Horticulture Hub

This guide explains how to connect and maintain the **Google Sheet backend** so any class cancellations, rescheduling, teacher reassignments, or assignment updates sync automatically to the live portal without editing any code.

---

## 🚀 2-Minute Quick Setup

### Step 1: Create a Google Sheet
1. Open Google Sheets (`sheets.new`) in your Google Drive.
2. Title it: **`BAU_MS_Horticulture_Routine_Backend`**.
3. Create two tabs at the bottom:
   * **Tab 1**: `Routine`
   * **Tab 2**: `Deadlines`

---

### Step 2: Paste the Template Data

#### Tab 1: `Routine`
Copy and paste this table into cell **A1** of the `Routine` tab:

```csv
Day,Slot,Course,Teacher,Type,Note
Sunday,slot_1,Hort. 503,MHrR,Compulsory,
Sunday,slot_2,Hort. 505,MKH,Compulsory,
Sunday,slot_3,Hort. 501,TH,Compulsory,
Sunday,slot_4,Hort. 523,MHrR,Elective,
Sunday,slot_5,Hort. 517,MMH,Elective,
Monday,slot_1,Hort. 503,MHR,Compulsory,
Monday,slot_2,Hort. 505,MRK,Compulsory,
Monday,slot_3,Hort. 501,MAR,Compulsory,
Monday,slot_4,Hort. 507,MMH,Compulsory,
Monday,slot_5_6,Hort. 502,MHR/MKH,Compulsory,1:30 to 3:25 PM (Double slot)
Tuesday,slot_1,Hort. 525,MRK,Elective,
Tuesday,slot_2,Hort. 507,MAI,Compulsory,
Tuesday,slot_3,Hort. 521,MAR,Elective,
Tuesday,slot_4,Hort. 523,MKH,Elective,
Tuesday,slot_5,Hort. 519,TH,Elective,
Wednesday,slot_1,Hort. 517,MAI,Elective,
Wednesday,slot_2,Hort. 519,MAR,Elective,
Wednesday,slot_3,Hort. 521,MHR,Elective,
Wednesday,slot_4,Hort. 525,MMH,Elective,
Thursday,all_day,Seminar / Workshop,Dept. Faculty,Academic,Weekly Seminar & Workshop
```

* **Slot Reference**:
  * `slot_1` = 09:00 – 09:55 AM
  * `slot_2` = 10:00 – 10:55 AM
  * `slot_3` = 11:00 – 11:55 AM
  * `slot_4` = 12:00 – 12:55 PM
  * `slot_5` = 01:30 – 02:25 PM
  * `slot_6` = 02:30 – 03:25 PM
  * `slot_5_6` = 01:30 – 03:25 PM (Double class)

---

#### Tab 2: `Deadlines`
Copy and paste this table into cell **A1** of the `Deadlines` tab:

```csv
Course_Code,Title,Category,Submission_To,Deadline,Instructions
HORT503,Comparative Analysis of Protected Cultivation Systems,Group Specific,Dr. Md. Harun Ar Rashid,2026-12-07 23:59,Submit group report via CR
HORT501,Physiological Mechanisms of Stress Tolerance in Tropical Fruits,General Title,Dr. Md. Azizur Rahman,2026-12-15 23:59,Individual literature synthesis
```

---

### Step 3: Set Share Permissions
1. Click the green **Share** button in the top-right of your Google Sheet.
2. Under **General access**, select **"Anyone with the link"** and leave role as **"Viewer"**.
3. Copy the link.

---

### Step 4: Connect to the Portal
1. Open the portal in your browser (`http://localhost:8082` or your live URL).
2. Click the **"Google Sheet Synced"** button in the top right.
3. Paste your Google Sheet URL (or ID) and click **"Save & Sync"**.

🎉 **That's it!** Whenever classes are swapped, rescheduled, or cancelled in the Google Sheet on your phone or laptop, the live portal updates automatically on page load!
