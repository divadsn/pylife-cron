FROM python:3.6
LABEL maintainer="David Sn <divad.nnamtdeis@gmail.com>"

# Install required dependencies 
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        cron && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Add crontab file in the cron directory
ADD crontab /etc/cron.d/pylife
RUN chmod 0644 /etc/cron.d/pylife && touch /var/log/cron.log

# Install cron scripts
ADD . /app
RUN pip install -r /app/requirements.txt
ENTRYPOINT [ "cron", "-f" ]
