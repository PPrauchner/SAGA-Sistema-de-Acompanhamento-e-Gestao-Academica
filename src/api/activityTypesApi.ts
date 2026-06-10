/**
 * API client for creditable activity types.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

async function getAuthHeader() {
  return { 'Authorization': `Bearer ${localStorage.getItem('token')}` };
}

export const activityTypesApi = {
  getActivityTypes: async () => {
    const response = await fetch(`${API_BASE_URL}/activity-types`, {
      headers: await getAuthHeader()
    });
    if (!response.ok) throw new Error('Failed to fetch activity types');
    return response.json();
  },

  createActivityType: async (data: any) => {
    const response = await fetch(`${API_BASE_URL}/activity-types`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(await getAuthHeader())
      },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('Failed to create activity type');
    return response.json();
  },

  updateActivityType: async (id: string, data: any) => {
    const response = await fetch(`${API_BASE_URL}/activity-types/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...(await getAuthHeader())
      },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('Failed to update activity type');
    return response.json();
  },

  toggleActivityType: async (id: string) => {
    const response = await fetch(`${API_BASE_URL}/activity-types/${id}/toggle`, {
      method: 'PATCH',
      headers: await getAuthHeader()
    });
    if (!response.ok) throw new Error('Failed to toggle activity type');
    return response.json();
  }
};
