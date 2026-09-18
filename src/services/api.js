const request = async (path, options = {}) => {
  let response;
  try {
    response = await fetch(`/api${path}`, {
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
  } catch {
    throw new Error('Unable to reach the server. Please check your connection and try again.');
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.message || payload.error || 'The request could not be completed.');
  return payload;
};

export const api = {
  login: (email, password, remember) => request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password, remember }) }),
  logout: () => request('/auth/logout', { method: 'POST' }),
  me: () => request('/auth/me'),
  students: () => request('/students'),
  student: (id) => request(`/students/${encodeURIComponent(id)}`),
  addStudent: (body) => request('/students', { method: 'POST', body: JSON.stringify(body) }),
  updateStudent: (id, body) => request(`/students/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(body) }),
  prediction: (id) => request(`/students/${encodeURIComponent(id)}/prediction`),
  risk: (id) => request(`/students/${encodeURIComponent(id)}/risk`),
  explain: (id) => request(`/students/${encodeURIComponent(id)}/explain`),
  predict: (body) => request('/predict', { method: 'POST', body: JSON.stringify(body) }),
  interventions: () => request('/interventions'),
  addIntervention: (body) => request('/interventions', { method: 'POST', body: JSON.stringify(body) }),
  updateIntervention: (id, body) => request(`/interventions/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(body) }),
  whatIf: (body) => request('/what-if', { method: 'POST', body: JSON.stringify(body) }),
  analytics: () => request('/analytics/overview'),
};
