import os
from datetime import datetime as dt
from datetime import date
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from core.models import ChecklistLog
from django_q.tasks import async_task, result
from core import taskfunctions


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

def update_checklist_tracker():
    from core.models import ChecklistSubmissionRecord, ChecklistLog, Forklift
    forklift_numbers = list(Forklift.objects.values_list('unit_number', flat=True).order_by('id'))
    right_now = dt.now()
    yesterday = date.today()-datetime.timedelta(days=1)
    one_AM_today = right_now.replace(hour=1, minute=0).strftime('%Y-%m-%d')
    checklists_today = ChecklistLog.objects.filter(submitted_date__gt=one_AM_today)
    if not ChecklistSubmissionRecord.objects.filter(check_date__gt=yesterday).exists():
        checklist_statuses = {}
        for number in forklift_numbers:
            if checklists_today.filter(unit_number__icontains=number).exists():
                checklist_statuses[number] = "Report Submitted"
            else:
                checklist_statuses[number] = "MISSING"

        ChecklistSubmissionRecord.objects.create(
            forklift_1 = checklist_statuses['1'],
            forklift_2 = checklist_statuses['2'],
            forklift_3 = checklist_statuses['3'],
            forklift_4 = checklist_statuses['4'],
            forklift_5 = checklist_statuses['5'],
            forklift_6 = checklist_statuses['6'],
            forklift_7 = checklist_statuses['7'],
            forklift_8 = checklist_statuses['8'],
            forklift_9 = checklist_statuses['9'],
            forklift_10 = checklist_statuses['10'],
            forklift_11 = checklist_statuses['11'],
            forklift_12 = checklist_statuses['12'],
            forklift_13 = checklist_statuses['13'],
            forklift_15 = checklist_statuses['15'],
            forklift_16 = checklist_statuses['16'],
            forklift_17 = checklist_statuses['17'],
            forklift_18 = checklist_statuses['18'],
            forklift_19 = checklist_statuses['19'],
            forklift_20 = checklist_statuses['20'],
            forklift_21 = checklist_statuses['21'],
            forklift_22 = checklist_statuses['22'],
            forklift_23 = checklist_statuses['23'],
            forklift_24 = checklist_statuses['24'],
            forklift_25 = checklist_statuses['25'],
            forklift_26 = checklist_statuses['26'],
            forklift_27 = checklist_statuses['27'],
            forklift_28 = checklist_statuses['28'],
            forklift_29 = checklist_statuses['29'],
            forklift_30 = checklist_statuses['30'],
            forklift_32 = checklist_statuses['32'],
            forklift_34 = checklist_statuses['34'],
            forklift_35 = checklist_statuses['35'],
            forklift_36 = checklist_statuses['36'],
            forklift_37 = checklist_statuses['37'],
            forklift_38 = checklist_statuses['38'],
            forklift_39 = checklist_statuses['39'],
            forklift_40 = checklist_statuses['40'],
            forklift_41 = checklist_statuses['41'],
            forklift_42 = checklist_statuses['42'],
            forklift_43 = checklist_statuses['43'],
            forklift_44 = checklist_statuses['44'],
            forklift_45 = checklist_statuses['45'],
            forklift_46 = checklist_statuses['46'],
            forklift_47 = checklist_statuses['47'],
            forklift_48 = checklist_statuses['48'],
            forklift_49 = checklist_statuses['49'],
            forklift_50 = checklist_statuses['50'],
            forklift_Rental1 = checklist_statuses['Rental1'],
            forklift_Rental2 = checklist_statuses['Rental2'],
            forklift_Rental3 = checklist_statuses['Rental3']
            )


def email_checklist_submission_tracking():
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from core.models import ChecklistSubmissionRecord, Forklift

    
    submission_records_today = ChecklistSubmissionRecord.objects.filter(check_date__gte=date.today()).values()
    checklist_statuses = submission_records_today[0]
    forklifts_missing_submission = {key : val for key, val in checklist_statuses.items() if val != 'Report Submitted' and key != 'id' and key != 'check_date'}
    forklift_numbers = list(forklifts_missing_submission.keys())
    forklift_numbers = [lift_number.replace('forklift_','') for lift_number in forklift_numbers]

    operator_list = list(Forklift.objects.values_list('normal_operator', flat=True).order_by('id'))
    numbers_list = list(Forklift.objects.values_list('unit_number', flat=True).order_by('id'))          # list of all forklift numbers
    operators_and_numbers = dict(zip(numbers_list, operator_list))   # join the operators list with the forklift numbers list
    
    operators_and_numbers = {key:val for key, val in operators_and_numbers.items() if key in forklift_numbers} # clean up the dictionary based on our list of relevant forklift numbers 
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
    for key, value in operators_and_numbers.items():

        html_code +="""
                            <tr>
                                <td>{}</td>
                                <td>{}</td>
                                <td>{}</td>
                            </tr>
                            """.format(key, value, 'NOT SUBMITTED')
    html_code +="""     </table>
                    </body>"""

    today = (date.today())
    sender_address = os.getenv('NOTIF_EMAIL_ADDRESS')
    sender_pass =  os.getenv('NOTIF_PW')
    print(sender_address)
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


email_issue_list = async_task(taskfunctions.email_checklist_issues)

task_id = async_task(taskfunctions.test_function)


# get the result
task_result = result(task_id)

#async_task('math.modf', 2.5, hook='hooks.print_result')

# hooks.py
#def print_result(task):
#    print(task.result)