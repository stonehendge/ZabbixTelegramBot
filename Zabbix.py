from pyzabbix import ZabbixAPI
from Config import (
    ZABBIX_SERVER,
    ZABBIX_API_USER,
    ZABBIX_API_PWD
)

# The hostname at which the Zabbix web interface is available
zapi = ZabbixAPI(ZABBIX_SERVER)

# Login to the Zabbix API
zapi.login(ZABBIX_API_USER, ZABBIX_API_PWD)


def GetZabbix() -> str:
    unack_triggers = zapi.trigger.get(only_true=1,
                                      skipDependent=1,
                                      monitored=1,
                                      active=1,
                                      output='extend',
                                      expandDescription=1,
                                      selectHosts=['host'],
                                      withLastEventUnacknowledged=1, group='SQL Servers'
                                      )
    unack_trigger_ids = [t['triggerid'] for t in unack_triggers]
    for t in unack_triggers:
        t['unacknowledged'] = True if t['triggerid'] in unack_trigger_ids \
            else False

    result = ""

    for t in unack_triggers:
        if int(t['value']) == 1:
            result += "{0} - {1} {2}".format(t['hosts'][0]['host'],
                                             t['description'].encode('utf-8'),
                                             '(Unack)' if t['unacknowledged'] else '') + "\n"

    return result


#print(GetZabbix())

def GetHostGroups():
    unack_triggers = zapi.hostgroup.get() #with_hosts_and_templates=1,monitored_hosts=1,with_triggers=1

    result = []
    counter = 1

    for h in unack_triggers:
        result.append((h["name"],h["groupid"])) #counter
        counter +=1
    return result
