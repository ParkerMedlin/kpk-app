import os
from datetime import datetime as dt
from datetime import date
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from core.models import ChecklistLog

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

def email_checklist_issues():
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.image import MIMEImage
    from core.models import ChecklistLog
    from datetime import date

    today_date = date.today()
    print('this is the email_checklist_issues function')
    if today_date.weekday()<5:
        print('the function is getting past our logical condition')
        checklist_logs_today = ChecklistLog.objects.filter(submitted_date__gte=date.today()).filter(
            engine_oil__contains='Bad') | ChecklistLog.objects.filter(submitted_date__gte=date.today()).filter(
            propane_tank__contains='Bad') | ChecklistLog.objects.filter(submitted_date__gte=date.today()).filter(
            radiator_leaks__contains='Bad') | ChecklistLog.objects.filter(submitted_date__gte=date.today()).filter(
            tires__contains='Bad') | ChecklistLog.objects.filter(submitted_date__gte=date.today()).filter(
            mast_and_forks__contains='Bad') | ChecklistLog.objects.filter(submitted_date__gte=date.today()).filter(
            leaks__contains='Bad') | ChecklistLog.objects.filter(submitted_date__gte=date.today()).filter(
            horn__contains='Bad') | ChecklistLog.objects.filter(submitted_date__gte=date.today()).filter(
            driver_compartment__contains='Bad') | ChecklistLog.objects.filter(submitted_date__gte=date.today()).filter(
            seatbelt__contains='Bad') | ChecklistLog.objects.filter(submitted_date__gte=date.today()).filter(
            battery__contains='Bad') | ChecklistLog.objects.filter(submitted_date__gte=date.today()).filter(
            safety_equipment__contains='Bad') | ChecklistLog.objects.filter(submitted_date__gte=date.today()).filter(
            steering__contains='Bad') | ChecklistLog.objects.filter(submitted_date__gte=date.today()).filter(
            brakes__contains='Bad').order_by('unit_number')
        
        print('the function is successfully evaluating our queryset')
        all_checklist_log_issues = {}
        if checklist_logs_today:
            for object in checklist_logs_today:
                print('if object.engine_oil == d')
                if object.engine_oil == 'Bad':
                    all_checklist_log_issues[object.unit_number.unit_number + '_Engine_Oil_Issue'] = (object.engine_oil_comments, object.operator_name)
                if object.propane_tank == 'Bad':
                    all_checklist_log_issues[object.unit_number.unit_number + '_Propane_Tank_Issue'] = (object.propane_tank_comments, object.operator_name)
                if object.radiator_leaks == 'Bad':
                    all_checklist_log_issues[object.unit_number.unit_number + '_Radiator_Leaks_Issue'] = (object.radiator_leaks_comments, object.operator_name)
                if object.tires == 'Bad':
                    all_checklist_log_issues[object.unit_number.unit_number + '_Tires_Issue'] = (object.tires_comments, object.operator_name)
                if object.mast_and_forks == 'Bad':
                    all_checklist_log_issues[object.unit_number.unit_number + '_Mast_and_Forks_Issue'] = (object.mast_and_forks_comments, object.operator_name)
                if object.leaks == 'Bad':
                    all_checklist_log_issues[object.unit_number.unit_number + '_Leaks_Issue'] = (object.leaks_comments, object.operator_name)
                if object.horn == 'Bad':
                    all_checklist_log_issues[object.unit_number.unit_number + '_Horn_Issue'] = (object.horn_comments, object.operator_name)
                if object.driver_compartment == 'Bad':
                    all_checklist_log_issues[object.unit_number.unit_number + '_Driver_Compartment_Issue'] = (object.driver_compartment_comments, object.operator_name)
                if object.seatbelt == 'Bad':
                    all_checklist_log_issues[object.unit_number.unit_number + '_Seatbelt_Issue'] = (object.seatbelt_comments, object.operator_name)
                if object.battery == 'Bad':
                    all_checklist_log_issues[object.unit_number.unit_number + '_Battery_Issue'] = (object.battery_comments, object.operator_name)
                if object.safety_equipment == 'Bad':
                    all_checklist_log_issues[object.unit_number.unit_number + '_Safety_Equipment_Issue'] = (object.safety_equipment_comments, object.operator_name)
                if object.steering == 'Bad':
                    all_checklist_log_issues[object.unit_number.unit_number + '_Steering_Issue'] = (object.steering_comments, object.operator_name)
                if object.brakes == 'Bad':
                    all_checklist_log_issues[object.unit_number.unit_number + '_Brakes_Issue'] = (object.brakes_comments, object.operator_name)
                print('the function is successfully evaluating our queryset')
                if len(all_checklist_log_issues)!=0:
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
                                        <th>Issue</th>
                                        <th>Issue Details</th>
                                    </tr>
                                    """

                    for key, value in all_checklist_log_issues.items():
                        unit_num = (key[:2]).replace('_','')
                        issue_type = (key.split('_',1)[1]).replace('_',' ').replace('Issue','')
                        html_code += '''<tr>
                                            <td>{}</td>
                                            <td>{}</td>
                                            <td>{}</td>
                                            <td>{}</td>
                                            </tr>'''.format(unit_num, value[1], issue_type, value[0])
                    html_code +="""     </table>
                                    </body>"""
                
                else:
                    html_code = '''<h1>No Issues Reported Today</h1>
                                    <div></div>'''
        else: 
            html_code = '''<h1>No Logs Today</h1>
                                <div></div>'''
        print(html_code)

        sender_address = os.getenv('NOTIF_EMAIL_ADDRESS')
        sender_pass =  os.getenv('NOTIF_PW')
        print(sender_address)
        print(sender_pass)
        receiver_address = 'pmedlin@kinpakinc.com'
        message = MIMEMultipart('alternative')
        message['From'] = sender_address
        message['To'] = receiver_address
        message['Subject'] = 'All forklift log issues for '+str(today_date)
        message.attach(MIMEText(html_code, 'html'))
        print('the function has successfully created an email message object')

        ### CREATE SMTP SESSION AND SEND THE EMAIL ###
        session = smtplib.SMTP('smtp.gmail.com', 587) #use gmail with port
        session.starttls() #enable security
        session.login(sender_address, sender_pass) #login with mail_id and password
        session.sendmail(sender_address, receiver_address, message.as_string())
        session.quit()
        print('message sent')









def test_func():
    today_date = date.today()
    print('this is the test function.')
    print('todays weekday: '+str(today_date.weekday()))
    if today_date.weekday()<5:
        print('today is before saturday')
    else:
        print('today is not before saturday')