from SharePtFunction import download_file
from office365.sharepoint.client_context import ClientContext, UserCredential

user_credentials = UserCredential('pmedlin@kinpakinc.com','K2P1K#02')
local_abs = 'C:\\Users\\pmedlin\\Desktop\\thing.xlsb'
glob = 'https://adminkinpak.sharepoint.com/sites/PDTN/Shared%20Documents/Production%20Schedule/Starbrite%20KPK%20production%20schedule.xlsb'

ctx = ClientContext(r'https://adminkinpak.sharepoint.com/').with_credentials(user_credentials)
download_file(local_abs,glob,ctx)
