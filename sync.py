from typing import List
from collections import defaultdict
import uuid
from models.user import User
from models.action import Action, ActionType
from client import Client









            

#     for client in clients:
#         if client.id == action.client_id:
#             client.messages.append({"type": "data-synced", "action": action})
#             continue
#         for action in changes[key]:
#             action_is_a_conflict = False
#             for change in changes[key][::-1]:
#                 if change.client_id == client.id:
#                     client.messages.append({"type": "conflict", "action": action, "your_action": change})
#                     action_is_a_conflict = True
#                     break
#             if not action_is_a_conflict:
#                 client.messages.append({"type": "data-change", "action": action})
#     return changes

# def apply_changes(base_data: List[User], changes_by_name: dict) -> None:
#     for catogorizing_key, actions in changes_by_name.items():
#         if len(actions) == 1:
#             base_data.append(actions[0].data)
#         else:
#             # todo notify the user that their edit was not applied
#             newest_action = max(actions, key=lambda a: (a.version, a.time))
#             base_data.append(newest_action.data)

# def sync_clients(base_data: List[User], clients: dict[uuid.UUID, Client]) -> None:
#     """Synchronize all clients' changes with the base data."""
#     catogorized_changes = collect_changes_by_key(clients, lambda user: user.name)
#     apply_changes(base_data, catogorized_changes) 