import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit'
import axios from 'axios'

interface Task {
  id: string
  title: string
  status: 'pending' | 'claimed' | 'done'
  bounty: { amount: number; token: string }
}

interface TasksState {
  items: Task[]
  status: 'idle' | 'loading' | 'succeeded' | 'failed'
}

const initialState: TasksState = {
  items: [],
  status: 'idle',
}

export const fetchTasks = createAsyncThunk('tasks/fetchTasks', async () => {
  // In dev, we might mock this or proxy to backend
  // For now, return mock data to prove UI
  return [
    { id: '1', title: 'Verify Tweet 492', status: 'pending', bounty: { amount: 10, token: 'MIND' } },
    { id: '2', title: 'Audit Auth Module', status: 'pending', bounty: { amount: 50, token: 'MIND' } },
    { id: '3', title: 'Design Logo', status: 'claimed', bounty: { amount: 100, token: 'MIND' } },
  ]
})

const tasksSlice = createSlice({
  name: 'tasks',
  initialState,
  reducers: {
    addTask(state, action: PayloadAction<Task>) {
      state.items.unshift(action.payload)
    },
    removeTask(state, action: PayloadAction<string>) {
      state.items = state.items.filter(t => t.id !== action.payload)
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchTasks.pending, (state) => {
        state.status = 'loading'
      })
      .addCase(fetchTasks.fulfilled, (state, action) => {
        state.status = 'succeeded'
        state.items = action.payload
      })
  },
})

export const { addTask, removeTask } = tasksSlice.actions
export default tasksSlice.reducer