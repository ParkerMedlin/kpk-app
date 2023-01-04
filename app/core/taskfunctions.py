import os
from datetime import datetime as dt
from datetime import date
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from core.models import ChecklistLog


def test_function():
    today = (date.today())
    sender_address = 'kpknotifications@gmail.com'
    sender_pass = 'nrnzvspsdongergf'
    print(sender_address)
    receiver_address = 'jdavis@kinpakinc.com'
    message = MIMEMultipart('alternative')
    message['From'] = sender_address
    message['To'] = receiver_address
    message['Subject'] = 'All forklift log issues for '+str(today)
    message.attach(MIMEText('<h1>Hey</h1>', 'html'))


    ### CREATE SMTP SESSION AND SEND THE EMAIL ###
    session = smtplib.SMTP('smtp.gmail.com', 587) #use gmail with port
    session.starttls() #enable security
    session.login(sender_address, sender_pass) #login with mail_id and password
    session.sendmail(sender_address, receiver_address, message.as_string())
    session.quit()