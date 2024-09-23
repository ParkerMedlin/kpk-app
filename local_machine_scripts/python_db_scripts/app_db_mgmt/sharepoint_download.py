import os
from dotenv import load_dotenv
from msal import ConfidentialClientApplication
import requests

def get_access_token():
    load_dotenv()
    app = ConfidentialClientApplication(
        os.getenv('AZURE_CLIENT_ID'),
        authority=f"https://login.microsoftonline.com/{os.getenv('AZURE_TENANT_ID')}",
        client_credential=os.getenv('AZURE_CLIENT_SECRET')
    )
    
    result = app.acquire_token_silent(["https://graph.microsoft.com/.default"], account=None)
    if not result:
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    
    if "access_token" in result:
        return result["access_token"]
    else:
        raise Exception("Failed to acquire token, make sure it's not 9/11, if it is, check the Azure portal at https://entra.microsoft.com/?feature.tokencaching=true&feature.internalgraphapiversion=true#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Credentials/appId/6318854d-eeff-454e-bf84-5f529f147fba/isMSAApp~/false")


def download_to_temp(which_file):
    access_token = get_access_token()
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }
    
    site_id = "adminkinpak.sharepoint.com,ea15b2fd-35e7-426f-a90b-605f97dadca0,45d34af9-f92f-425d-8feb-e1b3e9f3207f"
    drive_id = "b!_bIV6uc1b0KpC2Bfl9rcoPlK00Uv-V1Cj-vhs-nzIH8aDWyU6El7Tpp_ePWKacOm"
    
    if which_file == "ProductionSchedule":
        file_path = '/Production Schedule/Starbrite KPK production schedule.xlsb'
        download_path = os.path.expanduser('~\\Documents\\kpk-app\\db_imports\\prodschedule.xlsb')
    elif which_file == "BlendingSchedule":
        file_path = '/03 Projects/Blending Schedule/Blending-Schedule/BlendingSchedule.xlsb'
        download_path = os.path.expanduser('~\\Documents\\kpk-app\\db_imports\\blndscheduleB.xlsb')
    elif which_file == "LotNumGenerator":
        file_path = '/01 Spreadsheet Tools/Blending Lot Number Generator/LotNumGenerator-Prod/Blending Lot Number Generator.xlsb'
        download_path = os.path.expanduser('~\\Documents\\kpk-app\\db_imports\\lotnumsB.xlsb')
    else:
        raise ValueError("Invalid file type specified")

    # Get the file metadata
    file_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:{file_path}"
    response = requests.get(file_url, headers=headers)
    response.raise_for_status()
    file_metadata = response.json()

    # Get the download URL
    download_url = file_metadata.get('@microsoft.graph.downloadUrl')
    if not download_url:
        raise Exception("Failed to get download URL")

    # Download the file
    try:
        with requests.get(download_url, stream=True) as r:
            r.raise_for_status()
            with open(download_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
    except requests.RequestException as e:
        return f'SHAREPOINT ERROR: Unable to download file. Error: {str(e)}'

    return download_path