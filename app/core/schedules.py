from django_q.tasks import schedule
from core import taskfunctions

schedule(taskfunctions.email_checklist_issues,
    cron = '0 32 9 ? * MON,TUE,WED,THU,FRI *'
    )