import os
import tempfile
from office365.sharepoint.client_context import ClientContext, UserCredential
import easygui as eg
from dotenv import load_dotenv, dotenv_values

def download_to_temp(whichfile):
   config = dotenv_values(".env")
   load_dotenv()
   print(os.getenv('O365_EMAIL'))
   print("ok")
   sharePtInputs = [whichfile,os.getenv('O365_EMAIL'),os.getenv('O365_PASS')]
   
   if whichfile == "ProductionSchedule":
      file_url = '/sites/PDTN/Shared Documents/Production Schedule/Starbrite KPK production schedule.xlsb'
      client_context_url = r'https://adminkinpak.sharepoint.com/sites/PDTN/'
      download_path = os.path.expanduser('~\Documents')+"\\"+'prodschedule.xlsb'
   elif whichfile == "BlendingSchedule":
      file_url = '/sites/BLND/Shared Documents/03 Projects/Blending Schedule/Blending-Schedule/BlendingSchedule.xlsb'
      download_path = os.path.expanduser('~\Documents\kpk-app\init-db-imports')+"\\"+'blndscheduleB.xlsb'
      client_context_url = r'https://adminkinpak.sharepoint.com/sites/BLND/'
   elif whichfile == "LotNumGenerator":
      file_url = '/sites/BLND/Shared Documents/01 Spreadsheet Tools/Blending Lot Number Generator/LotNumGenerator-Prod/Blending Lot Number Generator.xlsb'
      download_path = os.path.expanduser('~\Documents\kpk-app\init-db-imports')+"\\"+'lotnumsB.xlsb'
      client_context_url = r'https://adminkinpak.sharepoint.com/sites/BLND/'
   user_credentials = UserCredential(sharePtInputs[1], sharePtInputs[2])
   ctx = ClientContext(client_context_url).with_credentials(user_credentials)
   try:
      with open(download_path, "wb") as local_file:
         file = ctx.web.get_file_by_server_relative_url(file_url).download(local_file).execute_query()
   except AttributeError:
      print('This script is about to tell a lie')
      download_path = 'Error Encountered'

   print("[Ok] file has been downloaded into: {0}".format(download_path))

   return download_path