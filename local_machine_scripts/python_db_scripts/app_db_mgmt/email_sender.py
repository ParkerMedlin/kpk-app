from dotenv import load_dotenv
import os
import datetime as dt
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

load_dotenv()

def send_email_error(error_list, recipient_addresses):
    timestamp = datetime.now()
    sender_address = os.getenv('NOTIF_EMAIL_ADDRESS')
    sender_pass =  os.getenv('NOTIF_PW')
    recipient_list = recipient_addresses.split(',')
    message_body = f'Server updates have stopped due to excessive errors. \ncan devs DO SOMETHING?? \n{timestamp}\n'
    for error in error_list:
        message_body = message_body + '\n' + str(error)
    for recipient in recipient_list:
        message = MIMEMultipart('alternative')
        message['From'] = sender_address
        message['To'] = recipient
        message['Subject'] = 'Server refresh issues'
        message.attach(MIMEText(message_body))

        ### CREATE SMTP SESSION AND SEND THE EMAIL ###
        session = smtplib.SMTP('smtp.gmail.com', 587) #use gmail with port
        session.starttls() #enable security
        session.login(sender_address, sender_pass) #login with mail_id and password
        session.sendmail(sender_address, recipient, message.as_string())
        session.quit()
        print(f'message sent to {recipient}')