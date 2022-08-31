import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import datetime
from datetime import date

### SET SOME VARIABLES FOR LATER ###
today = (date.today())
formatToday = today.strftime("%b-%d-%Y")
week_agoStr = str(today - datetime.timedelta(days=5))

### CONSTRUCT AND SEND THE EMAIL ###
sender_address = os.getenv('NOTIF_EMAIL_ADDRESS')
sender_pass =  os.getenv('NOTIF_PW')
receiver_address = 'pmedlin@kinpakinc.com'
message = MIMEMultipart('alternative')
message['From'] = sender_address
message['To'] = receiver_address
message['Subject'] = 'Forklift logs '+week_agoStr+" to "+str(today)
mail_content = "Below is a table showing all forklift issues reported for the week of "+ week_agoStr + " to " + str(today)
listOfObjects = ['aaa','bbb','ccc']
html_code = """
                <style>
                    table, td {
                        border: 1px solid black;
                        border-collapse: collapse;
                    }
                    th, td {
                        padding: 5px;
                        text-align: left;    
                    }
                    th {
                        border: 2px solid black;
                        background: #8b8378;
                        color: #FFFFFF;
                    }    
                </style>
                <body>
                    <table border='1'>
                    <tr>
                        <th>Forklift Number</th>
                        <th>Operator</th>
                        <th>Checklist Status</th>
                    </tr>
                    <tr>
                        <td>asdf</td>
                        <td>fdfda</td>
                        <td>sdf</td>
                    </tr>
                    </table>
                </body>"""
print(html_code)
part1 = MIMEText(mail_content, 'plain')
part2 = MIMEText(html_code, 'html')
message.attach(part1)
message.attach(part2)

### CREATE SMTP SESSION AND SEND THE EMAIL ###
session = smtplib.SMTP('smtp.gmail.com', 587) #use gmail with port
session.starttls() #enable security
session.login(sender_address, sender_pass) #login with mail_id and password
session.sendmail(sender_address, receiver_address, message.as_string())
session.quit()