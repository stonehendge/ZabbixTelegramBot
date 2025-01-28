import asyncio
import datetime
import logging
import operator
import os

from Config import (
    ZABBIX_SERVER,
    ZABBIX_API_USER,
    ZABBIX_API_PWD,
    API_TOKEN
)

from Database import (
    add_user_settings,
    db,
    update_user_settings,
    get_user_settings
)
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Message

from aiogram_dialog import (
    Dialog,
    DialogManager,
    StartMode,
    Window,
    setup_dialogs,
)
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Cancel, Multiselect, Start, SwitchTo, Group, Radio,ScrollingGroup
from aiogram_dialog.widgets.text import Const, Format

from Zabbix import GetZabbix, GetHostGroups

from tinydb import Query

class DialogSG(StatesGroup):
    greeting = State()
    host_group_state = State()
    schedule = State()

class HostGroupSelectSG(StatesGroup):
    choice = State()


async def get_hostgroups_data(dialog_manager: DialogManager, **kwargs):
    await update_hostgroups_data(dialog_manager)
    await update_welcome_greeting_data(dialog_manager)
    return {
        "hostgroups": dialog_manager.dialog_data.get("hostgroups", ""),
        "greeting": dialog_manager.dialog_data.get("greeting", "Select hostgroups"),
        "welcome_greeting": dialog_manager.dialog_data.get("welcome_greeting", "")
    }

async def update_hostgroups_data(dialog_manager: DialogManager, **kwargs):
    # get host groups from zbx server
    try:
        dialog_manager.dialog_data["hostgroups"] = GetHostGroups()

        # get current settings for user
        usr_settings = get_user_settings(dialog_manager.current_context().access_settings.user_ids[0])
        if usr_settings != []:
            dialog_manager.current_context().widget_data["check"]= usr_settings[0]["host_groups"]

    except Exception as e:
        logging.error(e)

async def update_welcome_greeting_data(dialog_manager: DialogManager, **kwargs):
    if "welcome_greeting" not in dialog_manager.dialog_data.keys():
        dialog_manager.dialog_data["welcome_greeting"] = "First step - configure hostgroups to monitor and schedule"


async def on_btn_settings_click(
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager,
):
    await manager.switch_to(DialogSG.host_group_state)


async def on_btn_save_settings_click(callback: CallbackQuery, button: Button, manager: DialogManager):
    chat_id = callback.message.chat.id
    # selected = manager.current_context().widget_data["check"]

    try:
        # manager.current_context().widget_data.keys()
        selection = manager.current_context().widget_data.keys()

        if "check" in selection and "id_radio" in selection:
            selected_host_groups = manager.current_context().widget_data["check"]
            selected_schedules = manager.current_context().widget_data["id_radio"]

            # if manager.current_context().widget_data["id_radio"] == "":
            #     schedule = "3m"
            # else:
            schedule = manager.current_context().widget_data["id_radio"]  # "3m"

            last_update = str(datetime.datetime.now())

            user_exists = Query()

            if db.search(user_exists.chat_id == callback.message.chat.id) == []:
                await add_user_settings(chat_id, selected_host_groups, selected_schedules, last_update)
            else:
                await update_user_settings(chat_id, selected_host_groups, selected_schedules, last_update)

            manager.dialog_data["greeting"] = "Congrats! Setting completed!\n"
            manager.dialog_data["welcome_greeting"] = "Congrats! Setting completed!\n"
            await manager.switch_to(DialogSG.greeting)

        else:
            manager.dialog_data["greeting"] = "Please choose host_groups and schedule interval for notification\n"
            # callback.message("Please choose host_groups and schedule interval for notofication\n")
            # callback.message.answer("Please choose host_groups and schedule interval for notofication\n")
    except Exception as e:
        logging.error(f"Error on saving data to db: {e}")

#==================================================================================================
#==================================================================================================
#==================================================================================================

multi = Multiselect(
    Format("✓ {item[0]}"),  
    Format("{item[0]}"),
    id="check",
    item_id_getter=operator.itemgetter(1),
    items="hostgroups",
)

dialog = Dialog(
    Window(
        Format("{welcome_greeting}\r\n"),
        Button(Const("Settings"), id="btn_settings", on_click=on_btn_settings_click),
        Cancel(Const("Exit")),
        state=DialogSG.greeting,
        getter=get_hostgroups_data,
    ),
    Window(
        Format("{greeting}\r\n"),
        ScrollingGroup(
            multi,
            width=2,
            height=10,
            id="id_scroll",
        ),
        Const(" \r\n"),
            SwitchTo(
                Const("Back"),
                state=DialogSG.greeting, id="to_title",
            ),
            SwitchTo(
                Const("Schedule"),
                state=DialogSG.schedule, id="to_schedule",
            ),
            Button(Const("Save"), id="btn_save_settings", on_click=on_btn_save_settings_click),
        #    width=1,
        #),
        state=DialogSG.host_group_state,
        getter=get_hostgroups_data,

    ),
    Window(
        Format("Select schedule for recieving updates\r\n"),
        Const("Choose update interval \n"),
        Group(
            Radio(
                checked_text=Format("🔘 {item}"),
                unchecked_text=Format("⚪️ {item}"),
                items=["1m", "3m", "30m", "1h","Never"],
                item_id_getter=lambda x: x,
                id="id_radio",
            ),
            width=2,
        ),
        SwitchTo(
            Const("Back"),
            state=DialogSG.host_group_state, id="to_host_group_state",
        ),
        # Button(Const("Save"), id="btn_save_settings", on_click=on_btn_save_settings_click),
        state=DialogSG.schedule,
        # getter=get_hostgroups_data,
    )
)


async def start(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(DialogSG.greeting, mode=StartMode.RESET_STACK)
    # await update_hostgroups_data(dialog_manager)


async def main():

    logging.basicConfig(filename='zbxmon.log',level=logging.INFO,format= '[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s')

    storage = MemoryStorage()
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher(storage=storage)
    dp.include_router(dialog)

    # register handler which resets stack and start dialogs on /start command
    dp.message.register(start, CommandStart())
    dp.business_message.register(start, CommandStart())

    setup_dialogs(dp)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
