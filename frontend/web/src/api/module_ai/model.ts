import request from '@utils/http'

const API_PATH = '/ai/model'

/** 模型列表查询参数（分页/列表通用） */
export interface AiModelQuery extends PageQuery {
  provider_id?: number
  model_key?: string
  name?: string
  status?: string
}

/** 模型响应模型（含所属供应商摘要信息） */
export interface AiModel {
  id: number
  provider_id: number
  model_key: string
  name: string
  url: string | null
  tool_calling: boolean | null
  vision: boolean | null
  max_input_tokens: number | null
  max_output_tokens: number | null
  thinking: boolean | null
  temperature: number | null
  is_default: boolean | null
  sort_order: number | null
  status?: string
  description?: string
  provider_name?: string | null
  vendor?: string | null
  api_type?: string | null
  created_time?: string
  updated_time?: string
}

/** 模型下拉列表条目（不暴露密钥） */
export interface AiModelOption {
  id: number
  provider_id: number
  provider_name: string | null
  vendor: string | null
  api_type: string | null
  model_key: string
  name: string
  thinking: boolean | null
  tool_calling: boolean | null
  vision: boolean | null
  is_default: boolean | null
}

/** 模型创建/更新载荷 */
export interface AiModelPayload {
  provider_id: number
  model_key: string
  name: string
  url?: string | null
  tool_calling?: boolean
  vision?: boolean
  max_input_tokens?: number
  max_output_tokens?: number
  thinking?: boolean
  temperature?: number
  is_default?: boolean
  sort_order?: number
  description?: string
}

export const AiModelAPI = {
  /** 模型详情（含所属供应商信息） */
  getDetail(id: number) {
    return request<ApiResponse<AiModel>>({
      url: `${API_PATH}/detail/${id}`,
      method: 'get',
    })
  },

  /** 模型列表 */
  getList(query: Partial<AiModelQuery> = {}) {
    return request<ApiResponse<AiModel[]>>({
      url: `${API_PATH}/list`,
      method: 'get',
      params: query,
    })
  },

  /** 模型分页 */
  getPage(query: AiModelQuery) {
    return request<ApiResponse<PageResult<AiModel>>>({
      url: `${API_PATH}/page`,
      method: 'get',
      params: query,
    })
  },

  /** 按供应商查启用模型（前端分类下拉） */
  getByProvider(providerId: number) {
    return request<ApiResponse<AiModelOption[]>>({
      url: `${API_PATH}/by-provider/${providerId}`,
      method: 'get',
    })
  },

  /** 新建模型 */
  create(body: AiModelPayload) {
    return request<ApiResponse<AiModel>>({
      url: `${API_PATH}/create`,
      method: 'post',
      data: body,
    })
  },

  /** 更新模型 */
  update(id: number, body: AiModelPayload) {
    return request<ApiResponse<AiModel>>({
      url: `${API_PATH}/update/${id}`,
      method: 'put',
      data: body,
    })
  },

  /** 删除模型（批量） */
  delete(ids: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/delete`,
      method: 'delete',
      data: ids,
    })
  },

  /** 设置默认模型 */
  setDefault(id: number) {
    return request<ApiResponse>({
      url: `${API_PATH}/set-default/${id}`,
      method: 'put',
    })
  },
}

export default AiModelAPI
