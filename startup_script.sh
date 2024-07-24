#!/bin/bash
apt-get update -y
apt-get install nginx -y
apt-get install wget -y
wget https://sonal-bucket.s3.ap-northeast-2.amazonaws.com/index.hmtl
cp ./index.html /var/www/html/*
systemctl restart nginx