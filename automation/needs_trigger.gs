function onFormSubmit(e) {
  // Jab Khare Google Cloud ka link degi, tab yahan replace karenge
  var targetWebsite = "YOUR_GOOGLE_CLOUD_RUN_URL_HERE/webhook";

  var answers = e.namedValues;

  // Data ko organized dabbe (JSON) mein pack karna
  var dataBox = {
    reporter_name: answers["Reporter Name"] ? answers["Reporter Name"][0] : "",
    reporter_phone: answers["Reporter Phone Number (10 digits)"]
      ? answers["Reporter Phone Number (10 digits)"][0]
      : "",
    location: answers[
      "Exact Location (Paste a Google Maps link, Plus Code, or exact landmark)"
    ]
      ? answers[
          "Exact Location (Paste a Google Maps link, Plus Code, or exact landmark)"
        ][0]
      : "",
    disaster_type: answers["Type of Disaster"]
      ? answers["Type of Disaster"][0]
      : "",
    help_needed: answers[
      "What immediate help do you need? (Select all that apply)"
    ]
      ? answers["What immediate help do you need? (Select all that apply)"][0]
      : "",
    description: answers["Describe the situation in your own words"]
      ? answers["Describe the situation in your own words"][0]
      : "",
  };

  var shippingDetails = {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify(dataBox),
  };

  try {
    var response = UrlFetchApp.fetch(targetWebsite, shippingDetails);
    Logger.log("Response: " + response.getContentText());
  } catch (error) {
    Logger.log("Error: " + error.toString());
  }
}
