# BAU MS Horticulture - Google Drive Upload Webhook Setup

This Google Apps Script enables uploading study materials, lecture slides, books, and past exam papers directly into your official Google Drive folders from the web interface, with **automatic rule-based file renaming** and **subfolder creation**.

---

## ⚡ 1-Minute Setup Guide

### Step 1: Open Google Apps Script
1. Open your connected Google Sheet:  
   👉 [BAU MS Horticulture Spreadsheet](https://docs.google.com/spreadsheets/d/1VSTzdOkCTSTRnIwS6kTJ1rLDnNaJAyAYAMBCl3Zf8s8)
2. In the top menu, click **Extensions** > **Apps Script**.

### Step 2: Paste the Code
1. Delete any existing code in the editor (`function myFunction() { ... }`).
2. Copy and paste the entire contents of [`Code.gs`](./Code.gs) into the editor.
3. Click the **Save** (💾 floppy disk) icon.

### Step 3: Deploy as Web App
1. At the top right, click **Deploy** > **New deployment**.
2. Click the gear icon (**Select type**) next to "Select type" and select **Web app**.
3. Fill in the fields:
   - **Description**: `BAU MS Hort Drive Uploader`
   - **Execute as**: `Me (your_email@gmail.com)`
   - **Who has access**: `Anyone` *(crucial so your web app frontend can send files)*
4. Click **Deploy**.
5. When Google asks to authorize permissions:
   - Click **Authorize access**.
   - Choose your Google account.
   - Click **Advanced** > **Go to Untitled project (unsafe)** (standard for personal Apps Scripts).
   - Click **Allow**.

### Step 4: Copy & Paste the URL
1. Copy the **Web App URL** (looks like: `https://script.google.com/macros/s/AKfycb.../exec`).
2. Go to your portal [ms-hort-bau.vercel.app](https://ms-hort-bau.vercel.app) or local.
3. Click **Upload Material** in the *Materials Vault* section.
4. Paste the URL into the **Webhook URL** field (under *⚙️ Webhook Connection Settings* - it saves automatically to your browser for all future uploads).
5. Enter the **Batch Passcode** (the first 6 digits of MS ID) to verify your upload.

---

## 📁 Live Folder Synchronization
* When you pick any course in the portal uploader, it automatically queries Google Drive (`doGet`) and displays all existing and newly created folders in the dropdown.
* You can also click the **🔄** icon next to *Folder Location* to immediately sync all folders from Google Drive.
* If you ever create a folder in Google Drive manually, clicking **🔄** brings it directly into the portal's dropdown.

---

## 🔒 Batch Upload Passcode
* Only classmates who know the passcode (first 6 digits of MS ID) can upload files.
* This prevents unauthorized internet traffic or web scrapers from adding spam to your Drive.
* If you ever wish to change or remove the passcode, simply edit `const SECRET_PASSCODE = "262020";` at line 24 of `Code.gs` and re-deploy.

---

## 🏷️ Auto-Renaming Rule
When you select a course and type of material, each file automatically gets renamed:
* **Single File:** `[CourseCode]_[Type]_[Title]_[YYYYMMDD].[ext]`
* **Multiple Files (Batch):** `[CourseCode]_[Type]_[Title]_Part01_[YYYYMMDD].[ext]`, `...Part02...`
* **If Title is omitted:** Preserves original clean filename: `[CourseCode]_[Type]_[OriginalName]_[YYYYMMDD].[ext]`

*Examples:*
* `HORT501_Lecture_Advanced_Fruit_Physiology_20261111.pdf`
* `HORT505_Lecture_Biometrics_Part01_20261111.pdf`
* `HORT505_Lecture_Biometrics_Part02_20261111.pdf`
* `EXAM_PastQues_Midterm_2025.pdf`
* `EXAM_Questions_Midterm_2025.pdf`
