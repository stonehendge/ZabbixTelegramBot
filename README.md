# ZabbixTelegramBot
Moitor zabbix problems in TG Bot


Steps for running bot in docker:

1) Edit Config.py. Change parameters for access zabbix server and Bot Token (create bot as usual with BotFather)
2) docker build . -t zbxmon:1.0
3) docker run --name zbxmonbot -itd zbxmon:1.0
4) docker cp __init__.py ContainerID:/usr/local/lib/python3.12/site-packages/aioschedule/__init__.py
5) docker stop ContainerID && docker start ContainerID
