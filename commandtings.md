# STEPS FOR SETTING UP THIS PROJECT 

## Program Installs:

### Required:
 - Git - <a href="https://git-scm.com/download/">(Installer download)</a>
 - Python: - <a href="https://www.python.org/downloads/">(Installer download)</a>
    - Be sure to add Python to PATH.
 - Postgres - <a href="https://www.postgresql.org/download/">(Installer download)</a>
 - Docker - <a href="https://docs.docker.com/desktop/install/windows-install/">(Installer download)</a>



## Steps:
<em>Note: skip steps 1,2,6, & 7 if you're just doing a trial deployment with the sample data in db_imports > dump.sql</em>

1. After third-party apps are all installed, open command prompt and execute the command "`python -m pip install C:\Users\` *computer_user_name* `\Documents\kpk-app\hostreqs.txt`"
   
2. Run "`python -m pip install pyodbc @ file:///C:/Users/` *computer_user_name* `/Documents/kpk-app/whls/pyodbc-4.0.32-cp310-cp310-win_amd64.whl`". Close command prompt.

3. Navigate to the Documents folder and open git bash. Set user name and email using "`git config --global user.name "John Doe"`" and then "`git config --global user.email johndoe@example.com`"

4. Still in the same git bash window, clone this repository: "`git clone https://github.com/ParkerMedlin/kpk-app.git`". Close the git bash window when process completes. 

5. Access Kinpak workspace on OneDrive or Sharepoint and navigate to \Blending - Documents\02 Resources\Computer Environment\ and then copy the .env file from there to \kpk-app\.

6.  Navigate to M:\Sage 100 ERP\MAS90\wksetup\Prerequisites\64Bit ODBC\ and run the file `Sage ODBC 64-bit Installer`. 

7. Access Kinpak workspace on OneDrive or Sharepoint and navigate to \Blending - Documents\02 Resources\Computer Environment\ and then run the file `pmedlinAutoODBC.reg`.

8. Start Docker.

9. Open command prompt and execute  "`cd C:\Users\` *computer_user_name* `\Documents\kpk-app\`".

10. Still in the same command prompt or terminal window, execute "`docker-compose -f docker-compose-PROD.yml -p kpk-app build`".

11. Still in the same command prompt or terminal window, execute "`docker-compose -f docker-compose-DEV.yml -p kpk-app up`".

12. Next, import all the db information from a `.sql` file: 
   `SET "PGPASSWORD=blend2021"&& `*"path_to_psql.exe"*` -h localhost -p 5432 -U postgres -d blendversedb -f `*"path_to_dump.sql"*


## Deploying Changes:
1. Run the python script `C:Users/...Documents/kpk-app/python_db_scripts/app_color_switcher.py`

2. Pay attention to the output of this script and restart whichever container is not being used.

3. Wait for the container to restart and then run the script again to switch back to it, now that it's updated.