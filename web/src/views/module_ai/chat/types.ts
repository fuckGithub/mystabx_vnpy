// 聊天消息类型
export interface ChatMessage {
  id: string
  type: 'user' | 'assistant'
  content: string
  timestamp: number
  loading?: boolean
  collapsed?: boolean
  /** 思考/推理过程内容（与回答区分展示） */
  reasoning?: string
  reasoningCollapsed?: boolean
  files?: UploadedFile[]
}

// 上传文件类型
export interface UploadedFile {
  id: string
  name: string
  size: number
  type: string
  url?: string
  file?: File
}

// 会话消息类型（来自后端）
export interface SessionMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_time?: string
}

// 会话详情类型
export interface SessionDetail {
  id: string
  title: string
  created_time?: string
  updated_time?: string
  message_count: number
  messages: SessionMessage[]
}
