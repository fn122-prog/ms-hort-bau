/**
 * 🌿 Google Drive Smart Cloner & Auto-Renamer for BAU MS Horticulture
 *
 * Source Folder: MS in Horticulture (Oct-Mar)
 * Source Folder ID: 1OscDa4RUjoa5sMAIb7CK7B1qXLi3pEGd
 *
 * WHAT THIS SCRIPT DOES:
 * 1. Automatically renames course folders to official BAU catalog titles:
 *    - Hort.501 -> Hort_501_Advanced_Fruit_Production
 *    - Hort.502 -> Hort_502_Methods_in_Advanced_Research
 *    - Hort.503 -> Hort_503_Advanced_Vegetable_Production
 *    - Hort.505 -> Hort_505_Advanced_Research_Methodology
 *    - Hort.507 -> Hort_507_Ornamental_and_Landscape_Hort
 *    - Hort.523 -> Hort_523_Advanced_Nursery_Management
 *    - Hort.525 -> Hort_525_Storage_Management_of_Horticultural_Crops
 *    - MS Syllabus -> 00_Syllabus_and_Curriculum
 *    - Question Vault -> 00_Question_Vault_and_Past_Exams
 * 2. Cleans teacher folder names (e.g., 'Dr. Aziz sir' -> 'Dr. Aziz').
 * 3. Sanitizes file names (removes awkward double-spaces, fix ' .pdf' typos).
 * 4. Recursively copies all materials cloud-to-cloud directly inside Google Drive.
 *
 * HOW TO RUN:
 * 1. Log into your TARGET Gmail in your browser.
 * 2. Go to https://script.new
 * 3. Replace all code with this script.
 * 4. Click Save, select 'cloneHorticultureDrive' and click 'Run'.
 * 5. Grant one-time permissions when prompted.
 */

// Official BAU Course & Directory Normalization Map
const FOLDER_RENAME_MAP = {
  "Hort.501": "Hort_501_Advanced_Fruit_Production",
  "Hort.502": "Hort_502_Methods_in_Advanced_Research",
  "Hort.503": "Hort_503_Advanced_Vegetable_Production",
  "Hort.505": "Hort_505_Advanced_Research_Methodology",
  "Hort.507": "Hort_507_Ornamental_and_Landscape_Hort",
  "Hort.523": "Hort_523_Advanced_Nursery_Management",
  "Hort.525": "Hort_525_Storage_Management_of_Horticultural_Crops",
  "MS Syllabus": "00_Syllabus_and_Curriculum",
  "Question Vault": "00_Question_Vault_and_Past_Exams",
  "Question bank": "01_Question_Bank_by_Topic",
  "Question images": "02_Exam_Paper_Images"
};

function cloneHorticultureDrive() {
  const SOURCE_FOLDER_ID = "1OscDa4RUjoa5sMAIb7CK7B1qXLi3pEGd";
  const TARGET_ROOT_NAME = "BAU_MS_Horticulture_Hub";

  Logger.log("🚀 Starting Smart Clone & Auto-Renaming from ID: " + SOURCE_FOLDER_ID);

  try {
    const sourceFolder = DriveApp.getFolderById(SOURCE_FOLDER_ID);
    
    // Create new neatly organized root directory
    const targetFolder = DriveApp.createFolder(TARGET_ROOT_NAME);
    Logger.log("📁 Created Target Root: '" + targetFolder.getName() + "'");

    // Recursively clone and rename
    smartCopyFolderRecursive(sourceFolder, targetFolder);

    Logger.log("🎉 SUCCESS! All files and folders have been neatly organized and renamed.");
    Logger.log("🔗 New Google Drive Link: " + targetFolder.getUrl());
  } catch (err) {
    Logger.log("❌ Error during clone: " + err.toString());
  }
}

function smartCopyFolderRecursive(source, target) {
  // 1. Copy & sanitize all files in the current folder
  const files = source.getFiles();
  while (files.hasNext()) {
    const file = files.next();
    const originalName = file.getName();
    const cleanName = getCleanFileName(originalName);

    try {
      file.makeCopy(cleanName, target);
      if (cleanName !== originalName) {
        Logger.log("  📄 Copied & Renamed File: '" + originalName + "' ➔ '" + cleanName + "'");
      } else {
        Logger.log("  📄 Copied File: '" + cleanName + "'");
      }
    } catch (e) {
      Logger.log("  ⚠️ Failed to copy file: " + originalName + " (" + e.message + ")");
    }
  }

  // 2. Traverse, normalize names, and copy all subfolders
  const subfolders = source.getFolders();
  while (subfolders.hasNext()) {
    const subfolder = subfolders.next();
    const originalFolderName = subfolder.getName();
    const cleanFolderName = getCleanFolderName(originalFolderName);

    Logger.log("📁 Processing: '" + originalFolderName + "' ➔ '" + cleanFolderName + "'");
    const newTargetSubfolder = target.createFolder(cleanFolderName);
    
    smartCopyFolderRecursive(subfolder, newTargetSubfolder);
  }
}

/**
 * Normalizes folder names based on BAU syllabus and eliminates informal suffixes
 */
function getCleanFolderName(rawName) {
  const trimmed = rawName.trim();
  
  // Exact match from syllabus mapping
  if (FOLDER_RENAME_MAP[trimmed]) {
    return FOLDER_RENAME_MAP[trimmed];
  }

  // Handle minor spacing variants e.g. "Hort 501", "Hort. 501"
  const normalizedKey = trimmed.replace(/\s+/g, '').replace('-', '.');
  for (const key in FOLDER_RENAME_MAP) {
    if (key.replace(/\s+/g, '') === normalizedKey) {
      return FOLDER_RENAME_MAP[key];
    }
  }

  // Teacher folder cleanup: remove informal 'sir', 'madam', 'ma'am'
  let clean = trimmed
    .replace(/\s+sir\b/gi, '')
    .replace(/\s+madam\b/gi, '')
    .replace(/\s+ma'am\b/gi, '')
    .trim();

  return clean;
}

/**
 * Cleans up file names (removes accidental spaces before extensions, etc.)
 */
function getCleanFileName(rawName) {
  let clean = rawName.trim();
  // Fix "filename .pdf" -> "filename.pdf"
  clean = clean.replace(/\s+\.([a-zA-Z0-9]+)$/, '.$1');
  // Collapse excessive spaces
  clean = clean.replace(/\s{2,}/g, ' ');
  return clean;
}
