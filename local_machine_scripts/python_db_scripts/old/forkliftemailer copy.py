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

forkliftNumList = [
                    '3', '4', '6', '7', '8', '9', '10', '11', '12', '13', '15', '16', '17', '18', '19', '20', '21', '22', 
                    '23', '24', '25', '26', '27', '28', '29', '30', '32', '34', '35', '36', '37', '38', '39', '40', '41', 
                    '42', '43', '44', '45', '46', '47', '48', '49', '50', 'Rental1', 'Rental2', 'Rental3'
                    ]
refinedForkliftOpDict = {
                            '3': '', '4': 'Morris Chandler', '6': 'Joe Calhoun', '7': '', '8': 'Tom Stone', '9': 'Anthony Todd', 
                            '10': 'Mike Abrams', '11': 'Tom Stone', '12': 'Hakeem Woods', '13': 'Renardo Williams', '15': 'Torrie Jones(Blending)', 
                            '16': 'Otis Glover', '17': 'Eric Phillips', '18': 'Vicki Brown', '19': 'Joshua Price ', '20': 'Crystal Holloway', 
                            '21': 'Leo Jackson', '22': 'Leo Jackson', '23': 'T Vinson', '24': 'Corey Brown', '25': 'Earnest Taylor', '26': 'Rodney Riddle', 
                            '27': 'Mack Caldwell', '28': 'Temp', '29': 'Blowmold', '30': 'Blowmold', '32': 'Earnest Woods', '34': '', '35': 'bobby Barganier', 
                            '36': 'Torrie Jones', '37': 'Maxie Clark', '38': 'Joey Blankenship', '39': 'Bobby Barganier', '40': 'Maxie Clark', 
                            '41': 'Marquitt Phillips', '42': 'Kirby Armont', '43': 'Zach McMannes', '44': 'Grady Wingfield', '45': 'Mark Davis', 
                            '46': 'Saeed Abdus Salaam', '47': 'Rasari Thomas', '48': 'Jamie Boutwell Jr.', '49': 'Michael Abbruscato', '50': 'Mike Lockwood', 
                            'Rental1': 'Charlie Jones', 'Rental2': 'returned  4/9/2021', 'Rental3': 'returned  4/9/2021'
                            }
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
                        text-align: center;
                    }    
                </style>
                <body>
                    <table border='1'>
                    <tr>
                        <th>Forklift Number</th>
                        <th>Operator</th>
                        <th>Checklist Status</th>
                    </tr>
                    """
for key, value in refinedForkliftOpDict.items():

    html_code +="""
                        <tr>
                            <td>{}</td>
                            <td>{}</td>
                            <td>{}</td>
                        </tr>
                        """.format(key, value, 'NOT SUBMITTED')
html_code +="""     </table>
                </body>"""

sender_address = os.getenv('NOTIF_EMAIL_ADDRESS')
sender_pass =  os.getenv('NOTIF_PW')
receiver_address = 'pmedlin@kinpakinc.com'
message = MIMEMultipart('alternative')
message['From'] = sender_address
message['To'] = receiver_address
message['Subject'] = 'All personnel missing forklift logs for '+str(today)
message.attach(MIMEText(html_code, 'html'))

### CREATE SMTP SESSION AND SEND THE EMAIL ###
session = smtplib.SMTP('smtp.gmail.com', 587) #use gmail with port
session.starttls() #enable security
session.login(sender_address, sender_pass) #login with mail_id and password
session.sendmail(sender_address, receiver_address, message.as_string())
session.quit()