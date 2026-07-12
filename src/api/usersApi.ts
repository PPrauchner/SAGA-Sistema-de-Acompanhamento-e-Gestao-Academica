import { apiPut } from "@/api/http";
import type { NotificationPreferences } from "@/app/context/AppContext";

export interface UpdateProfilePayload {
  nome?: string;
  notification_preferences?: NotificationPreferences;
}

export interface UpdateProfileResponse {
  uid: string;
  nome: string;
  notification_preferences: NotificationPreferences;
}

export const usersApi = {
  updateProfile(token: string, payload: UpdateProfilePayload): Promise<UpdateProfileResponse> {
    return apiPut<UpdateProfileResponse>("/users/profile", payload, token);
  },
};
