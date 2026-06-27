/**
 * API client for program configurations and vehicle levels.
 */

import { API_URL } from "@/api/authApi";

const API_BASE_URL = `${API_URL}/api/v1`;

export interface Program {
  id: string;
  nome?: string;
  [key: string]: unknown;
}

export const programsApi = {
  getPrograms: async (token: string): Promise<Program[]> => {
    const response = await fetch(`${API_BASE_URL}/programs`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (!response.ok) throw new Error('Failed to fetch programs');
    return response.json();
  },

  getProgramConfig: async (token: string) => {
    const response = await fetch(`${API_BASE_URL}/programs/config`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    
    if (response.status === 404) return null;
    
    if (!response.ok) throw new Error('Failed to fetch program config');
    return response.json();
  },

  updateProgramConfig: async (token: string, data: any) => {
    const response = await fetch(`${API_BASE_URL}/programs/config`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('Failed to update program config');
    return response.json();
  },

  updateVehicleLevel: async (token: string, vehicleId: string, data: { nivel: string, peso: number }) => {
    const response = await fetch(`${API_BASE_URL}/vehicle-levels/${vehicleId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('Failed to update vehicle level');
    return response.json();
  },

  getVehicleLevels: async (token: string) => {
    const response = await fetch(`${API_BASE_URL}/vehicle-levels`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to fetch vehicle levels');
    return response.json();
  }
};
