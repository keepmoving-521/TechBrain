import { describe, expect, it } from "vitest";
import { AxiosError, AxiosHeaders } from "axios";

import { getErrorMessage } from "@/utils/errors";

describe("getErrorMessage", () => {
  it("returns backend error message from API envelope", () => {
    const error = new AxiosError("Request failed", undefined, undefined, undefined, {
      status: 400,
      statusText: "Bad Request",
      headers: {},
      config: {
        headers: new AxiosHeaders(),
      },
      data: {
        error: {
          code: "VALIDATION_ERROR",
          message: "请求参数校验失败",
        },
        request_id: "request-id",
      },
    });

    expect(getErrorMessage(error)).toBe("请求参数校验失败");
  });

  it("returns network hint when backend is unreachable", () => {
    const error = new AxiosError("Network Error", "ERR_NETWORK");

    expect(getErrorMessage(error)).toBe("无法连接后端服务，请确认 API 服务已启动。");
  });
});
