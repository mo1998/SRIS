import React, { useState } from 'react'
import { Container } from 'react-bootstrap'
import { FiCheckCircle, FiAlertCircle } from 'react-icons/fi'
import { useTranslation } from 'react-i18next'
import SystemCheck from './SystemCheck'
import PracticeMode from './PracticeMode'
import PageHeader from '../components/ui/PageHeader'

const PracticeArea: React.FC = () => {
  const { t } = useTranslation()
  const [step, setStep] = useState<'intro' | 'systemcheck' | 'practice' | 'done'>('intro')
  const [checkPassed, setCheckPassed] = useState<boolean | null>(null)

  return (
    <Container className="mt-4">
      <PageHeader
        title={t('sidebar.practiceArea')}
        subtitle={t('practiceArea.subtitle')}
      />

      {step === 'intro' && (
        <div className="text-center py-5">
          <FiCheckCircle size={64} className="text-success mb-3" />
          <h3>{t('practiceArea.introTitle')}</h3>
          <p className="text-muted mb-4">{t('practiceArea.introBody')}</p>
          <button
            className="btn btn-primary btn-lg"
            onClick={() => {
              setCheckPassed(null)
              setStep('systemcheck')
            }}
          >
            {t('practiceArea.runSystemCheck')}
          </button>
        </div>
      )}

      {step === 'systemcheck' && (
        <SystemCheck
          onDone={(passed) => {
            setCheckPassed(passed)
            if (passed) {
              setStep('done')
            }
          }}
          onCancel={() => setStep(checkPassed === true ? 'done' : 'intro')}
        />
      )}

      {step === 'practice' && (
        <PracticeMode onExit={() => setStep(checkPassed === true ? 'done' : 'systemcheck')} />
      )}

      {step === 'done' && (
        <div className="text-center py-5">
          {checkPassed ? (
            <>
              <FiCheckCircle size={64} className="text-success mb-3" />
              <h3>{t('practiceArea.allGood')}</h3>
              <p className="text-muted mb-4">{t('practiceArea.allGoodBody')}</p>
              <div className="d-flex gap-2 justify-content-center">
                <button className="btn btn-outline-primary" onClick={() => setStep('systemcheck')}>
                  {t('practiceArea.runAgain')}
                </button>
                <button className="btn btn-success" onClick={() => setStep('practice')}>
                  {t('practiceMode.title')}
                </button>
              </div>
            </>
          ) : (
            <>
              <FiAlertCircle size={64} className="text-danger mb-3" />
              <h3>{t('practiceArea.issuesFound')}</h3>
              <p className="text-muted mb-4">{t('practiceArea.issuesBody')}</p>
              <button className="btn btn-primary" onClick={() => setStep('systemcheck')}>
                {t('practiceArea.runAgain')}
              </button>
            </>
          )}
        </div>
      )}
    </Container>
  )
}

export default PracticeArea
