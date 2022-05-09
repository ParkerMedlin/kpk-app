# STEPS FOR SETTING UP THIS PROJECT 

## Prereqs:
 - git
 - Docker
 - python

## Steps:
1. Pull latest files from git into a repository folder.

2. In the init-db-imports, make sure all the csv files are up to date with the latest info. (These will be pulled in to populate the databases ONE TIME)

3. Start Docker (if Docker is not open, you will get a weird error that doesn't actually tell you what the problem is)

4. Open terminal or cmd or whatever

5. cd to the project directory, like the highest level you can be at, & then do: `docker-compose -f docker-compose-DEV.yml build`
    This will build the base image that docker will use to spin up the containers for app and db. (note that this docker-compose-DEV.yml file 
    uses the development server, and the image it builds will not include nginx. To build an image of the full production stack, docker-compose-PROD.yml 
    is your guy.) 

6. `docker-compose -f docker-compose-DEV.yml up`
    This starts the containers and the server, as well as calling makemigrations and migrate. (can think of it like executing docker-compose-DEV.yml)

7. Create an admin user: `docker-compose -f docker-compose-DEV.yml run --rm app sh -c "python manage.py createsuperuser"`
    This will get you access to the admin panel so you can then create other users to test with.

8. Open Docker, open the CLI on the APPLICATION CONTAINER, not the db container, and then import the lot number csv by running `python manage.py import_batches --path /init-db-imports/lotnums.csv`

9. Still in Docker CLI run `python manage.py import_instructions --path /init-db-imports/blendinstructions.csv` to import the blend instructions

10. Close Docker CLI and open cmd on the regular operating system of the HOST MACHINE. cd to the project directory and then run `python AllSagetoPostgres.py`

11. Still in cmd in the os of the host machine, run `python BlendThesetoPostgres.py`

12. Access the server at localhost:8000
    note: if you run `production docker-composePROD.yml`, it will be [your ip address]:1337


## Misc: 
 - If you ever need to burn all the volumes(information accessed and used by containers, eg database files), you run: `docker-compose -f docker-compose-DEV.yml down --volumes`

 - To stop the containers, you can either click stop in the Docker GUI or do: `docker-compose -f docker-compose-DEV.yml stop`

