import { onCleanup, For } from "solid-js";
import { createStore } from "solid-js/store";
import { LocalStorageWithIndex } from "./local_sync";





type Sync_row = {
  is_deleted?: boolean
}
type User = {name: string, age: number, email: string, }
const [users, setUsers] = createStore<{[key: string]: User & Sync_row}>({});



const clientId = crypto.randomUUID();
const socket = new WebSocket(`ws://localhost:8000/ws/${clientId}`);

let clientVersion = 0; // updated when receiving versioned data from backend


socket.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  console.log(msg);
  
  clientVersion = msg.version;
  // alert(`Data update from server: ${JSON.stringify(msg)}`);
  switch (msg.type) {
    case "add":
      console.log({users});
      setUsers(msg.key, msg.data);
      console.log({users});
      break;
  
    case "edit":
      setUsers((users) => {
        console.log({row_changes: msg.row_changes});
        
        for (const [key, value] of Object.entries(msg.row_changes)) {
          console.log({key, value});
          
          setUsers(msg.key, key, value);
        }
      });
      break;
  
    case "delete":
      console.log({users});
      setUsers(msg.key, undefined);
      console.log({users});
      break;
  
    default:
      break;
  }
  

  console.log({users});

};



export function addUser(name: string, age: number, email: string) {
  socket.send(JSON.stringify({
      type: "add",
      data: { name, age, email },
      key: name,
      version: clientVersion,
      clientId,
      time: new Date(),
      value: { name, age, email },
  }));
  setUsers(name, {name, age, email})
}

export function editUser(key: string, field: string, value: any) {
  socket.send(JSON.stringify({
      type: "edit",
      key,
      field,
      value,
      version: clientVersion,
      clientId,
      time: new Date(),
  }));
  setUsers(key, field as keyof User, value)
}

export function deleteUser(key: string) {
  socket.send(JSON.stringify({
      type: "delete",
      key,
      version: clientVersion,
      clientId,
      time: new Date(),
  }));
  setUsers(key, "is_deleted", true)
}


function App() {



  return (
    <div>
      <h1>User Sync</h1>
      <button onClick={() => addUser("Mendy", 30, "mendy@example.com")}>Add Mendy</button>
      <For each={Object.values(users).filter(u => !u.is_deleted)}>
        {(user: User) => (
          <div>
            <span style={{padding: "0 10px"}}>{user.name}</span>
            <span style={{padding: "0 10px"}}>{user.age}</span>
            <span style={{padding: "0 10px"}}>{user.email}</span>
            <button onClick={() => editUser(user.name, "age", user.age + 1)}>+ Age</button>
            <button onClick={() => deleteUser(user.name)}>Delete</button>
          </div>
        )}
      </For>
      <form onsubmit={(e) => {
        e.preventDefault();
        const name = (e.currentTarget as HTMLFormElement).name.value;
        const age = Number((e.currentTarget as HTMLFormElement).age.value);
        const email = (e.currentTarget as HTMLFormElement).email.value;
        addUser(name, age, email);
      }}>
        <label>Name</label>
        <input type="text" name="name" />
        <br />
        <label>Age</label>
        <input type="number" name="age" />
        <br />
        <label>Email</label>
        <input type="email" name="email" />
        <br />
        <button type="submit">Add</button>
      </form>
    </div>
  );
}


(window as any).users_store = new LocalStorageWithIndex("user")



export default App;
