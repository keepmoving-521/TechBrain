import axios from "axios";

interface ApiErrorEnvelope {
  error?: {
    code?: string;
    message?: string;
    details?: unknown;
  };
  request_id?: string;
}

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError<ApiErrorEnvelope>(error)) {
    const apiMessage = error.response?.data?.error?.message;
    if (apiMessage) {
      return apiMessage;
    }

    if (error.response?.status) {
      return `接口请求失败，状态码：${error.response.status}`;
    }

    if (error.code === "ERR_NETWORK") {
      return "无法连接后端服务，请确认 API 服务已启动。";
    }
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return "请求处理失败，请稍后重试。";
}
