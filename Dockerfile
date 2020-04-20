FROM python:3.7-slim
LABEL maintainer="David Sn <divad.nnamtdeis@gmail.com>"

# Install required dependencies 
RUN set -ex && \
    DEBIAN_FRONTEND=noninteractive \
    apt-get update && \
    apt-get install -y \
        cron mailutils && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Add crontab file in the cron directory
ADD crontab /etc/cron.d/pylife
RUN chmod 0644 /etc/cron.d/pylife && touch /var/log/cron.log

# Install cron scripts
ADD . /app
RUN pip install -r /app/requirements.txt
ENTRYPOINT [ "/app/entrypoint.sh" ]
