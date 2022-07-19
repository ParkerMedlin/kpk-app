from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.management import call_command
import os
from datetime import datetime as dt
from datetime import date
import datetime


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

logger = get_task_logger(__name__)

@shared_task
def update_checklist_tracker():
    from core.models import ChecklistSubmissionTracker, ChecklistLog, Forklift
    forkliftNumbers = list(Forklift.objects.values_list('unit_number', flat=True).order_by('id'))
    rightNow = dt.now()
    yesterday = date.today()-datetime.timedelta(days=1)
    oneAMtoday = rightNow.replace(hour=1, minute=0).strftime('%Y-%m-%d')
    checklistsToday = ChecklistLog.objects.filter(submitted_date__gt=oneAMtoday)
    if not ChecklistSubmissionTracker.objects.filter(check_date__gt=yesterday).exists():
        resultsDict = {}
        for forklift in forkliftNumbers:
            if checklistsToday.filter(unit_number__unit_number__icontains=forklift).exists():
                resultsDict[forklift] = "Report Submitted"
            else:
                resultsDict[forklift] = "MISSING"

        ChecklistSubmissionTracker.objects.create(
            forklift_1 = resultsDict['1'],
            forklift_2 = resultsDict['2'],
            forklift_3 = resultsDict['3'],
            forklift_4 = resultsDict['4'],
            forklift_5 = resultsDict['5'],
            forklift_6 = resultsDict['6'],
            forklift_7 = resultsDict['7'],
            forklift_8 = resultsDict['8'],
            forklift_9 = resultsDict['9'],
            forklift_10 = resultsDict['10'],
            forklift_11 = resultsDict['11'],
            forklift_12 = resultsDict['12'],
            forklift_13 = resultsDict['13'],
            forklift_15 = resultsDict['15'],
            forklift_16 = resultsDict['16'],
            forklift_17 = resultsDict['17'],
            forklift_18 = resultsDict['18'],
            forklift_19 = resultsDict['19'],
            forklift_20 = resultsDict['20'],
            forklift_21 = resultsDict['21'],
            forklift_22 = resultsDict['22'],
            forklift_23 = resultsDict['23'],
            forklift_24 = resultsDict['24'],
            forklift_25 = resultsDict['25'],
            forklift_26 = resultsDict['26'],
            forklift_27 = resultsDict['27'],
            forklift_28 = resultsDict['28'],
            forklift_29 = resultsDict['29'],
            forklift_30 = resultsDict['30'],
            forklift_32 = resultsDict['32'],
            forklift_34 = resultsDict['34'],
            forklift_35 = resultsDict['35'],
            forklift_36 = resultsDict['36'],
            forklift_37 = resultsDict['37'],
            forklift_38 = resultsDict['38'],
            forklift_39 = resultsDict['39'],
            forklift_40 = resultsDict['40'],
            forklift_41 = resultsDict['41'],
            forklift_42 = resultsDict['42'],
            forklift_43 = resultsDict['43'],
            forklift_44 = resultsDict['44'],
            forklift_45 = resultsDict['45'],
            forklift_46 = resultsDict['46'],
            forklift_47 = resultsDict['47'],
            forklift_48 = resultsDict['48'],
            forklift_49 = resultsDict['49'],
            forklift_50 = resultsDict['50'],
            forklift_Rental1 = resultsDict['Rental1'],
            forklift_Rental2 = resultsDict['Rental2'],
            forklift_Rental3 = resultsDict['Rental3']
            )

@shared_task
def DAILY_email_checklistSubTrack():
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from core.models import ChecklistSubmissionTracker, Forklift, CeleryTaskSetting

    if CeleryTaskSetting.objects.first().checklist_sub_track:
        checksQs = ChecklistSubmissionTracker.objects.filter(check_date__gte=date.today()).values() # the point of this is to get a list of all the unit_numbers 
        checksDict = checksQs[0]                                                                    # for forklifts that don't have a checklist submission for today 
        refinedChecksDict = {key:val for key, val in checksDict.items() if val != 'Report Submitted' and key != 'id' and key != 'check_date'}
        columnNameList = list(refinedChecksDict.keys())
        forkliftNumList = [forkliftNum.replace('forklift_','') for forkliftNum in columnNameList] # here is our list of the relevant forklift numbers

        forkliftOperatorsList = list(Forklift.objects.values_list('normal_operator', flat=True).order_by('id')) # list of all operators
        forkliftNumsList = list(Forklift.objects.values_list('unit_number', flat=True).order_by('id'))          # list of all forklift numbers
        forkliftOperatorsDict = dict(zip(forkliftNumsList,forkliftOperatorsList))   # join the operators list with the forklift numbers list
        
        refinedForkliftOpDict = {key:val for key, val in forkliftOperatorsDict.items() if key in forkliftNumList} # clean up the dictionary based on our list of relevant forklift numbers 
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
    
