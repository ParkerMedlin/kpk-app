from django import forms

reportchoices = [('Chem-Shortage','Chem-Shortage'),
                    ('Startron-Runs','Startron-Runs'),
                    ('Transaction-History','Transaction-History'),
                    ('All-Lot-Numbers','All-Lot-Numbers'),
                    ('All-Upcoming-Runs','All-Upcoming-Runs'),
                    ('Physical-Count-History','Physical-Count-History')
                    ]

class ReportForm(forms.Form):
    part_number=forms.CharField(max_length=100,label='Enter Part Number:')
    item_description=forms.CharField(max_length=100,label='Item Description:')
    which_report=forms.CharField(widget=forms.RadioSelect(choices=reportchoices))

