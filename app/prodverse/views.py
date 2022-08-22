from django.shortcuts import render

def issueSheets(request, line):
    allRunsQS = IssueSheetNeeded.objects.all()
    if line == 'INLINE':
        lineRunsQS = allRunsQS.filter(prodline__icontains='INLINE').order_by('starttime')
    if line == 'PDLINE':
        lineRunsQS = allRunsQS.filter(prodline__icontains='PD LINE').order_by('starttime')
    if line == 'JBLINE':
        lineRunsQS = allRunsQS.filter(prodline__icontains='JB LINE').order_by('starttime')
    if line == 'all':
        lineRunsQS = allRunsQS.order_by('prodline','starttime')
    dateToday = date.today().strftime('%m/%d/%Y')

    return render(request, 'core/issuesheet.html', {'lineRunsQS':lineRunsQS, 'line':line, 'dateToday':dateToday})
