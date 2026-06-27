import { apiPut } from "@/api/http";

export interface UpdateProfilePayload {
  nome: string;
  departamento?: string;
}

export interface UpdateProfileResponse {
  message: string;
}

export const usersApi = {
  updateProfile(token: string, payload: UpdateProfilePayload): Promise<UpdateProfileResponse> {
    return apiPut<UpdateProfileResponse>("/users/profile", payload, token);
  },
};
