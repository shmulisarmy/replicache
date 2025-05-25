import React, { useState, useEffect, useRef } from 'react';
import { Trash2, UserPlus, Plus } from 'lucide-react';

// Types
interface User {
  name: string;
  age: number;
  email: string;
}

interface SyncRow {
  is_deleted?: boolean;
}

type UserWithSync = User & SyncRow;

interface WebSocketMessage {
  type: 'add' | 'edit' | 'delete';
  key: string;
  data?: User;
  row_changes?: Record<string, any>;
  version: number;
}

// WebSocket Manager Class
class WebSocketManager {
  private socket: WebSocket | null = null;
  private clientId: string;
  private clientVersion: number = 0;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  private onMessageCallback: ((msg: WebSocketMessage) => void) | null = null;

  constructor(clientId: string) {
    this.clientId = clientId;
  }

  connect(onMessage: (msg: WebSocketMessage) => void) {
    this.onMessageCallback = onMessage;
    try {
      this.socket = new WebSocket(`ws://localhost:8000/ws/${this.clientId}`);
      
      this.socket.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
      };

      this.socket.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        this.clientVersion = msg.version;
        if (this.onMessageCallback) {
          this.onMessageCallback(msg);
        }
      };

      this.socket.onclose = () => {
        console.log('WebSocket disconnected');
        this.attemptReconnect();
      };

      this.socket.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      this.attemptReconnect();
    }
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        console.log(`Reconnection attempt ${this.reconnectAttempts}`);
        if (this.onMessageCallback) {
          this.connect(this.onMessageCallback);
        }
      }, 2000 * this.reconnectAttempts);
    }
  }

  send(message: any) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({
        ...message,
        version: this.clientVersion,
        clientId: this.clientId,
        time: new Date().toISOString()
      }));
    } else {
      console.error('WebSocket is not connected');
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }
}

// Main Component
export default function UserSyncApp() {
  const [users, setUsers] = useState<Record<string, UserWithSync>>({});
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');
  const [formData, setFormData] = useState({ name: '', age: '', email: '' });
  const wsManager = useRef<WebSocketManager | null>(null);

  useEffect(() => {
    const clientId = crypto.randomUUID();
    wsManager.current = new WebSocketManager(clientId);

    const handleMessage = (msg: WebSocketMessage) => {
      console.log('Received message:', msg);
      setConnectionStatus('connected');

      switch (msg.type) {
        case 'add':
          if (msg.data) {
            /**@ts-ignore */
            setUsers(prev => ({
              ...prev,
              [msg.key]: { ...msg.data, is_deleted: false }
            }));
          }
          break;

        case 'edit':
          if (msg.row_changes) {
            setUsers(prev => ({
              ...prev,
              [msg.key]: {
                ...prev[msg.key],
                ...msg.row_changes
              }
            }));
          }
          break;

        case 'delete':
          setUsers(prev => {
            const updated = { ...prev };
            delete updated[msg.key];
            return updated;
          });
          break;
      }
    };

    wsManager.current.connect(handleMessage);

    return () => {
      wsManager.current?.disconnect();
    };
  }, []);

  const addUser = (name: string, age: number, email: string) => {

    const userData = { name: name.trim(), age, email: email.trim() };
    
    // Optimistic update
    setUsers(prev => ({
      ...prev,
      [name]: { ...userData, is_deleted: false }
    }));

    // Send to server
    wsManager.current?.send({
      type: 'add',
      data: userData,
      key: name
    });
  };

  const editUser = (key: string, field: keyof User, value: any) => {
    // Optimistic update
    setUsers(prev => ({
      ...prev,
      [key]: {
        ...prev[key],
        [field]: value
      }
    }));

    // Send to server
    wsManager.current?.send({
      type: 'edit',
      key,
      field,
      value
    });
  };

  const deleteUser = (key: string) => {
    if (true) {
      // Optimistic update
      setUsers(prev => {
        const updated = { ...prev };
        delete updated[key];
        return updated;
      });

      // Send to server
      wsManager.current?.send({
        type: 'delete',
        key
      });
    }
  };

  const handleSubmit = () => {
    console.log("handleSubmit");
    
    const { name, age, email } = formData;

    addUser(name, parseInt(age) || 0, email);
    setFormData({ name: '', age: '', email: '' });
  };

  const activeUsers = Object.values(users).filter(user => !user.is_deleted);

  return (
    <div className="max-w-4xl mx-auto p-6 bg-white min-h-screen">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Real-time User Sync</h1>
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full ${
            connectionStatus === 'connected' ? 'bg-green-500' : 
            connectionStatus === 'connecting' ? 'bg-yellow-500' : 'bg-red-500'
          }`} />
          <span className="text-sm text-gray-600 capitalize">{connectionStatus}</span>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="mb-6">
        <button
          onClick={() => addUser("Mendy", 30, "mendy@example.com")}
          className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors"
        >
          <UserPlus size={16} />
          Add Mendy (Quick Test)
        </button>
      </div>

      {/* User List */}
      <div className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Users ({activeUsers.length})</h2>
        {activeUsers.length === 0 ? (
          <div className="text-gray-500 text-center py-8">
            No users yet. Add some users below!
          </div>
        ) : (
          <div className="space-y-2">
            {activeUsers.map((user) => (
              <div
                key={user.name}
                className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <div className="flex items-center gap-6">
                  <div className="font-medium text-gray-900">{user.name}</div>
                  <div className="text-gray-600">Age: {user.age}</div>
                  <div className="text-gray-600">{user.email}</div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => editUser(user.name, 'age', user.age + 1)}
                    className="bg-green-500 hover:bg-green-600 text-white px-3 py-1 rounded text-sm flex items-center gap-1 transition-colors"
                  >
                    <Plus size={12} />
                    Age
                  </button>
                  <button
                    onClick={() => deleteUser(user.name)}
                    className="bg-red-500 hover:bg-red-600 text-white px-3 py-1 rounded text-sm flex items-center gap-1 transition-colors"
                  >
                    <Trash2 size={12} />
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add User Form */}
      <form onSubmit={e => {e.preventDefault()

        handleSubmit();
      }}>
      <div className="bg-gray-50 p-6 rounded-lg">
        <h2 className="text-xl font-semibold mb-4">Add New User</h2>
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Name
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter name"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Age
              </label>
              <input
                type="number"
                value={formData.age}
                onChange={(e) => setFormData(prev => ({ ...prev, age: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter age"
                min="0"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email
              </label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter email"
              />
            </div>
          </div>
          <button
            type='submit'
            className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg font-medium transition-colors"
          >
            Add User
          </button>
        </div>
      </div>
      </form>

      {/* Debug Info */}
      <div className="mt-8 p-4 bg-gray-100 rounded-lg">
        <details>
          <summary className="cursor-pointer font-medium text-gray-700">
            Debug Information
          </summary>
          <pre className="mt-2 text-xs text-gray-600 overflow-auto">
            {JSON.stringify({ users, connectionStatus }, null, 2)}
          </pre>
        </details>
      </div>
    </div>
  );
}