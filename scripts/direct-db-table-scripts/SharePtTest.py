import os
import tempfile

from office365.sharepoint.client_context import ClientContext, UserCredential
# from tests import test_team_site_url, test_client_credentials

user_credentials = UserCredential('pmedlin@kinpakinc.com','K2P1K#02')

ctx = ClientContext(r'https://adminkinpak.sharepoint.com/').with_credentials(user_credentials)
# file_url = '/sites/team/Shared Documents/big_buck_bunny.mp4'
file_url = r'https://adminkinpak.sharepoint.com/:x:/r/sites/PDTN/Shared%20Documents/Production%20Schedule/Starbrite%20KPK%20production%20schedule.xlsb?d=w400ca0f10f484ecea821d980e7da1f1f&csf=1&web=1&e=a0luEG'
download_path = os.path.join(tempfile.mkdtemp(), os.path.basename(file_url))
# download_path = "C:\Users\Blendverse\Desktop\\"
with open(download_path, "wb") as local_file:
    file = ctx.web.get_file_by_server_relative_path(file_url).download(local_file).execute_query()
    #file = ctx.web.get_file_by_server_relative_url(file_url).download(local_file).execute_query()
print("[Ok] file has been downloaded into: {0}".format(download_path))