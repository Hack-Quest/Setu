function onNgoFormSubmit(e) {
  var targetWebsite = "https://tweak-dole-registry.ngrok-free.dev/ngo/register";

  var answers = e.namedValues;

  var dataBox = {
    name: answers["NGO Name"] ? answers["NGO Name"][0] : "",
    reg_number: answers["Registration Number"] ? answers["Registration Number"][0] : "",
    lat: parseFloat(answers["Latitude"] ? answers["Latitude"][0] : 0) || 0.0,
    lng: parseFloat(answers["Longitude"] ? answers["Longitude"][0] : 0) || 0.0,
    radius: parseFloat(answers["Operational Radius (km)"] ? answers["Operational Radius (km)"][0] : 0) || 10.0
  };

  var shippingDetails = {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify(dataBox),
  };

  try {
    UrlFetchApp.fetch(targetWebsite, shippingDetails);
  } catch (error) {
    Logger.log("Error: " + error.toString());
  }
}
