import { request } from "@/utils/request";

export interface HealthResponse {
  status: "ok";
  service: string;
  version: string;
  environment: string;
}

export const healthApi = {
  getLive() {
    return request.get<HealthResponse>("/health/live");
  },
};
