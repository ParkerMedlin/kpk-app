docker-compose -f docker-compose-DEV.yml down --volumes
docker-compose -f docker-compose-DEV.yml build
docker-compose -f docker-compose-DEV.yml up