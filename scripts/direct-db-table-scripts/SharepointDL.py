import os
import tempfile
from office365.sharepoint.client_context import ClientContext, UserCredential

def download_to_temp(theFile:str):
   if theFile == "ProductionSchedule":
      file_url = '/sites/PDTN/Shared Documents/Production Schedule/Starbrite KPK production schedule.xlsb'
      client_context_url = r'https://adminkinpak.sharepoint.com/sites/PDTN/'
   elif theFile == "BlendingSchedule":
      file_url = '/sites/BLND/Shared Documents/03 Projects/Blending Schedule/Blending-Schedule/BlendingSchedule_2.0.xlsb'
      client_context_url = r'https://adminkinpak.sharepoint.com/sites/BLND/'

   user_credentials = UserCredential('pmedlin@kinpakinc.com','K2P1K#02')
   ctx = ClientContext(client_context_url).with_credentials(user_credentials)
   download_path = os.path.join(tempfile.mkdtemp(), os.path.basename(file_url))
   with open(download_path, "wb") as local_file:
      file = ctx.web.get_file_by_server_relative_url(file_url).download(local_file).execute_query()
   print("[Ok] file has been downloaded into: {0}".format(download_path))