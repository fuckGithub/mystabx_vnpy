import request from '@utils/http'

const API_PATH = '/ai/provider'

/** 供应商列表查询参数（分页/列表通用） */
export interface AiProviderQuery extends PageQuery {
  name?: string
  vendor?: string
  api_type?: string
  status?: string
}

/** 供应商响应模型 */
export interface AiProvider {
  id: number
  name: string
  vendor: string
  api_type: string
  api_key: string | null
  base_url: string | null
  is_default: boolean | null
  sort_order: number | null
  status?: string
  description?: string
  created_time?: string
  updated_time?: string
}

/** 供应商详情（含嵌套模型列表） */
export interface AiProviderDetail extends AiProvider {
  models: AiModelItem[] | null
}

/** 供应商内模型条目 */
export interface AiModelItem {
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
}

/** 供应商创建/更新载荷 */
export interface AiProviderPayload {
  name: string
  vendor: string
  api_type: string
  api_key?: string | null
  base_url?: string | null
  is_default?: boolean
  sort_order?: number
  description?: string
}

export const AiProviderAPI = {
  /** 供应商详情（含嵌套模型） */
  getDetail(id: number) {
    return request<ApiResponse<AiProviderDetail>>({
      url: `${API_PATH}/detail/${id}`,
      method: 'get',
    })
  },

  /** 供应商列表 */
  getList(query: Partial<AiProviderQuery> = {}) {
    return request<ApiResponse<AiProvider[]>>({
      url: `${API_PATH}/list`,
      method: 'get',
      params: query,
    })
  },

  /** 供应商分页 */
  getPage(query: AiProviderQuery) {
    return request<ApiResponse<PageResult<AiProvider>>>({
      url: `${API_PATH}/page`,
      method: 'get',
      params: query,
    })
  },

  /** 新建供应商 */
  create(body: AiProviderPayload) {
    return request<ApiResponse<AiProviderDetail>>({
      url: `${API_PATH}/create`,
      method: 'post',
      data: body,
    })
  },

  /** 更新供应商 */
  update(id: number, body: AiProviderPayload) {
    return request<ApiResponse<AiProvider>>({
      url: `${API_PATH}/update/${id}`,
      method: 'put',
      data: body,
    })
  },

  /** 删除供应商（批量，级联删除其下模型） */
  delete(ids: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/delete`,
      method: 'delete',
      data: ids,
    })
  },

  /** 设置默认供应商 */
  setDefault(id: number) {
    return request<ApiResponse>({
      url: `${API_PATH}/set-default/${id}`,
      method: 'put',
    })
  },

  /** 测试供应商连通性 */
  testConnectivity(body: AiProviderPayload & { model_key: string }) {
    return request<ApiResponse<{ success: boolean; latency_ms: number | null; error: string | null }>>({
      url: `${API_PATH}/test-connectivity`,
      method: 'post',
      data: body,
    })
  },
}

export default AiProviderAPI
