import axios from 'axios'

const API_URL = '/api'

export const api = {
  // Users and organization
  users: {
    updateMe: (data: { full_name?: string; phone?: string }) => axios.patch(`${API_URL}/users/me`, data),
    changePassword: (data: { current_password: string; new_password: string }) => axios.post(`${API_URL}/users/me/password`, data),
    getMyOrganization: () => axios.get(`${API_URL}/users/me/organization`),
    getMyMemberships: () => axios.get(`${API_URL}/users/me/memberships`),
    addMembership: (data: { email: string; role: string }) => axios.post(`${API_URL}/users/me/memberships`, data)
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
    addQuestion: (id: number, data: any) => axios.post(`${API_URL}/interviews/${id}/questions`, data)
  },
  
  // Invitations
  invitations: {
    create: (data: any) => axios.post(`${API_URL}/invitations/`, data),
    createBulk: (data: any[]) => axios.post(`${API_URL}/invitations/bulk`, data),
    preview: (interviewId: number, data: { candidate_name?: string; custom_message?: string }) => axios.post(`${API_URL}/invitations/preview/${interviewId}`, data),
    list: (interviewId: number) => axios.get(`${API_URL}/invitations/${interviewId}`),
    verify: (token: string) => axios.get(`${API_URL}/invitations/verify/${token}`),
    resend: (invitationId: number) => axios.post(`${API_URL}/invitations/${invitationId}/resend`),
    revoke: (invitationId: number) => axios.post(`${API_URL}/invitations/${invitationId}/revoke`)
  },
  
  // Responses
  responses: {
    start: (data: any) => axios.post(`${API_URL}/responses/`, data),
    submitAnswer: (responseId: number, questionId: number, answerText: string, audioFile?: File, timeTaken?: number, onUploadProgress?: (progressEvent: any) => void) => {
      const formData = new FormData()
      if (audioFile) {
        formData.append('audio_file', audioFile)
      }
      return axios.post(`${API_URL}/responses/${responseId}/answer`, audioFile ? formData : null, {
        ...(audioFile ? { headers: { 'Content-Type': 'multipart/form-data' } } : {}),
        params: {
          question_id: questionId,
          answer_text: answerText,
          ...(timeTaken ? { time_taken_seconds: timeTaken } : {})
        },
        onUploadProgress
      })
    },
    submitQuality: (responseId: number, data: any) => axios.post(`${API_URL}/responses/${responseId}/quality`, null, { params: data }),
    submitEmotion: (responseId: number, data: any) => axios.post(`${API_URL}/responses/${responseId}/emotion`, null, { params: data }),
    complete: (responseId: number) => axios.post(`${API_URL}/responses/${responseId}/complete`),
    list: (interviewId: number) => axios.get(`${API_URL}/responses/interview/${interviewId}`),
    get: (responseId: number) => axios.get(`${API_URL}/responses/${responseId}`)
  },
  
  // Reports
  reports: {
    getInterviewReport: (interviewId: number) => axios.get(`${API_URL}/reports/interview/${interviewId}`),
    getCandidateReport: (responseId: number) => axios.get(`${API_URL}/reports/candidate/${responseId}`),
    getCandidateEvaluations: (responseId: number) => axios.get(`${API_URL}/reports/candidate/${responseId}/evaluations`),
    reevaluateCandidate: (responseId: number) => axios.post(`${API_URL}/reports/candidate/${responseId}/evaluations`),
    downloadInterviewPdf: (interviewId: number) => 
      axios.get(`${API_URL}/reports/interview/${interviewId}/pdf`, { responseType: 'blob' }),
    downloadCandidatePdf: (responseId: number) => 
      axios.get(`${API_URL}/reports/candidate/${responseId}/pdf`, { responseType: 'blob' }),
    getMyResults: () => axios.get(`${API_URL}/reports/my-results`)
  }
}
