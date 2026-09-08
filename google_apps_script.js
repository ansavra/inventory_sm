/**
 * ============================================================
 * Google Apps Script សម្រាប់ភ្ជាប់ជាមួយ SM Inventory System
 * ============================================================
 * 
 * របៀបដំឡើង (Setup Instructions)៖
 * 1. បង្កើត Google Sheet ថ្មីមួយនៅលើ Google Drive (ឧ. ឈ្មោះ "SM Inventory System")
 * 2. បង្កើត Sheet ២ ខាងក្រោម៖
 *    - Sheet ទី ១ ដាក់ឈ្មោះថា: Transactions
 *    - Sheet ទី ២ ដាក់ឈ្មោះថា: Products
 * 3. ចូលទៅកាន់ Menu: Extensions (ផ្នែកបន្ថែម) > Apps Script
 * 4. លុបកូដចាស់ៗចេញ រួច Copy កូដទាំងអស់នេះទៅបិទភ្ជាប់ (Paste)
 * 5. ចុច Save (💾)
 * 6. ចុច Deploy (ដាក់ឱ្យប្រើប្រាស់) > New deployment (ការដាក់ឱ្យប្រើប្រាស់ថ្មី)
 *    - Select type: Web app (កម្មវិធីគេហទំព័រ)
 *    - Description: SM Inventory Sync
 *    - Execute as: Me (គណនីរបស់អ្នក)
 *    - Who has access: Anyone (នរណាម្នាក់) ***សំខាន់ណាស់***
 * 7. ចុច Deploy រួច Copy "Web app URL" (តំណភ្ជាប់ដែលបញ្ចប់ដោយ /exec)
 * 8. យក URL នោះមកដាក់ក្នុងប្រព័ន្ធ SM Inventory ក្នុង .env:
 *    GOOGLE_SHEET_WEBHOOK_URL="https://script.google.com/macros/s/.../exec"
 */

function doPost(e) {
  try {
    var contents = JSON.parse(e.postData.contents);
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    
    // បង្កើតកាលបរិច្ឆេទ & ម៉ោងនៅកម្ពុជា (GMT+7)
    var now = Utilities.formatDate(new Date(), "GMT+7", "yyyy-MM-dd HH:mm:ss");

    if (contents.action === "transaction") {
      var sheet = ss.getSheetByName("Transactions");
      if (!sheet) {
        sheet = ss.insertSheet("Transactions");
        sheet.appendRow([
          "កាលបរិច្ឆេទ & ម៉ោង", "ប្រភេទ", "កូដទំនិញ", "ឈ្មោះទំនិញ",
          "ចំនួន", "ឯកតា", "តម្លៃរាយ ($)", "តម្លៃសរុប ($)",
          "កំណត់ចំណាំ / វិក្កយបត្រ", "អ្នកកត់ត្រា", "ស្តុកនៅសល់"
        ]);
        sheet.getRange(1, 1, 1, 11).setFontWeight("bold").setBackground("#312e81").setFontColor("#ffffff");
      }

      sheet.appendRow([
        now,
        contents.type,
        contents.product_code,
        contents.product_name,
        contents.quantity,
        contents.unit,
        contents.unit_price,
        contents.total_price,
        contents.reference,
        contents.performed_by,
        contents.stock_remaining
      ]);

      return ContentService.createTextOutput(JSON.stringify({ "status": "success", "message": "Transaction recorded" }))
        .setMimeType(ContentService.MimeType.JSON);
    } 
    
    else if (contents.action === "product") {
      var prodSheet = ss.getSheetByName("Products");
      if (!prodSheet) {
        prodSheet = ss.insertSheet("Products");
        prodSheet.appendRow([
          "កូដទំនិញ", "ឈ្មោះទំនិញ", "ប្រភេទ", "ឯកតា",
          "តម្លៃដើម ($)", "តម្លៃលក់ ($)", "ចំនួនស្តុក", "ទីតាំង", "កាលបរិច្ឆេទបង្កើត"
        ]);
        prodSheet.getRange(1, 1, 1, 9).setFontWeight("bold").setBackground("#059669").setFontColor("#ffffff");
      }

      prodSheet.appendRow([
        contents.code,
        contents.name,
        contents.category,
        contents.unit,
        contents.cost_price,
        contents.sell_price,
        contents.quantity,
        contents.location,
        now
      ]);

      return ContentService.createTextOutput(JSON.stringify({ "status": "success", "message": "Product recorded" }))
        .setMimeType(ContentService.MimeType.JSON);
    }

    return ContentService.createTextOutput(JSON.stringify({ "status": "pong" }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ "status": "error", "message": err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  return ContentService.createTextOutput("SM Inventory Google Sheet Sync is Active! (GMT+7)");
}
