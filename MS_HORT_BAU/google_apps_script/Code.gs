/**
 * ==============================================================================
 * BAU MS Horticulture Hub - Google Drive Auto-Uploader & Folder Webhook
 * ==============================================================================
 * 
 * SETUP INSTRUCTIONS (Takes ~1 minute):
 * 1. Open your Google Sheet (https://docs.google.com/spreadsheets/d/1VSTzdOkCTSTRnIwS6kTJ1rLDnNaJAyAYAMBCl3Zf8s8)
 *    OR go to https://script.google.com
 * 2. Click "Extensions" > "Apps Script".
 * 3. Delete any default code and paste this entire file contents into "Code.gs".
 * 4. Click "Deploy" (top right) > "New deployment".
 * 5. Click the gear icon (Select type) > Choose "Web app".
 * 6. Set:
 *    - Description: "BAU MS Hort Portal Uploader"
 *    - Execute as: "Me" (your Google account)
 *    - Who has access: "Anyone"
 * 7. Click "Deploy" and authorize permissions when prompted.
 * 8. Copy the generated "Web App URL" (ends in /exec).
 * 9. Paste this URL into your portal's Upload Modal (or Settings Modal).
 * ==============================================================================
 */

// Security PIN to prevent unauthorized uploads (Set to Batch PIN: 262020)
const SECRET_PASSCODE = "262020";

// Default Master Drive Folder ID (BAU_MS_Horticulture_Hub)
const DEFAULT_ROOT_FOLDER_ID = "1VonkTL2XPoKiQ5Z4_qZnUFbNMuunMhbW";

function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return responseJson({ status: "error", message: "No payload received." });
    }

    const data = JSON.parse(e.postData.contents);

    // 1. Security passcode check (Batch PIN)
    if (SECRET_PASSCODE && (!data.passcode || data.passcode.toString().trim() !== SECRET_PASSCODE)) {
      return responseJson({ 
        status: "error", 
        message: "Invalid batch PIN. Please enter the correct Batch PIN (262020) to upload." 
      });
    }

    // 2. Resolve destination parent folder
    let targetFolder;
    const folderId = data.folderId || DEFAULT_ROOT_FOLDER_ID;
    try {
      targetFolder = DriveApp.getFolderById(folderId);
    } catch (fErr) {
      targetFolder = DriveApp.getFolderById(DEFAULT_ROOT_FOLDER_ID);
    }

    // 3. Resolve or Create Subfolder if requested
    if (data.newSubfolder && data.newSubfolder.trim() !== "") {
      const subName = data.newSubfolder.trim();
      const existing = targetFolder.getFoldersByName(subName);
      if (existing.hasNext()) {
        targetFolder = existing.next();
      } else {
        targetFolder = targetFolder.createFolder(subName);
      }
    } else if (data.subfolderName && data.subfolderName.trim() !== "") {
      const subName = data.subfolderName.trim();
      const existing = targetFolder.getFoldersByName(subName);
      if (existing.hasNext()) {
        targetFolder = existing.next();
      }
    }

    // 4. File Decoding & Creation
    const contentType = data.mimeType || "application/octet-stream";
    const bytes = Utilities.base64Decode(data.base64);
    const finalName = data.finalFileName || ("Hort_Material_" + Utilities.formatDate(new Date(), "GMT+6", "yyyyMMdd_HHmmss"));
    const blob = Utilities.newBlob(bytes, contentType, finalName);

    const file = targetFolder.createFile(blob);
    file.setDescription("Uploaded via BAU MS Horticulture Academic Portal.");

    // Return detailed result
    return responseJson({
      status: "success",
      fileId: file.getId(),
      fileName: file.getName(),
      fileUrl: file.getUrl(),
      folderName: targetFolder.getName(),
      folderUrl: targetFolder.getUrl()
    });

  } catch (error) {
    return responseJson({
      status: "error",
      message: error.toString()
    });
  }
}

function doGet(e) {
  try {
    const action = e && e.parameter && e.parameter.action;
    
    // Live subfolder retrieval for portal dropdowns
    if (action === "getSubfolders") {
      const folderId = (e.parameter && e.parameter.folderId) || DEFAULT_ROOT_FOLDER_ID;
      let targetFolder;
      try {
        targetFolder = DriveApp.getFolderById(folderId);
      } catch (fErr) {
        targetFolder = DriveApp.getFolderById(DEFAULT_ROOT_FOLDER_ID);
      }
      
      const subfolders = [];
      const iterator = targetFolder.getFolders();
      while (iterator.hasNext()) {
        const sub = iterator.next();
        subfolders.push({
          id: sub.getId(),
          name: sub.getName(),
          url: sub.getUrl()
        });
      }
      
      return responseJson({
        status: "success",
        courseFolder: targetFolder.getName(),
        subfolders: subfolders
      });
    }

  } catch (err) {
    return responseJson({
      status: "error",
      message: err.toString()
    });
  }

  return responseJson({
    status: "active",
    message: "BAU MS Horticulture Drive Webhook is live and ready to accept file uploads."
  });
}

function responseJson(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
