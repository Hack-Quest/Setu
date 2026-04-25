function onNgoFormSubmit(e) {
  var targetWebsite = "https://tweak-dole-registry.ngrok-free.dev/ngo/register";

  var answers = e.namedValues;

  var dataBox = {
    ngo_name: answers["NGO Name"] ? answers["NGO Name"][0] : "",
    owner_name: answers["Owner Name"] ? answers["Owner Name"][0] : (answers["Name"] ? answers["Name"][0] : "Admin"),
    reg_number: answers["Registration Number"] ? answers["Registration Number"][0] : "",
    lat: parseFloat(answers["Latitude"] ? answers["Latitude"][0] : 0) || 0.0,
    lng: parseFloat(answers["Longitude"] ? answers["Longitude"][0] : 0) || 0.0,
    radius: parseFloat(answers["Operational Radius (km)"] ? answers["Operational Radius (km)"][0] : 0) || 10.0,
    location: answers["Location"] ? answers["Location"][0] : "",
    email: answers["Email Address"] ? answers["Email Address"][0] : "",
    description: answers["Description"] ? answers["Description"][0] : ""
  };

  var shippingDetails = {
    method: "post",
    contentType: "application/json",
    headers: {
      "Authorization": "Bearer hackathon-secret"
    },
    payload: JSON.stringify(dataBox),
  };

  try {
    UrlFetchApp.fetch(targetWebsite, shippingDetails);
  } catch (error) {
    Logger.log("Error: " + error.toString());
  }
}
