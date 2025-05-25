// // src/lib/ws.ts
// const clientId = crypto.randomUUID();
// const socket = new WebSocket(`ws://localhost:8000/ws/${clientId}`);

// let clientVersion = 0; // updated when receiving versioned data from backend

// socket.onmessage = (event) => {
//     const msg = JSON.parse(event.data);
//     if (msg.type === "data-change") {
//         // Full user list received
//         clientVersion = msg.version;
//         console.log("Data update from server:", msg.users);
//     } else if (msg.type === "conflict") {
//         console.warn("Conflict detected:", msg);
//     }
// };

// export { socket, clientId, clientVersion };
