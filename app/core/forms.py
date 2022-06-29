from django import forms

reportchoices = [('Chem-Shortage','Chem Shortage'),
                    ('Startron-Runs','Startron Runs'),
                    ('Transaction-History','Transaction History'),
                    ('Lot-Numbers','Lot Numbers'),
                    ('All-Upcoming-Runs','All Upcoming Runs'),
                    ('Physical-Count-History','Physical Count History'),
                    ('Counts-And-Transactions','Counts And Transactions')
                    ]

class ReportForm(forms.Form):
    part_number=forms.CharField(max_length=100,label='Enter Part Number:')
    # description=forms.CharField(max_length=100,label='Item Description:')
    which_report=forms.CharField(
        widget=forms.Select(choices=reportchoices)
        )

