import request from '@utils/http'

/** 对应后端 `plugin.module_storage.node` */
const API_PATH = '/storage/node'

const StorageNodeAPI = {
  getNodeList(query: StorageNodePageQuery) {
    return request<ApiResponse<PageResult<StorageNodeTable>>>({
      url: `${API_PATH}/list`,
      method: 'get',
      params: query,
    })
  },

  getNodeDetail(id: number) {
    return request<ApiResponse<StorageNodeTable>>({
      url: `${API_PATH}/detail/${id}`,
      method: 'get',
    })
  },

  createNode(body: StorageNodeForm) {
    return request<ApiResponse<StorageNodeTable>>({
      url: `${API_PATH}/create`,
      method: 'post',
      data: body,
    })
  },

  updateNode(id: number, body: StorageNodeForm) {
    return request<ApiResponse<StorageNodeTable>>({
      url: `${API_PATH}/update/${id}`,
      method: 'put',
      data: body,
    })
  },

  deleteNode(body: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/delete`,
      method: 'delete',
      data: body,
    })
  },
}

export default StorageNodeAPI
export { StorageNodeAPI }

export interface StorageNodePageQuery extends PageQuery {
  name?: string
  type?: string
  status?: string
  created_time?: string[]
  updated_time?: string[]
  created_id?: number
  updated_id?: number
}

export interface StorageNodeTable extends BaseType {
  name?: string
  type?: string
  config?: string
  description?: string
  status?: string
}

export interface StorageNodeForm extends BaseFormType {
  name?: string
  type?: string
  config?: string
  description?: string
}
