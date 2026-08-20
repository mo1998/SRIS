import axios from 'axios'

const API_URL = '/api'

export const api = {
  // Authentication
  auth: {
    forgotPassword: (email: string) => axios.post(`${API_URL}/auth/forgot-password`, { email }),
    resetPassword: (token: string, new_password: string) => axios.post(`${API_URL}/auth/reset-password`, { token, new_password }),
  },

  // Users and organization
  users: {
    updateMe: (data: { full_name?: string; phone?: string }) => axios.patch(`${API_URL}/users/me`, data),
    changePassword: (data: { current_password: string; new_password: string }) => axios.post(`${API_URL}/users/me/password`, data),
    getMyOrganization: () => axios.get(`${API_URL}/users/me/organization`),
    getMyMemberships: () => axios.get(`${API_URL}/users/me/memberships`),
    getOrganizationMembers: () => axios.get(`${API_URL}/users/me/organization/members`),
    addMembership: (data: { email: string; role: string }) => axios.post(`${API_URL}/users/me/memberships`, data),
    getOrganizationProviders: () => axios.get(`${API_URL}/users/me/organization/providers`),
    updateOrganizationSettings: (data: {
      evaluation_provider?: string | null
      evaluation_model?: string | null
      evaluation_base_url?: string | null
      evaluation_api_key?: string | null
    }) => axios.patch(`${API_URL}/users/me/organization/settings`, data),
    listProviderPresets: () => axios.get(`${API_URL}/users/me/organization/presets`),
    createProviderPreset: (data: {
      name: string
      provider: string
      model?: string | null
      base_url?: string | null
      api_key?: string | null
    }) => axios.post(`${API_URL}/users/me/organization/presets`, data),
    applyProviderPreset: (id: number) => axios.post(`${API_URL}/users/me/organization/presets/${id}/apply`),
    deleteProviderPreset: (id: number) => axios.delete(`${API_URL}/users/me/organization/presets/${id}`),
  },

  // Interviews
  interviews: {
    create: (data: any) => axios.post(`${API_URL}/interviews/`, data),
    listTemplates: () => axios.get(`${API_URL}/interviews/templates`),
    getTemplate: (id: number) => axios.get(`${API_URL}/interviews/templates/${id}`),
    createFromTemplate: (id: number, data: any) => axios.post(`${API_URL}/interviews/templates/${id}/interviews`, data),
    list: () => axios.get(`${API_URL}/interviews/`),
    get: (id: number) => axios.get(`${API_URL}/interviews/${id}`),
    update: (id: number, data: any) => axios.put(`${API_URL}/interviews/${id}`, data),
    activate: (id: number) => axios.post(`${API_URL}/interviews/${id}/activate`),
    complete: (id: number) => axios.post(`${API_URL}/interviews/${id}/complete`),
    delete: (id: number) => axios.delete(`${API_URL}/interviews/${id}`),
    getQuestions: (id: number) => axios.get(`${API_URL}/interviews/${id}/questions`),
    addQuestion: (id: number, data: any) => axios.post(`${API_URL}/interviews/${id}/questions`, data),
    listQuestionBank: () => axios.get(`${API_URL}/interviews/question-bank`),
    saveQuestionToBank: (data: any) => axios.post(`${API_URL}/interviews/question-bank`, data),
    deleteQuestionBankEntry: (id: number) => axios.delete(`${API_URL}/interviews/question-bank/${id}`),
    runMaintenance: () => axios.post(`${API_URL}/maintenance/run`)
  },
  
  // Invitations
  invitations: {
    create: (data: any) => axios.post(`${API_URL}/invitations/`, data),
    createBulk: (data: any[]) => axios.post(`${API_URL}/invitations/bulk`, data),
    preview: (interviewId: number, data: { candidate_name?: string; custom_message?: string }) => axios.post(`${API_URL}/invitations/preview/${interviewId}`, data),
    list: (interviewId: number) => axios.get(`${API_URL}/invitations/${interviewId}`),
    verify: (token: string) => axios.get(`${API_URL}/invitations/verify/${token}`),
    getResults: (token: string) => axios.get(`${API_URL}/invitations/${token}/results`),
    resend: (invitationId: number) => axios.post(`${API_URL}/invitations/${invitationId}/resend`),
    revoke: (invitationId: number) => axios.post(`${API_URL}/invitations/${invitationId}/revoke`),
    cancel: (invitationId: number) => axios.delete(`${API_URL}/invitations/${invitationId}/cancel`),
    cancelAll: (interviewId: number) => axios.delete(`${API_URL}/invitations/${interviewId}/cancel-all`),
  },

  // Pre-interview system check
  systemCheck: {
    ping: () => axios.get(`${API_URL}/system-check/ping`),
    download: (sizeMb: number) =>
      axios.get(`${API_URL}/system-check/download`, {
        params: { size_mb: sizeMb },
        responseType: 'arraybuffer',
      }),
    upload: (payload: Blob) =>
      axios.post(`${API_URL}/system-check/upload`, payload, {
        headers: { 'Content-Type': 'application/octet-stream' },
      }),
  },
  
  // Responses
  responses: {
    start: (data: any) => axios.post(`${API_URL}/responses/`, data),
    submitAnswer: (responseId: number, questionId: number, answerText: string, audioFile?: File, videoFile?: File, timeTaken?: number, onUploadProgress?: (progressEvent: any) => void, invitationToken?: string) => {
      const hasFile = !!(audioFile || videoFile)
      const formData = new FormData()
      if (audioFile) {
        formData.append('audio_file', audioFile)
      }
      if (videoFile) {
        formData.append('video_file', videoFile)
      }
      return axios.post(`${API_URL}/responses/${responseId}/answer`, hasFile ? formData : null, {
        ...(hasFile ? { headers: { 'Content-Type': 'multipart/form-data' } } : {}),
        params: {
          question_id: questionId,
          answer_text: answerText,
          ...(timeTaken ? { time_taken_seconds: timeTaken } : {}),
          ...(invitationToken ? { invitation_token: invitationToken } : {})
        },
        onUploadProgress
      })
    },
    submitQuality: (responseId: number, data: any, invitationToken?: string) => axios.post(`${API_URL}/responses/${responseId}/quality`, null, { params: { ...data, ...(invitationToken ? { invitation_token: invitationToken } : {}) } }),
    submitIntegrityEvents: (responseId: number, events: any[], invitationToken?: string) => axios.post(`${API_URL}/responses/${responseId}/integrity-events`, events, { params: invitationToken ? { invitation_token: invitationToken } : {} }),
    submitEmotion: (responseId: number, data: any, invitationToken?: string) => axios.post(`${API_URL}/responses/${responseId}/emotion`, null, { params: { ...data, ...(invitationToken ? { invitation_token: invitationToken } : {}) } }),
    complete: (responseId: number, invitationToken?: string) => axios.post(`${API_URL}/responses/${responseId}/complete`, null, { params: invitationToken ? { invitation_token: invitationToken } : {} }),
    getTimer: (responseId: number, invitationToken?: string) => axios.get(`${API_URL}/responses/${responseId}/timer`, { params: invitationToken ? { invitation_token: invitationToken } : {} }),
    list: (interviewId: number) => axios.get(`${API_URL}/responses/interview/${interviewId}`),
    get: (responseId: number) => axios.get(`${API_URL}/responses/${responseId}`),
    delete: (responseId: number) => axios.delete(`${API_URL}/responses/${responseId}`)
  },
  
  // Reports
  reports: {
    getInterviewReport: (interviewId: number) => axios.get(`${API_URL}/reports/interview/${interviewId}`),
    reevaluateInterview: (interviewId: number) => axios.post(`${API_URL}/reports/interview/${interviewId}/evaluations`),
    getInterviewEvaluationAnalytics: (interviewId: number) => axios.get(`${API_URL}/reports/interview/${interviewId}/evaluation-analytics`),
    getCandidateReport: (responseId: number) => axios.get(`${API_URL}/reports/candidate/${responseId}`),
    getCandidateEvaluations: (responseId: number) => axios.get(`${API_URL}/reports/candidate/${responseId}/evaluations`),
    reevaluateCandidate: (responseId: number) => axios.post(`${API_URL}/reports/candidate/${responseId}/evaluations`),
    getEvaluationHealth: (organizationId?: number) => axios.get(`${API_URL}/reports/evaluation/health`, { params: { organization_id: organizationId } }),
    getEmailHealth: () => axios.get(`${API_URL}/reports/email/health`),
    downloadInterviewPdf: (interviewId: number) => 
      axios.get(`${API_URL}/reports/interview/${interviewId}/pdf`, { responseType: 'blob' }),
    downloadCandidatePdf: (responseId: number) => 
      axios.get(`${API_URL}/reports/candidate/${responseId}/pdf`, { responseType: 'blob' }),
    exportInterviewCsv: (interviewId: number) => 
      axios.get(`${API_URL}/reports/interview/${interviewId}/export.csv`, { responseType: 'blob' }),
    getComparison: (interviewId: number) => 
      axios.get(`${API_URL}/reports/interview/${interviewId}/comparison`),
    getQuestionAnalytics: (interviewId: number) => 
      axios.get(`${API_URL}/reports/interview/${interviewId}/question-analytics`),
    getCandidateProfile: (candidateEmail: string) => 
      axios.get(`${API_URL}/reports/candidate/profile/${encodeURIComponent(candidateEmail)}`),
    getPlagiarismReport: (interviewId: number) => 
      axios.get(`${API_URL}/reports/interview/${interviewId}/plagiarism`),
    getMyResults: () => axios.get(`${API_URL}/reports/my-results`)
  },

  // In-app notifications
  notifications: {
    list: (limit = 20) => axios.get(`${API_URL}/notifications/`, { params: { limit } }),
    unreadCount: () => axios.get(`${API_URL}/notifications/unread-count`),
    markRead: (notificationId: number) => axios.post(`${API_URL}/notifications/${notificationId}/read`),
    markAllRead: () => axios.post(`${API_URL}/notifications/read-all`)
  }
}
