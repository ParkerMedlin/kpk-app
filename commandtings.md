# STEPS FOR SETTING UP THIS PROJECT 

### Required:
 - Git - <a href="https://git-scm.com/download/">(Installer download)</a>
 - Python: - <a href="https://www.python.org/downloads/">(Installer download)</a>
    - Be sure to add Python to PATH.
    - Install host system requirements using `python -m pip install -r hostreqs.txt` or use a venv if you're a nerd
 - Postgres - <a href="https://www.postgresql.org/download/">(Installer download)</a>
    - Only need commandline tools, nothing else
 - Docker - <a href="https://docs.docker.com/desktop/install/windows-install/">(Installer download)</a>


## Steps:
1. run app_deploy.bat
2. profit

## Deploying Changes:
1. Run the python script `C:Users/...Documents/kpk-app/python_db_scripts/app_color_switcher.py`
2. Click the <button>button</button> , wait for container to restart , clik <button>button</button> again

## Reading Logs
`docker logs -f --details --timestamps --since="yyyy-mm-ddTHH:MM:SS" --until="yyyy-mm-ddTHH:MM:SS" my_container_name`