import asyncio
import queue
from dataclasses import dataclass
from action import Action, ActionType, EditAction, DeleteAction
from client import Client
from typing import List
from copy import deepcopy
from collections import defaultdict
import uuid
from mutations_mutex import mutations_mutex_locked


def find_client(clients: list[Client], client_id: uuid.UUID) -> Client:
    for client in clients:
        if client.id == client_id:
            return client

    raise Exception("Client not found")


@dataclass
class Db[T]:
    data_version: int
    data: dict[str, T]
    id_upto: int
    settings: str
    def __init__(self, data: list[T]):
        self.data_version = 1
        self.data = {}
        self.id_upto = 0
        self.settings = "apply latest" # other options: "apply col", "apply by row"

        for item in data:
            self.id_upto += 1
            self.data[item.name] = {"id": self.id_upto, "data": item}
    

    @staticmethod
    def group_changes_by_key(actions: List[Action], key: str) -> dict:
        changes = defaultdict(list)
        for action in actions:
            match action.type:
                    case ActionType.APPEND:
                        action: AppendAction
                        keyValue = action.key
                       
                    case ActionType.DELETE:
                        action: DeleteAction
                        keyValue = action.key
                       
                    case ActionType.EDIT:
                        keyValue = action.key
            # action.client_id = client.id
            changes[keyValue].append(action)
        return changes


    async def handle_mutations(self, all_actions: List[Action], key: str, logger: list, clients: list[uuid.UUID]) -> dict[uuid.UUID, list]:
        print(f'in handle_mutations: {all_actions = }')


        if not all_actions:
            return {client: [] for client in clients}
        
        global mutations_mutex_locked
        while mutations_mutex_locked:
            await asyncio.sleep(0.1)
            continue
        mutations_mutex_locked = True

        messages: dict[uuid.UUID, list] = defaultdict(list)
        for row_key, row_changes in Db.group_changes_by_key(all_actions, key).items():
            for change in sorted(filter(lambda change: change.type == ActionType.APPEND, row_changes), key=lambda change: [-change.version, change.time], reverse=True):
                print(f'{change = }')
                
                change: AppendAction
                self.data[row_key] = deepcopy({"id": row_key, "data": change.data})
                self.id_upto += 1
        
                for client_id in clients:
                    messages[client_id].append({"type": "add", "key": row_key, "data": change.data, "version": self.data_version})
                

            if any(change.type == ActionType.DELETE for change in row_changes):
                if any(change.type == ActionType.EDIT for change in row_changes):
                    messages[change.client_id].append({"type": "conflict", "message": f"another user has recently made a change, {change.description}, do you still want to delete it"})
                else:
                    del self.data[row_key]

                    for client_id in clients:
                        messages[client_id].append({"type": "delete", "key": row_key, "version": self.data_version})
                logger.append({"type": "delete", "key": row_key, "version": self.data_version})


            if not any(change.type == ActionType.EDIT for change in row_changes):
                continue
            assert self.data[row_key], "you cannot edit a row that does not exist"
            edit_changes_iterator = filter(lambda change: change.type == ActionType.EDIT, row_changes)
            if self.settings == "apply latest": # not handling other cases now
                change_dict = {}
                for change in sorted(edit_changes_iterator, key=lambda change: change.version):
                    change: EditAction
                    change_dict[change.field] = change.value
                
                this_row = self.data[row_key]['data']
                
                for key, value in change_dict.items():
                    this_row[key] = value

                for client_id in clients:
                    messages[client_id].append({"type": "edit", "key": row_key, "row_changes": change_dict, "version": self.data_version})
                logger.append({"type": "edit", "key": row_key, "row_changes": change_dict, "version": self.data_version})

        mutations_mutex_locked = False

        self.data_version += 1
        for client_id in clients:
            for message in messages[client_id]:
                message["version"] = self.data_version
                
        return messages
