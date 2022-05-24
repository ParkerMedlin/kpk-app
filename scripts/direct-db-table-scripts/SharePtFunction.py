import os
import tempfile

from office365.sharepoint.client_context import ClientContext, UserCredential
# from tests import test_team_site_url, test_client_credentials

user_credentials = UserCredential('pmedlin@kinpakinc.com','K2P1K#02')

ctx = ClientContext(r'https://adminkinpak.sharepoint.com/').with_credentials(user_credentials)
# file_url = '/sites/team/Shared Documents/big_buck_bunny.mp4'
file_url = '/sites/PDTN/Shared Documents/Production Schedule/Starbrite KPK production schedule.xlsb'
download_path = os.path.join(tempfile.mkdtemp(), os.path.basename(file_url))
# download_path = "C:\Users\Blendverse\Desktop\\"
with open(download_path, "wb") as local_file:
    file = ctx.web.get_file_by_server_relative_path(file_url).download(local_file).execute_query()
    #file = ctx.web.get_file_by_server_relative_url(file_url).download(local_file).execute_query()
print("[Ok] file has been downloaded into: {0}".format(download_path))





# from urllib.parse import urlparse
# from office365.runtime.auth.authentication_context import AuthenticationContext
# from office365.sharepoint.client_context import ClientContext

# def download_file(local_absolute_path:str, global_absolute_path:str, client_context:ClientContext) -> None:
#         print(f"The file {global_absolute_path} is being prepared for download.")
#         download_location = urlparse(global_absolute_path)
#         file_to_download = client_context.web.get_file_by_server_relative_url(download_location)
#         with open(local_absolute_path, "wb") as local_file:
#             file_to_download.download_session(local_file).execute_query()
#         print(f"──► Download successful. The file has been saved as {local_absolute_path}\n")