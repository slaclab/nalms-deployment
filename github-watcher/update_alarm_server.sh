#!/bin/bash

git config --global http.proxy http://sdfproxy.sdf.slac.stanford.edu:3128

git clone $GIT_REPO
cd $GIT_REPO_NAME

echo "Monitoring for updates"

while true
do
    git fetch
    if [ ! $(git rev-parse HEAD) == $(git rev-parse @{u}) ]; then
        echo "Change detected, re-deploying alarm server"
        git pull
        kubectl apply -k alarm-servers/ -n nalms-test
    fi
    sleep 10
done
