import os
from office365.sharepoint.client_context import ClientContext, UserCredential
from dotenv import load_dotenv

def download_to_temp(which_file):
   load_dotenv()
   sharePtInputs = [which_file,os.getenv('O365_EMAIL'),os.getenv('O365_PASS')]
   
   if which_file == "ProductionSchedule":
      file_url = '/sites/PDTN/Shared Documents/Production Schedule/Starbrite KPK production schedule.xlsb'
      client_context_url = r'https://adminkinpak.sharepoint.com/sites/PDTN/'
      download_path = os.path.expanduser('~\\Documents\\kpk-app\\db_imports')+"\\"+'prodschedule.xlsb'
   elif which_file == "BlendingSchedule":
      file_url = '/sites/BLND/Shared Documents/03 Projects/Blending Schedule/Blending-Schedule/BlendingSchedule.xlsb'
      download_path = os.path.expanduser('~\\Documents\\kpk-app\\db_imports')+"\\"+'blndscheduleB.xlsb'
      client_context_url = r'https://adminkinpak.sharepoint.com/sites/BLND/'
   elif which_file == "LotNumGenerator":
      file_url = '/sites/BLND/Shared Documents/01 Spreadsheet Tools/Blending Lot Number Generator/LotNumGenerator-Prod/Blending Lot Number Generator.xlsb'
      download_path = os.path.expanduser('~\\Documents\\kpk-app\\db_imports')+"\\"+'lotnumsB.xlsb'
      client_context_url = r'https://adminkinpak.sharepoint.com/sites/BLND/'
   user_credentials = UserCredential(sharePtInputs[1], sharePtInputs[2])
   ctx = ClientContext(client_context_url).with_credentials(user_credentials)
   try:
      with open(download_path, "wb") as local_file:
         file = ctx.web.get_file_by_server_relative_url(file_url).download(local_file).execute_query()
   except AttributeError:
      download_path = 'SHAREPOINT ERROR: Unable to connect to Sharepoint. Please check internet and then check for Microsoft outages.'

   return download_path