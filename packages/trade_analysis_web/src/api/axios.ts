import axios, { type AxiosInstance, type AxiosRequestConfig,type InternalAxiosRequestConfig,type AxiosResponse, AxiosError } from "axios";
import { type ResultData } from "./interface";

export interface CustomAxiosRequestConfig extends InternalAxiosRequestConfig {
  loading?: boolean;
  cancel?: boolean;
}

const apiBaseUrl = (import.meta.env.VITE_API_URL || "/api/v1").replace(/\/$/, "");

const config = {
  // 默认地址请求地址，可在 .env.** 文件中修改
  baseURL: apiBaseUrl,
  // 跨域时候允许携带凭证
  withCredentials: true
};

class AxiosClient {
  service: AxiosInstance;
  public constructor(config: AxiosRequestConfig) {
    this.service = axios.create(config);
    this.service.interceptors.response.use(
      (response: AxiosResponse & { config: CustomAxiosRequestConfig}) => {
        const { data } = response;
        if (data.code && data.code !== 200) {
          return Promise.reject(data);
        }
        return data;
      },
      async (error: AxiosError) => {
        const { response } = error;
        return Promise.reject(response);
      }
    )
  }
  get<T>(url: string, params?: object, _object = {}): Promise<ResultData<T>> {
    return this.service.get(url, { params, ..._object });
  }
  post<T>(url: string, params?: object | string, _object = {}): Promise<ResultData<T>> {
    return this.service.post(url, params, _object);
  }
  put<T>(url: string, params?: object, _object = {}): Promise<ResultData<T>> {
    return this.service.put(url, params, _object);
  }
  delete<T>(url: string, params?: any, _object = {}): Promise<ResultData<T>> {
    return this.service.delete(url, { params, ..._object });
  }
  download(url: string, params?: object, _object = {}): Promise<BlobPart> {
    return this.service.post(url, params, { ..._object, responseType: "blob" });
  }
}

export default new AxiosClient(config);
