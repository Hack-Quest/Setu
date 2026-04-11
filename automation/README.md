# Automation Module (Google Workspace Integration)

This folder contains the Google Apps Script (`.gs`) files used to trigger webhooks from our Google Forms.

## 🚀 How to deploy these scripts:

**Do NOT run these scripts locally in VS Code.** They must be pasted into Google Sheets.

1. Open the Google Sheet linked to your Google Form.
2. Click on **Extensions > Apps Script** in the top menu.
3. Paste the code from `needs_trigger.gs`.
4. Replace `YOUR_GOOGLE_CLOUD_RUN_URL_HERE` with the URL provided by Khare (Backend Team).
5. Click **Save**.
6. Set up a **Trigger**:
   - Event source: `From spreadsheet`
   - Event type: `On form submit`

**Author:** Anshika (Frontend & Automation Lead)