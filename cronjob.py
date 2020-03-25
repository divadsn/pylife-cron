#!/usr/bin/env python3
import argparse
import os
import re
import pytz
import socket
import urllib.request
import urllib.error
import logging

from time import time
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, create_engine, func, exc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from bs4 import BeautifulSoup

# Regular expressions to extract data from house pages
PRICE_REGEX = r"^\D*(\d+(?:\.\d+)?)"
DATE_REGEX = r"[0-9]{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[1-2][0-9]|3[0-1])"

# SQL Alchemy database URI
DB_URI = os.environ.get("DATABASE_URI", "postgresql://postgres:example@localhost:5432/postgres")

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger("cronjob")

# Fix wrong timezone behavior in Python
timezone = pytz.timezone("Europe/Warsaw")

# Trying to avoid as much trouble as possbile by "mocking" a real browser request
custom_headers = {
    "Referer": "http://panel.pylife.pl",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:73.0) Gecko/20100101 Firefox/73.0"
}

Base = declarative_base()


class House(Base):
    __tablename__ = "houses"

    id = Column(Integer, primary_key=True, nullable=False)
    x = Column(Integer, nullable=False)
    y = Column(Integer, nullable=False)
    name = Column(Text, nullable=False)
    location = Column(Text, nullable=False)
    owner = Column(String(22), nullable=True)
    price = Column(Float, nullable=True)
    expiry = Column(DateTime, nullable=True)
    last_update = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


def get_houses():
    request = urllib.request.Request("http://panel.pylife.pl/domy", headers=custom_headers)
    page = urllib.request.urlopen(request, timeout=10)
    bs4 = BeautifulSoup(page, "html.parser")

    table = bs4.find("table", {"id": "tdomy"})
    houses = []

    for row in table.find("tbody").find_all("tr"):
        data = row.find_all("td")
        house = {
            "id": int(row["hid"]),
            "x": int(float(row["x"])),
            "y": int(float(row["y"])),
            "name": data[0].string,
            "location": data[1].string,
            "owner": data[2].string if data[2].string != "Do wynajęcia" else None,
            "price": data[3].string if is_float(data[3].string) else False,
            "expiry": None
        }

        houses.append(house)

    return houses


def get_house_details(id: int):
    request = urllib.request.Request("http://panel.pylife.pl/domy/" + str(id), headers=custom_headers)
    page = urllib.request.urlopen(request, timeout=10)
    bs4 = BeautifulSoup(page, "html.parser")

    body = bs4.find("div", {"id": "m_domy"})
    details = {}

    for tag in body.find_all(text=True):
        if "za dobę" in tag.string:
            details["price"] = float(re.findall(PRICE_REGEX, tag.string)[0])
        elif "Dom jest opłacony do" in tag.string:
            details["expiry"] = parse_date(re.findall(DATE_REGEX, tag.string)[0])

    return details


def parse_date(date: str):
    dt = datetime.strptime(date, "%Y-%m-%d")
    return timezone.localize(dt)


def is_float(value: str):
    try:
        float(value)
        return True
    except ValueError:
        return False


def connect_db():
    engine = create_engine(DB_URI)
    engine.connect()

    Session = sessionmaker(bind=engine)
    return Session()


def execute_cron(force_update: bool):
    # Store start timestamp to calculate execution time
    start_time = time()

    logger.info("Play Your Life cron script, version 1.0")
    logger.info("Connecting to database...")

    try:
        session = connect_db()
    except exc.SQLAlchemyError as error:
        logger.fatal("Could not connect to database!")
        logger.fatal(error.orig) # pylint: disable=maybe-no-member
        exit(1)

    logger.info("Downloading house data from \"http://panel.pylife.pl/domy\"...")

    try:
        houses = get_houses()
    except urllib.error.URLError as error:
        logger.fatal("Could not download data from user panel!")
        logger.fatal(error.reason)
        exit(1)

    # List containing houses that need updating
    updates = []

    if args.force_update:
        logger.warning("Force update is enabled, all house details will be updated!")
        updates = houses
    else:
        for house in houses:
            old_house = session.query(House).get(house["id"])

            # Check if house exists in database
            if not old_house:
                logger.warning(f"House \"{house['name']}\" with ID {house['id']} does not exist in database!")
                continue

            # Add house to list if ownership has changed or has missing price/expiry
            if old_house.owner != house["owner"] or old_house.price == 0:
                updates.append(house)

    # Exit if nothing to update
    if len(updates) > 0:
        logger.info(f"Found {len(updates)} house(s) to be updated.")
    else:
        logger.info("Everything up-to-date, nothing to do.")
        exit(0)

    for house in updates:
        logger.info(f"Updating house \"{house['name']}\" with ID {house['id']}...")

        # Get house details if price is not set
        if not house["price"]:
            try:
                details = get_house_details(house["id"])
            except urllib.error.URLError:
                logger.error("Could not download house details from user panel, skipping!")
                continue
            except socket.timeout:
                logger.error("Connection timed out, skipping!")
                continue

            house.update(details)

        # Insert or update house in table
        session.merge(House(id=house["id"], x=house["x"], y=house["y"], name=house["name"], location=house["location"],
                            owner=house["owner"], price=house["price"], expiry=house["expiry"]))

    logger.info("Saving data to database...")
    session.commit()

    # Show total execution time since start_time
    logger.info(f"Done! Job finished in {round(time() - start_time, 2)} seconds.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Updates house data from Play Your Life user panel.")
    parser.add_argument("--force-update", help="updates all house details", action="store_true")
    args = parser.parse_args()

    logger.info(f"Starting cronjob at {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    execute_cron(args.force_update)
