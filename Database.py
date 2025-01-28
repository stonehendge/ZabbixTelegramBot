from tinydb import TinyDB, Query

db = TinyDB('db.json')

record = Query()

#db.truncate()

async def add_user_settings(chat_id, host_groups, schedule, last_update):
    db.insert({'chat_id': chat_id, 'host_groups': host_groups, 'schedule': schedule, 'last_update': last_update})


async def update_user_settings(chat_id, host_groups, schedule, last_update):
    db.update({'chat_id': chat_id, 'host_groups': host_groups, 'schedule': schedule, 'last_update': last_update},record.chat_id==chat_id)


def get_user_settings(chat_id) -> list:
    result=[]
    result = db.search(record.chat_id == chat_id)
    return result