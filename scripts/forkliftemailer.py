import smtplib
import os
import psycopg2
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import datetime
from datetime import date
import pandas as pd

### SET SOME VARIABLES FOR LATER ###
today = (date.today())
formatToday = today.strftime("%b-%d-%Y")
fileName = 'Forklift_Logs_'+formatToday + '.csv'
forkliftLogsPath = os.path.expanduser('~\Documents\\'+fileName)


### GRAB ALL FORKLIFT ENTRIES FROM THE PAST WEEK AND PUT THEM INTO A CSV IN DOCUMENTS ###
cnxnPG = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
cursPG = cnxnPG.cursor()
week_agoStr = str(today - datetime.timedelta(days=7))
fid = open(forkliftLogsPath, 'w')
sqlQuery = "copy (select * from core_checklistlog where core_checklistlog.submitted_date > '%s') TO STDOUT WITH CSV HEADER" % week_agoStr
cursPG.copy_expert(sqlQuery, fid)
fid.close()


### CONSTRUCT AND SEND THE EMAIL ###
mail_content = "Attached is a csv file including all forklift entries for the week of "+ week_agoStr + "to " + str(today)
sender_address = os.getenv('NOTIF_EMAIL_ADDRESS')
sender_pass =  os.getenv('NOTIF_PW')
receiver_address = 'jdavis@kinpakinc.com'
message = MIMEMultipart()
message['From'] = sender_address
message['To'] = receiver_address
message['Subject'] = 'Forklift logs '+week_agoStr+"to "+str(today)
message.attach(MIMEText(mail_content, 'plain'))
with open(forkliftLogsPath,'rb') as file:
    message.attach(MIMEApplication(file.read(), Name=fileName))


### CREATE SMTP SESSION AND SEND THE EMAIL ###
session = smtplib.SMTP('smtp.gmail.com', 587) #use gmail with port
session.starttls() #enable security
session.login(sender_address, sender_pass) #login with mail_id and password
text = message.as_string()
session.sendmail(sender_address, receiver_address, text)
session.quit()