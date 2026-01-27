2026-01-21 .. 3:30PM

1. need a big Approved checkbox added to the form and the interface
2. Navbar item needs to be moved into the Blending dropdown for any navbars it's a part of
3. Need to add the lab personnel field to the default form (autopopulate and readonly) just so the lab person can see it. 
4. Need to entirely change the names in EVERY single place. this is supposed to capture all discharged materials, not just flush totes. Change function names and all urls to "discharge-testing" and "discharge-testing-records". this includes the model name. Just change the model name and I'll delete the table. 
5. Need to add another field to the model and the form called final_disposition. It should be a required field and the purpose is to record what is done with the container after testing is done.
6. Need to just display the action_required field by default, remove the js that hides it by default. 


2026-01-26 .. 11:30 AM
ISSUES
 - Any user can access (and edit) the Discharge testing records. Should be restricted to staff only.
 - /core/discharge-testing/ does not allow lab non-staff to access. Should be open to anyone with lab group status. 
 - there is no "line personnel" user group. anyone in the entire db could be the sampling personnel. just need to verify that they are a legit user. 
 - the Clear button on the form causes all fields to be unclickable
 - need to make the initial pH field required
 - on the count records we need admin users to be able to delete rows
 - when you click the edit button, the delete button gets replaced with an empty text input field??


ISSUES THAT CAN BE DEFERRED
 - rounding doesn't happen automatically on pH fields, it just tells you you can't enter three decimal places
 - multiline text doesn't look amazing bc it all gets saved as one line, but it's still readable in the table on the records display page
 - 