import axios from 'axios'

const API_URL = '/api'

export const api = {
  // Users and organization
  users: {
    getMyOrganization: () => axios.get(`${API_URL}/users/me/organization`),
    getMyMemberships: () => axios.get(`${API_URL}/users/me/memberships`),
    addMembership: (data: { email: string; role: string }) => axios.post(`${API_URL}/users/me/memberships`, data)
  },

  // Interviews
  interviews: {
    create: (data: any) => axios.post(`${API_URL}/interviews/`, data),
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
    list: (interviewId: number) => axios.get(`${API_URL}/invitations/${interviewId}`),
    verify: (token: string) => axios.get(`${API_URL}/invitations/verify/${token}`),
    resend: (invitationId: number) => axios.post(`${API_URL}/invitations/${invitationId}/resend`)
  },
  
  // Responses
  responses: {
    start: (data: any) => axios.post(`${API_URL}/responses/`, data),
    submitAnswer: (responseId: number, questionId: number, answerText: string, audioFile?: File, timeTaken?: number) => {
      const formData = new FormData()
      formData.append('answer_text', answerText)
      if (audioFile) {
        formData.append('audio_file', audioFile)
      }
      if (timeTaken) {
        formData.append('time_taken_seconds', timeTaken.toString())
      }
      return axios.post(`${API_URL}/responses/${responseId}/answer?question_id=${questionId}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    },
    submitQuality: (responseId: number, data: any) => axios.post(`${API_URL}/responses/${responseId}/quality`, data),
    submitEmotion: (responseId: number, data: any) => axios.post(`${API_URL}/responses/${responseId}/emotion`, data),
    complete: (responseId: number) => axios.post(`${API_URL}/responses/${responseId}/complete`),
    list: (interviewId: number) => axios.get(`${API_URL}/responses/interview/${interviewId}`),
    get: (responseId: number) => axios.get(`${API_URL}/responses/${responseId}`)
  },
  
  // Reports
  reports: {
    getInterviewReport: (interviewId: number) => axios.get(`${API_URL}/reports/interview/${interviewId}`),
    getCandidateReport: (responseId: number) => axios.get(`${API_URL}/reports/candidate/${responseId}`),
    downloadInterviewPdf: (interviewId: number) => 
      axios.get(`${API_URL}/reports/interview/${interviewId}/pdf`, { responseType: 'blob' }),
    downloadCandidatePdf: (responseId: number) => 
      axios.get(`${API_URL}/reports/candidate/${responseId}/pdf`, { responseType: 'blob' }),
    getMyResults: () => axios.get(`${API_URL}/reports/my-results`)
  }
}
