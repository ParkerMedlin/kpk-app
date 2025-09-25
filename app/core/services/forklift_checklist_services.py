from core.kpkapp_utils import checklist_functions
from django.shortcuts import redirect

def update_submission_tracker(request):
    """Update the checklist submission tracking data.
    
    Manually triggers an update of the checklist submission tracker via checklist_functions.
    
    Args:
        request: HTTP request object
        
    Returns:
        Redirect to checklist management page
    """
    checklist_functions.update_checklist_tracker('the manual button on ChecklistMgmt.html')
    return redirect('display-checklist-mgmt-page')

def email_submission_report(request):
    """Email a report of checklist submissions.
    
    Sends an email report containing checklist submission tracking data to the specified recipient.
    
    Args:
        request: HTTP request containing:
            recipient (str): Email address to send report to
            
    Returns:
        Redirect to checklist management page
    """
    recipient_address = request.GET.get('recipient')
    print(recipient_address)
    checklist_functions.email_checklist_submission_tracking('the manual button on ChecklistMgmt.html', recipient_address)
    return redirect('display-checklist-mgmt-page')

def email_issue_report(request):
    """Email a report of checklist issues.
    
    Sends an email report containing checklist issues/problems to the specified recipient.
    
    Args:
        request: HTTP request containing:
            recipient (str): Email address to send report to
            
    Returns:
        Redirect to checklist management page
    """
    recipient_address = request.GET.get('recipient')
    checklist_functions.email_checklist_issues('the manual button on ChecklistMgmt.html', recipient_address)
    return redirect('display-checklist-mgmt-page')