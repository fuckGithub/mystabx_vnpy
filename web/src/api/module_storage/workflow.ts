import request from '@utils/http'

/** 对应后端 `plugin.module_storage.workflow` */
const API_PATH = '/storage/workflow'

const StorageWorkflowAPI = {
  getWorkflowList(query: StorageWorkflowPageQuery) {
    return request<ApiResponse<PageResult<StorageWorkflowTable>>>({
      url: `${API_PATH}/list`,
      method: 'get',
      params: query,
    })
  },

  getWorkflowDetail(id: number) {
    return request<ApiResponse<StorageWorkflowTable>>({
      url: `${API_PATH}/detail/${id}`,
      method: 'get',
    })
  },

  createWorkflow(body: StorageWorkflowForm) {
    return request<ApiResponse<StorageWorkflowTable>>({
      url: `${API_PATH}/create`,
      method: 'post',
      data: body,
    })
  },

  updateWorkflow(id: number, body: StorageWorkflowForm) {
    return request<ApiResponse<StorageWorkflowTable>>({
      url: `${API_PATH}/update/${id}`,
      method: 'put',
      data: body,
    })
  },

  deleteWorkflow(body: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/delete`,
      method: 'delete',
      data: body,
    })
  },
}

export default StorageWorkflowAPI
export { StorageWorkflowAPI }

export interface StorageWorkflowPageQuery extends PageQuery {
  name?: string
  code?: string
  status?: string
  created_time?: string[]
  updated_time?: string[]
  created_id?: number
  updated_id?: number
}

export interface StorageWorkflowTable extends BaseType {
  name?: string
  code?: string
  description?: string
  nodes_json?: string
  edges_json?: string
  status?: string
}

export interface StorageWorkflowForm extends BaseFormType {
  name?: string
  code?: string
  description?: string
  nodes_json?: string
  edges_json?: string
}
