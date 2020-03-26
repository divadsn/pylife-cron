#!/bin/sh

echo TZ=$TZ >> /etc/environment
echo DATABASE_URI=$DATABASE_URI >> /etc/environment

cron && tail -f /var/log/cron.log
