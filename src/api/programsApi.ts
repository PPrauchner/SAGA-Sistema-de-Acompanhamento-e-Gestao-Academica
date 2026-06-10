/**
 * API client for program configurations and vehicle levels.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

async function getAuthHeader() {
  // This should ideally come from a central auth state/hook
  // For now, we'll try to get it from a place where it's stored or just return a placeholder
  // In a real implementation, we'd use useAuth() hook, but outside components we might need another way.
  return { 'Authorization': `Bearer ${localStorage.getItem('token')}` };
}

export const programsApi = {
  getProgramConfig: async () => {
    const response = await fetch(`${API_BASE_URL}/programs/config`, {
      headers: await getAuthHeader()
    });
    if (!response.ok) throw new Error('Failed to fetch program config');
    return response.json();
  },

  updateProgramConfig: async (data: any) => {
    const response = await fetch(`${API_BASE_URL}/programs/config`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...(await getAuthHeader())
      },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('Failed to update program config');
    return response.json();
  },

  updateVehicleLevel: async (vehicleId: string, data: { nivel: string, peso: number }) => {
    const response = await fetch(`${API_BASE_URL}/vehicle-levels/${vehicleId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...(await getAuthHeader())
      },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('Failed to update vehicle level');
    return response.json();
  }
};
