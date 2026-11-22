import axios from 'axios';

// Resolve backend base URL from environment variable or fallback to local default
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Helper for standardized error messages
const getErrorMessage = (error, defaultMsg) => {
  if (error.response?.data?.detail) {
    if (Array.isArray(error.response.data.detail)) {
      return error.response.data.detail[0]?.msg || defaultMsg;
    }
    return String(error.response.data.detail);
  }
  if (error.response?.data?.error) {
    return String(error.response.data.error);
  }
  if (error.code === 'ECONNABORTED') {
    return 'Request timed out. Please check if the backend is running.';
  }
  if (!error.response) {
    return 'Network error. Unable to connect to NitiSetu backend on port 8000.';
  }
  return defaultMsg;
};

// ----------------- HEALTH & SYSTEM -----------------

export const checkBackendHealth = async () => {
  try {
    const response = await apiClient.get('/api/v1/health');
    return { success: true, data: response.data, error: null };
  } catch (error) {
    return { success: false, data: null, error: getErrorMessage(error, 'Backend service is currently unreachable.') };
  }
};

export const sendTestChatMessage = async (message) => {
  try {
    const trimmed = (message || '').trim();
    if (!trimmed) {
      return { success: false, data: null, error: 'Please enter a message before sending.' };
    }
    const response = await apiClient.post('/api/v1/chat/test', { message: trimmed });
    return { success: true, data: response.data, error: null };
  } catch (error) {
    return { success: false, data: null, error: getErrorMessage(error, 'Failed to communicate with chat test endpoint.') };
  }
};

// ----------------- SOURCE A: LAWS (NYAYKOSH) -----------------

export const searchLaws = async (query) => {
  try {
    const trimmed = (query || '').trim();
    if (!trimmed) {
      return { success: false, data: null, error: 'Please enter a search term for legal statutes.' };
    }
    const response = await apiClient.get('/api/v1/laws/search', { params: { q: trimmed } });
    return { success: true, data: response.data, error: null };
  } catch (error) {
    return { success: false, data: null, error: getErrorMessage(error, 'Failed to retrieve legal statutory provisions.') };
  }
};

// ----------------- SOURCE B: WELFARE SCHEMES -----------------

export const getAllSchemes = async () => {
  try {
    const response = await apiClient.get('/api/v1/schemes');
    return { success: true, data: response.data, error: null };
  } catch (error) {
    return { success: false, data: null, error: getErrorMessage(error, 'Failed to fetch welfare schemes list.') };
  }
};

export const getSchemeById = async (schemeId) => {
  try {
    const response = await apiClient.get(`/api/v1/schemes/${schemeId}`);
    return { success: true, data: response.data, error: null };
  } catch (error) {
    return { success: false, data: null, error: getErrorMessage(error, `Failed to load scheme '${schemeId}'.`) };
  }
};

export const searchSchemes = async (query) => {
  try {
    const trimmed = (query || '').trim();
    if (!trimmed) return getAllSchemes();
    const response = await apiClient.get('/api/v1/schemes/search', { params: { q: trimmed } });
    return { success: true, data: response.data, error: null };
  } catch (error) {
    return { success: false, data: null, error: getErrorMessage(error, 'Failed to search schemes.') };
  }
};

export const getSchemeEligibilityQuestions = async (schemeId) => {
  try {
    const response = await apiClient.get(`/api/v1/schemes/${schemeId}/eligibility/questions`);
    return { success: true, data: response.data, error: null };
  } catch (error) {
    return { success: false, data: null, error: getErrorMessage(error, 'Failed to load eligibility questionnaire.') };
  }
};

export const evaluateSchemeEligibility = async (schemeId, applicantData) => {
  try {
    const response = await apiClient.post(`/api/v1/schemes/${schemeId}/eligibility/evaluate`, {
      applicant_data: applicantData,
    });
    return { success: true, data: response.data, error: null };
  } catch (error) {
    return { success: false, data: null, error: getErrorMessage(error, 'Failed to evaluate scheme eligibility.') };
  }
};

// ----------------- SOURCE C: DOCUMENT INTELLIGENCE (PDF) -----------------

export const uploadDocument = async (file, ownerId = 'anonymous_dev') => {
  try {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post('/api/v1/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
        'x-user-id': ownerId,
      },
    });
    return { success: true, data: response.data, error: null };
  } catch (error) {
    return { success: false, data: null, error: getErrorMessage(error, 'Document upload and text extraction failed.') };
  }
};

export const getDocumentMetadata = async (documentId) => {
  try {
    const response = await apiClient.get(`/api/v1/documents/${documentId}`);
    return { success: true, data: response.data, error: null };
  } catch (error) {
    return { success: false, data: null, error: getErrorMessage(error, 'Failed to retrieve document metadata.') };
  }
};

export const getDocumentPages = async (documentId) => {
  try {
    const response = await apiClient.get(`/api/v1/documents/${documentId}/pages`);
    return { success: true, data: response.data, error: null };
  } catch (error) {
    return { success: false, data: null, error: getErrorMessage(error, 'Failed to retrieve document pages.') };
  }
};

export const deleteDocument = async (documentId, ownerId = 'anonymous_dev') => {
  try {
    const response = await apiClient.delete(`/api/v1/documents/${documentId}`, {
      headers: { 'x-user-id': ownerId },
    });
    return { success: true, data: response.data, error: null };
  } catch (error) {
    return { success: false, data: null, error: getErrorMessage(error, 'Failed to delete document.') };
  }
};

export default apiClient;
