import React, { useEffect, useState } from 'react'
import { Alert, Badge, Button, Card, Collapse, Form, Row, Col, Tabs, Tab } from 'react-bootstrap'
import { useTranslation } from 'react-i18next'
import { api } from '../services/api'
import { FiCpu, FiDownload, FiMail, FiActivity, FiSave } from 'react-icons/fi'
import PageHeader from '../components/ui/PageHeader'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import { useToast } from '../hooks/useToast'
import { useRealTimeRefresh } from '../hooks/useRealTimeRefresh'

const IntegrationSettings: React.FC = () => {
  const { t } = useTranslation()
  const toast = useToast()
  const [organization, setOrganization] = useState<any>(null)
  const [evaluationHealth, setEvaluationHealth] = useState<any>(null)
  const [emailHealth, setEmailHealth] = useState<any>(null)
  const [providersInfo, setProvidersInfo] = useState<any>(null)
  const [providerSelection, setProviderSelection] = useState('')
  const [providerModel, setProviderModel] = useState('')
  const [providerBaseUrl, setProviderBaseUrl] = useState('')
  const [providerApiKey, setProviderApiKey] = useState('')
  const [presets, setPresets] = useState<any[]>([])
  const [selectedPreset, setSelectedPreset] = useState('')
  const [presetName, setPresetName] = useState('')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [savingProvider, setSavingProvider] = useState(false)
  const [loading, setLoading] = useState(true)

  const providerLabelMap: Record<string, string> = {
    '': t('dashboard.providerDefault'),
    local_vllm: t('dashboard.providerLocal'),
    cloud_llm: t('dashboard.providerCloud'),
    hybrid: t('dashboard.providerHybrid'),
  }

  const selectedProviderLabel = (selected: string | null | undefined) =>
    selected ? providerLabelMap[selected] || selected : providerLabelMap['']

  const load = async () => {
    const organizationResponse = await api.users.getMyOrganization()
    const org = organizationResponse.data
    setOrganization(org)
    setProviderModel(org.evaluation_model || '')
    setProviderBaseUrl(org.evaluation_base_url || '')
    const [evaluationHealthResponse, emailHealthResponse, providersResponse, presetsResponse] = await Promise.all([
      api.reports.getEvaluationHealth(org?.id),
      api.reports.getEmailHealth(),
      api.users.getOrganizationProviders(),
      api.users.listProviderPresets(),
    ])
    setEvaluationHealth(evaluationHealthResponse.data)
    setEmailHealth(emailHealthResponse.data)
    setProvidersInfo(providersResponse.data)
    setPresets(presetsResponse.data || [])
    setProviderSelection(providersResponse.data.selected || '')
  }

  useEffect(() => {
    load().catch(() => toast.error(t('dashboard.loadFailed'), t('dashboard.loadError'))).finally(() => setLoading(false))
  }, [])

  useRealTimeRefresh(load, [])

  const handleSaveProvider = async (event: React.FormEvent) => {
    event.preventDefault()
    setSavingProvider(true)
    try {
      const response = await api.users.updateOrganizationSettings({
        evaluation_provider: providerSelection || '',
        evaluation_model: providerModel,
        evaluation_base_url: providerBaseUrl,
        evaluation_api_key: providerApiKey,
      })
      setOrganization(response.data)
      if (providersInfo) {
        setProvidersInfo({ ...providersInfo, selected: response.data.evaluation_provider })
      }
      setProviderApiKey('')
      toast.success(t('dashboard.providerSaved'))
    } catch {
      toast.error(t('dashboard.providerSaveFailed'))
    } finally {
      setSavingProvider(false)
    }
  }

  const refreshPresets = async () => {
    const res = await api.users.listProviderPresets()
    setPresets(res.data || [])
  }

  const handleApplyPreset = async () => {
    if (!selectedPreset) return
    try {
      const response = await api.users.applyProviderPreset(Number(selectedPreset))
      setOrganization(response.data)
      setProviderSelection(response.data.evaluation_provider || '')
      setProviderModel(response.data.evaluation_model || '')
      setProviderBaseUrl(response.data.evaluation_base_url || '')
      setProviderApiKey('')
      if (providersInfo) {
        setProvidersInfo({ ...providersInfo, selected: response.data.evaluation_provider })
      }
      setSelectedPreset('')
      toast.success(t('dashboard.presetLoaded'))
    } catch {
      toast.error(t('dashboard.presetLoadFailed'))
    }
  }

  const handleSavePreset = async () => {
    const name = presetName.trim()
    if (!name) {
      toast.error(t('dashboard.presetNameRequired'))
      return
    }
    try {
      await api.users.createProviderPreset({
        name,
        provider: providerSelection || '',
        model: providerModel || null,
        base_url: providerBaseUrl || null,
        api_key: providerApiKey || null,
      })
      setPresetName('')
      setProviderApiKey('')
      await refreshPresets()
      toast.success(t('dashboard.presetSaved'))
    } catch {
      toast.error(t('dashboard.presetSaveFailed'))
    }
  }

  const handleDeletePreset = async (id: number) => {
    if (!window.confirm(t('dashboard.presetConfirmDelete'))) return
    try {
      await api.users.deleteProviderPreset(id)
      await refreshPresets()
      toast.success(t('dashboard.presetDeleted'))
    } catch {
      toast.error(t('dashboard.presetDeleteFailed'))
    }
  }

  if (loading) return <LoadingSpinner text={t('dashboard.loading')} />

  return (
    <div>
      <PageHeader title={t('dashboard.integrationsTitle')} subtitle={t('dashboard.integrationsSubtitle')} />

      <Card>
        <Card.Body>
          <Tabs defaultActiveKey="provider">
            <Tab
              eventKey="provider"
              title={<span className="d-inline-flex align-items-center gap-2"><FiCpu />{t('dashboard.providerSettings')}</span>}
            >
              <div className="pt-3">
                <p className="text-muted small mb-3">{t('dashboard.providerSettingsSubtitle')}</p>
                {providersInfo ? (
                  providersInfo.role === 'owner' || providersInfo.role === 'admin' ? (
                    <Form onSubmit={handleSaveProvider}>
                      <Row className="g-3 align-items-end mb-3">
                        <Col md={6} xl={5}>
                          <Form.Label className="small text-muted">{t('dashboard.presetLabel')}</Form.Label>
                          <Form.Select
                            size="sm"
                            value={selectedPreset}
                            onChange={(e) => setSelectedPreset(e.target.value)}
                            aria-label={t('dashboard.presetLabel')}
                          >
                            <option value="">{t('dashboard.presetPlaceholder')}</option>
                            {presets.map((p: any) => (
                              <option key={p.id} value={p.id}>
                                {p.name} — {providerLabelMap[p.provider] || p.provider}
                                {p.api_key_set ? ' 🔑' : ''}
                              </option>
                            ))}
                          </Form.Select>
                        </Col>
                        <Col md={3} xl={2}>
                          <Button variant="outline-secondary" size="sm" className="w-100" onClick={handleApplyPreset} disabled={!selectedPreset}>
                            <FiDownload className="me-1" /> {t('dashboard.presetLoad')}
                          </Button>
                        </Col>
                        <Col md={3} xl={2}>
                          <Form.Label className="small text-muted">{t('dashboard.presetName')}</Form.Label>
                          <Form.Control size="sm" type="text" value={presetName} onChange={(e) => setPresetName(e.target.value)} placeholder={t('dashboard.presetName')} />
                        </Col>
                        <Col md={3} xl={2}>
                          <Button variant="outline-primary" size="sm" className="w-100" onClick={handleSavePreset}>
                            <FiSave className="me-1" /> {t('dashboard.presetSaveAs')}
                          </Button>
                        </Col>
                      </Row>
                      {presets.length > 0 && (
                        <Row className="mb-3">
                          <Col>
                            <div className="d-flex flex-wrap gap-2">
                              {presets.map((p: any) => (
                                <span key={p.id} className="badge text-bg-light border d-inline-flex align-items-center gap-2">
                                  {p.name}
                                  <button
                                    type="button"
                                    className="btn-close btn-close-sm"
                                    aria-label={t('dashboard.presetDeleteFailed')}
                                    onClick={() => handleDeletePreset(p.id)}
                                  />
                                </span>
                              ))}
                            </div>
                          </Col>
                        </Row>
                      )}
                      <Row className="g-3 align-items-end">
                        <Col md={6} xl={4}>
                          <Form.Label className="small text-muted">{t('dashboard.provider')}</Form.Label>
                          <Form.Select
                            value={providerSelection}
                            onChange={(e) => setProviderSelection(e.target.value)}
                            size="sm"
                            aria-label={t('dashboard.provider')}
                          >
                            <option value="">{t('dashboard.providerDefault')}</option>
                            {providersInfo.providers.map((p: any) => (
                              <option key={p.value} value={p.value} disabled={!p.available}>
                                {providerLabelMap[p.value] || p.value}
                                {!p.available ? ` (${t('dashboard.providerUnavailable')})` : ''}
                              </option>
                            ))}
                          </Form.Select>
                        </Col>
                        <Col md={3} xl={2}>
                          <Button type="submit" variant="primary" size="sm" className="w-100" disabled={savingProvider}>
                            <FiSave className="me-1" /> {t('common.save')}
                          </Button>
                        </Col>
                      </Row>
                      <Button
                        variant="link"
                        size="sm"
                        className="p-0 mt-2 text-decoration-none"
                        onClick={() => setShowAdvanced((s) => !s)}
                        aria-expanded={showAdvanced}
                      >
                        {t('dashboard.providerAdvanced')}
                      </Button>
                      <Collapse in={showAdvanced}>
                        <div>
                          <Row className="g-3 mt-0">
                            <Col md={4}>
                              <Form.Label className="small text-muted">{t('dashboard.providerModel')}</Form.Label>
                              <Form.Control size="sm" type="text" value={providerModel} onChange={(e) => setProviderModel(e.target.value)} />
                            </Col>
                            <Col md={4}>
                              <Form.Label className="small text-muted">{t('dashboard.providerBaseUrl')}</Form.Label>
                              <Form.Control size="sm" type="text" value={providerBaseUrl} onChange={(e) => setProviderBaseUrl(e.target.value)} />
                            </Col>
                            <Col md={4}>
                              <Form.Label className="small text-muted">{t('dashboard.providerApiKey')}</Form.Label>
                              <Form.Control size="sm" type="password" value={providerApiKey} onChange={(e) => setProviderApiKey(e.target.value)} autoComplete="off" />
                            </Col>
                          </Row>
                        </div>
                      </Collapse>
                    </Form>
                  ) : (
                    <p className="mb-0">
                      <Badge bg="secondary" pill>{selectedProviderLabel(providersInfo.selected)}</Badge>{' '}
                      <span className="text-muted small">{t('dashboard.providerReadOnly')}</span>
                    </p>
                  )
                ) : (
                  <p className="text-muted mb-0 small">{t('dashboard.unavailable')}</p>
                )}
              </div>
            </Tab>

            <Tab
              eventKey="evaluation"
              title={<span className="d-inline-flex align-items-center gap-2"><FiActivity />{t('dashboard.evaluationAgent')}</span>}
            >
              <div className="pt-3">
                {evaluationHealth ? (
                  <Row>
                    <Col xs={6}><p className="mb-1 text-muted small">{t('dashboard.status')}</p><Badge bg={evaluationHealth.healthy ? 'success' : 'warning'}>{evaluationHealth.status}</Badge></Col>
                    <Col xs={6}><p className="mb-1 text-muted small">{t('dashboard.provider')}</p><p className="mb-0 fw-medium">{evaluationHealth.provider}</p></Col>
                    <Col xs={6} className="mt-3"><p className="mb-1 text-muted small">{t('dashboard.model')}</p><p className="mb-0 fw-medium">{evaluationHealth.model_name || t('common.n/a')}</p></Col>
                    <Col xs={6} className="mt-3"><p className="mb-1 text-muted small">{t('dashboard.fallback')}</p><p className="mb-0 fw-medium">{evaluationHealth.fallback_provider || t('common.n/a')}</p></Col>
                    <Col xs={6} className="mt-3"><p className="mb-1 text-muted small">{t('dashboard.promptVersion')}</p><p className="mb-0 fw-medium">{evaluationHealth.prompt_version || t('common.n/a')}</p></Col>
                    <Col xs={6} className="mt-3"><p className="mb-1 text-muted small">{t('dashboard.configHash')}</p><p className="mb-0 fw-medium">{evaluationHealth.config_hash || t('common.n/a')}</p></Col>
                    {evaluationHealth.last_error && (
                      <Col xs={12} className="mt-3"><Alert variant="warning" className="mb-0 py-2 small">{evaluationHealth.last_error}</Alert></Col>
                    )}
                  </Row>
                ) : (
                  <p className="text-muted mb-0 small">{t('dashboard.unavailable')}</p>
                )}
              </div>
            </Tab>

            <Tab
              eventKey="email"
              title={<span className="d-inline-flex align-items-center gap-2"><FiMail />{t('dashboard.emailDelivery')}</span>}
            >
              <div className="pt-3">
                {emailHealth ? (
                  <Row>
                    <Col xs={6}><p className="mb-1 text-muted small">{t('dashboard.status')}</p><Badge bg={emailHealth.configured ? 'success' : 'warning'}>{emailHealth.status}</Badge></Col>
                    <Col xs={6}><p className="mb-1 text-muted small">{t('dashboard.from')}</p><p className="mb-0 fw-medium">{emailHealth.mail_from}</p></Col>
                    <Col xs={6} className="mt-3"><p className="mb-1 text-muted small">{t('dashboard.server')}</p><p className="mb-0 fw-medium">{emailHealth.mail_server}:{emailHealth.mail_port}</p></Col>
                    <Col xs={6} className="mt-3"><p className="mb-1 text-muted small">{t('dashboard.missing')}</p><p className="mb-0 fw-medium">{emailHealth.missing_settings?.length ? emailHealth.missing_settings.join(', ') : t('common.none')}</p></Col>
                  </Row>
                ) : (
                  <p className="text-muted mb-0 small">{t('dashboard.unavailable')}</p>
                )}
              </div>
            </Tab>
          </Tabs>
        </Card.Body>
      </Card>
    </div>
  )
}

export default IntegrationSettings
