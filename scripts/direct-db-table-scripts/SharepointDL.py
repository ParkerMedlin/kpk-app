import os
import tempfile
from office365.sharepoint.client_context import ClientContext, UserCredential
import easygui as eg

def download_to_temp():
   # input box to get the user credentials and the string indicating which file to grab.
   # This box will yield a list []
   fieldList = ['File','Email','Password']
   defaultList = ['ProductionSchedule', 'pmedlin@kinpakinc.com', 'thisisnotthepassword']
   sharePtInputs = eg.multenterbox('Enter file details', 'File Information', fieldList, defaultList)
   (sharePtInputs[0], sharePtInputs[1], sharePtInputs[2])
   
   if sharePtInputs[0] == "ProductionSchedule":
      file_url = '/sites/PDTN/Shared Documents/Production Schedule/Starbrite KPK production schedule.xlsb'
      client_context_url = r'https://adminkinpak.sharepoint.com/sites/PDTN/'
   elif sharePtInputs[0] == "BlendingSchedule":
      file_url = '/sites/BLND/Shared Documents/03 Projects/Blending Schedule/Blending-Schedule/BlendingSchedule_2.0.xlsb'
      client_context_url = r'https://adminkinpak.sharepoint.com/sites/BLND/'
   user_credentials = UserCredential(sharePtInputs[1], sharePtInputs[2])
   ctx = ClientContext(client_context_url).with_credentials(user_credentials)
   download_path = os.path.join(tempfile.mkdtemp(), os.path.basename(file_url))
   with open(download_path, "wb") as local_file:
      file = ctx.web.get_file_by_server_relative_url(file_url).download(local_file).execute_query()
   print("[Ok] file has been downloaded into: {0}".format(download_path))

   return download_path