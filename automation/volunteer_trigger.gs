function onVolunteerFormSubmit(e) {
  // Volunteers ke liye alag endpoint ho sakta hai
  var targetWebsite = "https://tweak-dole-registry.ngrok-free.dev/volunteer_webhook";

  var answers = e.namedValues;

  var dataBox = {
    volunteer_name: answers["Full Name"] ? answers["Full Name"][0] : "",
    phone: answers["Phone Number"] ? answers["Phone Number"][0] : "",
    skills: answers["Your Skills (e.g., Medical, Driving, Rescue)"]
      ? answers["Your Skills (e.g., Medical, Driving, Rescue)"][0]
      : "",
    location: answers["Your City/Area"] ? answers["Your City/Area"][0] : "",
    availability: answers["Are you available immediately?"]
      ? answers["Are you available immediately?"][0]
      : "",
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