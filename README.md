# pylife-cron
Repository containing updater script to be executed via cron.

## Usage
Use the following content for the docker-compose.yml file, then run docker-compose up.
```
# Use postgres/example user/password credentials
version: '3.1'

services:

  db:
    image: postgres
    restart: always
    environment:
      POSTGRES_PASSWORD: example
      POSTGRES_DB: pylife

  cron:
    image: divadsn/pylife-cron
    restart: always
    environment:
      TZ: "Europe/Warsaw"
      DATABASE_URI: "postgresql://postgres:example@db:5432/pylife"
    depends_on:
      - db
```
