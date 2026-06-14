/**
 * API client for creditable activity types.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const activityTypesApi = {
  getActivityTypes: async (token: string) => {
    const response = await fetch(`${API_BASE_URL}/activity-types`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to fetch activity types');
    return response.json();
  },

  createActivityType: async (token: string, data: any) => {
    const response = await fetch(`${API_BASE_URL}/activity-types`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('Failed to create activity type');
    return response.json();
  },

  updateActivityType: async (token: string, id: string, data: any) => {
    const response = await fetch(`${API_BASE_URL}/activity-types/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('Failed to update activity type');
    return response.json();
  },

  toggleActivityType: async (token: string, id: string) => {
    const response = await fetch(`${API_BASE_URL}/activity-types/${id}/toggle`, {
      method: 'PATCH',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to toggle activity type');
    return response.json();
  }
};
