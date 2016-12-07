# Haystack
A distributed file system for storing photos based on Facebook's Haystack paper.

Intructions to run the project: 
Cd to the directory pystack.
Please setup docker-compose first - https://docs.docker.com/compose/install/

Navigate to project directory in terminal and run the following commands:

docker-compose build
docker-compose up


This will start a webserver that will be mapped to port 5000 of localhost. So, you can access the web app at http://localhost:5000 . If you are using a mac, you will have to replace localhost with boot2docker IP.