@shared_task
def DAILY_email_checklistIssues():
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.image import MIMEImage
    from core.models import ChecklistLog, CeleryTaskSetting

    if CeleryTaskSetting.objects.first().checklist_issues:
        logsQs = ChecklistLog.objects.filter(submitted_date__gte=date.today()).filter(
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
        
    
        allIssuesTupleDict = {}
        for object in logsQs:
            if object.engine_oil == 'Bad':
                allIssuesTupleDict[object.unit_number.unit_number + '_Engine_Oil_Issue'] = (object.engine_oil_comments, object.operator_name)
            if object.propane_tank == 'Bad':
                allIssuesTupleDict[object.unit_number.unit_number + '_Propane_Tank_Issue'] = (object.propane_tank_comments, object.operator_name)
            if object.radiator_leaks == 'Bad':
                allIssuesTupleDict[object.unit_number.unit_number + '_Radiator_Leaks_Issue'] = (object.radiator_leaks_comments, object.operator_name)
            if object.tires == 'Bad':
                allIssuesTupleDict[object.unit_number.unit_number + '_Tires_Issue'] = (object.tires_comments, object.operator_name)
            if object.mast_and_forks == 'Bad':
                allIssuesTupleDict[object.unit_number.unit_number + '_Mast_and_Forks_Issue'] = (object.mast_and_forks_comments, object.operator_name)
            if object.leaks == 'Bad':
                allIssuesTupleDict[object.unit_number.unit_number + '_Leaks_Issue'] = (object.leaks_comments, object.operator_name)
            if object.horn == 'Bad':
                allIssuesTupleDict[object.unit_number.unit_number + '_Horn_Issue'] = (object.horn_comments, object.operator_name)
            if object.driver_compartment == 'Bad':
                allIssuesTupleDict[object.unit_number.unit_number + '_Driver_Compartment_Issue'] = (object.driver_compartment_comments, object.operator_name)
            if object.seatbelt == 'Bad':
                allIssuesTupleDict[object.unit_number.unit_number + '_Seatbelt_Issue'] = (object.seatbelt_comments, object.operator_name)
            if object.battery == 'Bad':
                allIssuesTupleDict[object.unit_number.unit_number + '_Battery_Issue'] = (object.battery_comments, object.operator_name)
            if object.safety_equipment == 'Bad':
                allIssuesTupleDict[object.unit_number.unit_number + '_Safety_Equipment_Issue'] = (object.safety_equipment_comments, object.operator_name)
            if object.steering == 'Bad':
                allIssuesTupleDict[object.unit_number.unit_number + '_Steering_Issue'] = (object.steering_comments, object.operator_name)
            if object.brakes == 'Bad':
                allIssuesTupleDict[object.unit_number.unit_number + '_Brakes_Issue'] = (object.brakes_comments, object.operator_name)
        
        if len(allIssuesTupleDict)!=0:
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

            for key, value in allIssuesTupleDict.items():
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
                            <div>
                            <img src="http://www.clipartbest.com/cliparts/niX/o7g/niXo7gM5T.jpg" alt="img" />
                            <pre>
             _____              _ _   
            |  __ \            ( ) |  
            | |  | | ___  _ __ |/| |_ 
            | |  | |/ _ \| '_ \  | __|
            | |__| | (_) | | | | | |_ 
            |_____/ \___/|_| |_|  \__|
                                    
                                    
                            </pre>
                            <pre>
                               _    
                              | |   
                     __ _  ___| |_  
                    / _` |/ _ \ __| 
                   | (_| |  __/ |_  
                    \__, |\___|\__| 
                    __/  |          
                    |___/           
                            </pre>
                            <pre>
                                    _                      _   
                                    | |                    | |  
            ___ ___  _ __ ___  _ __ | | __ _  ___ ___ _ __ | |_ 
            / __/ _ \| '_ ` _ \| '_ \| |/ _` |/ __/ _ \ '_ \| __|
           | (_| (_) | | | | | | |_) | | (_| | (_|  __/ | | | |_ 
            \___\___/|_| |_| |_| .__/|_|\__,_|\___\___|_| |_|\__|
                               | |                               
                               |_|                               
                            </pre>
                            </div>
                            ''' 



        today = (date.today())
        sender_address = os.getenv('NOTIF_EMAIL_ADDRESS')
        sender_pass =  os.getenv('NOTIF_PW')
        print(sender_address)
        receiver_address = 'pmedlin@kinpakinc.com'
        message = MIMEMultipart('alternative')
        message['From'] = sender_address
        message['To'] = receiver_address
        message['Subject'] = 'All forklift log issues for '+str(today)
        message.attach(MIMEText(html_code, 'html'))


        ### CREATE SMTP SESSION AND SEND THE EMAIL ###
        session = smtplib.SMTP('smtp.gmail.com', 587) #use gmail with port
        session.starttls() #enable security
        session.login(sender_address, sender_pass) #login with mail_id and password
        session.sendmail(sender_address, receiver_address, message.as_string())
        session.quit()

@shared_task
def testTask():
    sender_address = os.getenv('NOTIF_EMAIL_ADDRESS')
    sender_pass =  os.getenv('NOTIF_PW')
    print(sender_address)
    print('Hello there!')