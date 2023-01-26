import datetime as dt

now = dt.datetime.now()
weekday = now.weekday()
if weekday == 4:
    days_to_subtract = 5
else:
    days_to_subtract = 7
cutoff_date = now - dt.timedelta(days=days_to_subtract)
days_from_monday = weekday
this_monday_date = now - dt.timedelta(days=days_from_monday)
this_tuesday_date = this_monday_date + dt.timedelta(days=1)
this_wednesday_date = this_monday_date + dt.timedelta(days=2)
this_thursday_date = this_monday_date + dt.timedelta(days=3)
print('this_monday_date is '+str(this_monday_date))
print('this_tuesday_date is '+str(this_tuesday_date))
print('this_wednesday_date is '+str(this_wednesday_date))
print('this_thursday_date is '+str(this_thursday_date))
print('goof complete')