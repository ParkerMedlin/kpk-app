Okay so 
1. Gunicorn is handling all the translation from http to python to http, 
2. NGINX is handling all the http requests to and from gunicorn,
3. NGINX is also handling all http requests for static content, 
4. Django app (named 'app') is handling all dynamic stuff behind the scenes:
    - Reading/writing to database. (We are using Postgres)
    - Handling http requests for pages.
    - Login/user profile system.

## General Notes:
 - Nav Bar
     - The items and links are all laid out in the base.html template in kpk-app/app/templates
     - Login/Logout button will be present depending on whether the user is logged in (`user.is_authenticated`)
     - Admin button is present depending on whether the user is an admin (`user.is_staff`)


## The main functions of this app:

### 1: Forklift safety checklist
 - Forklift drivers will be able to fill out a checklist certifying that they have completed daily inspection of their vehicle.
 - Safety manager will be sent a report containing all daily inspection forms containing comments/safety concerns.
 - Would be nice if we could flag users who aren't completing the checklist.   
 - Would be nice if users could submit a picture of problem areas on forklift as well.

### 2: Blend sheets 
 - Blend crew will be presented with steps for each blend and required to submit pictures verifying quantity & correctness for each step. 

### 3: Lot Numbers
 - Database will contain our batch history. 


General naming conventions follow PEP 8 (https://peps.python.org/pep-0008/#naming-conventions):
 - Functions: all lowercase words, separated by underscore
	- Include a verb at the beginning to indicate what the function does
 - Variables: all lowercase words, separated by underscore
 - Classes (including Models): CamelCase

More specific and not necessarily python-related: 
 - the 'name' parameter of each url path is lowercase words separated by dashes
 - all templates are lowercase, words not separated by punctuation