from pyzabbix import ZabbixAPI
from dotenv import load_dotenv
import os
import asyncio
from Config import (
    ZABBIX_SERVER,
    ZABBIX_API_USER,
    ZABBIX_API_PWD,
    API_TOKEN
)
from Database import db
from tinydb import Query
from aiogram import Bot, Dispatcher

# from aiogram import executor
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

import aiogram.utils.formatting as AioFormat
import aioschedule as schedule
# import schedule
import time
import logging

logging.basicConfig(filename='processing.log', level=logging.INFO,
                    format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s')

# api object
zapi = ZabbixAPI(ZABBIX_SERVER)

# Login to the Zabbix API
zapi.login(ZABBIX_API_USER, ZABBIX_API_PWD)

record = Query()

storage = MemoryStorage()
bot = Bot(token=API_TOKEN)

#save current users with active schedulers
active_userlist={}

# async def send_message_wrap(chat_id,message_text):
#     await bot.send_message(chat_id=chat_id,text=message_text)

def sort_by_key(e):
    return e['host']

#send message
async def send_message_core(chat_id, message_text):
    async with Bot(
                token=API_TOKEN,
                default=DefaultBotProperties(
                    parse_mode=ParseMode.HTML,
                ),
        ) as bot:
            await bot.send_message(chat_id=chat_id, text=message_text)

# send problems to chats
async def send_message(chat_id, host_groups):
    message_text = ""
    message_array = []
    # get problems
    try:
        unack_triggers = zapi.trigger.get(only_true=1,
                                          skipDependent=1,
                                          monitored=1,
                                          active=1,
                                          output='extend',
                                          expandDescription=1,
                                          selectHosts=['host'],
                                          withLastEventUnacknowledged=1,
                                          groupids=host_groups
                                          )

        # todo: opdata hosts
        priority = [
            {"0": "*Not classified*", "1": "*Info*", "2": "*Warn*", "3": "*Avg*", "4": "*High*", "5": "*Disaster*"}
        ]

        problems = []

        for t in unack_triggers:
            if int(t['value']) == 1:
                priority_item = priority[0][t['priority']]
                item = {"host": t['hosts'][0]['host'], "priority": priority_item, "desc": t['description']}
                problems.append(item)
                # message_text += "<b>"+t['hosts'][0]['host'] + "</b> \r\n " + str(t['description']) + " \n"

        problems.sort(key=sort_by_key)

        current_host = ""

        for i in problems:

            if i["host"] == current_host:
                message_text += "<u>" + i["priority"] + "</u> " + i["desc"] + "\r\n"
            else:
                message_text += "<b>" + i["host"] + "</b>\r\n" "<u>" + i["priority"] + "</u> " + i["desc"] + "\r\n"

            current_host = i["host"]

            if len(message_text) > 4000:
                message_array.append(message_text)
                message_text=""

    except Exception as e:
        message_text = "Error in processing logic. See server logs."
        logging.error(f"Unresolved error: {e}")

    if message_array != []:
        for msg in message_array:
            send_message_core(chat_id,msg)

    if message_text != "":
        async with Bot(
                token=API_TOKEN,
                default=DefaultBotProperties(
                    parse_mode=ParseMode.HTML,
                ),
        ) as bot:
            await bot.send_message(chat_id=chat_id, text=message_text)

#    await bot.send_message(chat_id=chat_id, text=message_text, parse_mode=ParseMode.HTML)  # MARKDOWN_V2)

def update_schedule_core():
    try:
        usr_settings = db.all()
    except Exception as e:
        logging.error(f"DB error: {e}")

    for i in usr_settings:
        chat_id = i["chat_id"]
        host_groups = i["host_groups"]
        user_schedule = i["schedule"]
        intervals = [{"1m": 1, "3m": 3, "30m": 30, "1h": 60, "Never": 0}]
        interval = intervals[0][user_schedule]
        #New user
        if interval != 0 and chat_id not in active_userlist.keys():
            logging.info(f"New user: {chat_id} - new interval: {interval}")
            schedule.every(interval).minutes.do(send_message, chat_id=chat_id, host_groups=host_groups).tag((str(chat_id), 'tag'))
            active_userlist[chat_id] = interval
        #Update existing chat_id settings
        if chat_id in active_userlist.keys() and interval != active_userlist[chat_id] and interval != 0:
            logging.info(f"Change schedule for user: {chat_id} - new interval: {interval}")
            schedule.clear((str(chat_id),'tag'))
            schedule.every(interval).minutes.do(send_message, chat_id=chat_id, host_groups=host_groups).tag((str(chat_id), 'tag'))
            active_userlist[chat_id] = interval
        #Delete schedule
        if interval == 0 and chat_id in active_userlist.keys():
            logging.info(f"Delete schedule for user: {chat_id} ")
            schedule.clear((str(chat_id),'tag'))
            active_userlist[chat_id] = interval

def notify_job():
    update_schedule_core()

async def scheduler_job():
    while 1:
        await schedule.run_pending()
        await asyncio.sleep(1)


async def update_scheduler():
    update_schedule_core()

async def start_bot():
    dp = Dispatcher(storage=storage)
    await dp.start_polling(bot)


async def main():
    schedule.clear()

    notify_job()

    schedule.every(2).minutes.do(update_scheduler)
    # task_bot = asyncio.create_task(start_bot())
    task_scheduler = asyncio.create_task(scheduler_job())

    await task_scheduler
    # await task_bot


if __name__ == "__main__":
    asyncio.run(main())
