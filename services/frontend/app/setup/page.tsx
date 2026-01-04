'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { 
  Rocket, 
  CheckCircle2, 
  Circle, 
  ArrowRight, 
  ArrowLeft,
  Link2,
  Key,
  TestTube,
  Loader2,
  AlertCircle,
  ExternalLink,
  Copy,
  Check,
  Sparkles,
  Shield
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface SetupStep {
  id: number
  title: string
  description: string
  completed: boolean
}

interface ConnectionStatus {
  bitrix24: boolean
  google: boolean
  database: boolean
}

export default function SetupWizardPage() {
  const router = useRouter()
  const [currentStep, setCurrentStep] = useState(1)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  
  // Form states
  const [webhookUrl, setWebhookUrl] = useState('')
  const [testResult, setTestResult] = useState<{success: boolean; message: string; data?: any} | null>(null)
  
  // Connection status
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({
    bitrix24: false,
    google: false,
    database: false
  })

  const steps: SetupStep[] = [
    {
      id: 1,
      title: 'Hoş Geldiniz',
      description: 'BitSheet24 kurulum sihirbazına hoş geldiniz',
      completed: currentStep > 1
    },
    {
      id: 2,
      title: 'Bitrix24 Bağlantısı',
      description: 'Webhook URL adresinizi girin',
      completed: connectionStatus.bitrix24
    },
    {
      id: 3,
      title: 'Bağlantı Testi',
      description: 'Bağlantınızı test edin',
      completed: testResult?.success || false
    },
    {
      id: 4,
      title: 'Tamamlandı',
      description: 'Kurulum başarıyla tamamlandı',
      completed: false
    }
  ]

  // Check initial status
  useEffect(() => {
    checkConnectionStatus()
  }, [])

  const checkConnectionStatus = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4001'}/api/v1/setup/status`)
      if (response.ok) {
        const data = await response.json()
        setConnectionStatus(data)
        if (data.bitrix24) {
          setCurrentStep(3)
        }
      }
    } catch (err) {
      console.error('Status check failed:', err)
    }
  }

  const handleWebhookSubmit = async () => {
    if (!webhookUrl.trim()) {
      setError('Lütfen webhook URL adresini girin')
      return
    }

    // Basic URL validation
    if (!webhookUrl.startsWith('https://') || !webhookUrl.includes('/rest/')) {
      setError('Geçersiz Bitrix24 webhook URL formatı. URL "https://..." ile başlamalı ve "/rest/" içermelidir.')
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4001'}/api/v1/setup/bitrix24`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ webhook_url: webhookUrl })
      })

      const data = await response.json()

      if (response.ok) {
        setConnectionStatus(prev => ({ ...prev, bitrix24: true }))
        setCurrentStep(3)
      } else {
        setError(data.detail || 'Bağlantı kaydedilemedi')
      }
    } catch (err) {
      setError('Sunucuya bağlanılamadı. Lütfen tekrar deneyin.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleTestConnection = async () => {
    setIsLoading(true)
    setError(null)
    setTestResult(null)

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4001'}/api/v1/setup/test-bitrix24`)
      const data = await response.json()

      if (response.ok && data.success) {
        setTestResult({
          success: true,
          message: 'Bağlantı başarılı!',
          data: data.data
        })
      } else {
        setTestResult({
          success: false,
          message: data.detail || 'Bağlantı testi başarısız'
        })
      }
    } catch (err) {
      setTestResult({
        success: false,
        message: 'Test sırasında hata oluştu'
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleComplete = () => {
    router.push('/dashboard')
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Step 1: Welcome
  const renderWelcomeStep = () => (
    <div className="text-center space-y-6">
      <div className="flex justify-center">
        <div className="w-24 h-24 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
          <Rocket className="w-12 h-12 text-white" />
        </div>
      </div>
      
      <div>
        <h2 className="text-3xl font-bold text-slate-900 mb-3">
          BitSheet24&apos;e Hoş Geldiniz! 🎉
        </h2>
        <p className="text-lg text-slate-600 max-w-md mx-auto">
          Birkaç basit adımda Bitrix24 verilerinizi Google Sheets ile senkronize etmeye başlayın.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
        <div className="p-4 bg-blue-50 rounded-xl">
          <Link2 className="w-8 h-8 text-blue-600 mx-auto mb-2" />
          <h3 className="font-semibold text-slate-800">1. Bağlantı</h3>
          <p className="text-sm text-slate-600">Bitrix24 webhook URL&apos;nizi girin</p>
        </div>
        <div className="p-4 bg-green-50 rounded-xl">
          <TestTube className="w-8 h-8 text-green-600 mx-auto mb-2" />
          <h3 className="font-semibold text-slate-800">2. Test</h3>
          <p className="text-sm text-slate-600">Bağlantınızı doğrulayın</p>
        </div>
        <div className="p-4 bg-purple-50 rounded-xl">
          <Sparkles className="w-8 h-8 text-purple-600 mx-auto mb-2" />
          <h3 className="font-semibold text-slate-800">3. Başla</h3>
          <p className="text-sm text-slate-600">Verileri senkronize edin</p>
        </div>
      </div>

      <Button 
        size="lg" 
        onClick={() => setCurrentStep(2)}
        className="mt-8 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
      >
        Kuruluma Başla
        <ArrowRight className="w-5 h-5 ml-2" />
      </Button>
    </div>
  )

  // Step 2: Bitrix24 Connection
  const renderBitrixStep = () => (
    <div className="space-y-6">
      <div className="text-center mb-8">
        <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <Link2 className="w-8 h-8 text-blue-600" />
        </div>
        <h2 className="text-2xl font-bold text-slate-900">Bitrix24 Bağlantısı</h2>
        <p className="text-slate-600 mt-2">Bitrix24 webhook URL adresinizi girin</p>
      </div>

      {/* Help Box */}
      <Card className="bg-amber-50 border-amber-200">
        <CardContent className="p-4">
          <h4 className="font-semibold text-amber-800 mb-2 flex items-center gap-2">
            <Key className="w-4 h-4" />
            Webhook URL nasıl alınır?
          </h4>
          <ol className="text-sm text-amber-700 space-y-1 list-decimal list-inside">
            <li>Bitrix24 paneline giriş yapın</li>
            <li>Sol menüden <strong>Uygulamalar</strong> → <strong>Geliştirici kaynakları</strong> seçin</li>
            <li><strong>Diğer</strong> → <strong>Gelen webhook</strong> tıklayın</li>
            <li>Webhook URL&apos;yi kopyalayın</li>
          </ol>
          <a 
            href="https://helpdesk.bitrix24.com/open/17169604/" 
            target="_blank" 
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-sm text-amber-800 hover:text-amber-900 mt-2 font-medium"
          >
            Detaylı rehber için tıklayın
            <ExternalLink className="w-3 h-3" />
          </a>
        </CardContent>
      </Card>

      {/* Input */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-slate-700">
          Bitrix24 Webhook URL
        </label>
        <div className="flex gap-2">
          <Input
            type="url"
            placeholder="https://yourdomain.bitrix24.com/rest/1/xxxxx/"
            value={webhookUrl}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setWebhookUrl(e.target.value)}
            className="flex-1 text-base"
          />
          {webhookUrl && (
            <Button
              variant="outline"
              size="icon"
              onClick={() => copyToClipboard(webhookUrl)}
            >
              {copied ? <Check className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
            </Button>
          )}
        </div>
        <p className="text-xs text-slate-500">
          Bu URL güvenli şekilde sunucuda saklanacaktır
        </p>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="w-4 h-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Security Note */}
      <div className="flex items-start gap-2 p-3 bg-slate-50 rounded-lg">
        <Shield className="w-5 h-5 text-slate-600 mt-0.5" />
        <div className="text-sm text-slate-600">
          <strong>Güvenlik:</strong> Webhook URL&apos;niz sunucu tarafında şifreli olarak saklanır ve 
          asla başka bir yerle paylaşılmaz.
        </div>
      </div>

      {/* Navigation */}
      <div className="flex justify-between pt-4">
        <Button variant="outline" onClick={() => setCurrentStep(1)}>
          <ArrowLeft className="w-4 h-4 mr-2" />
          Geri
        </Button>
        <Button 
          onClick={handleWebhookSubmit}
          disabled={isLoading || !webhookUrl.trim()}
          className="bg-blue-600 hover:bg-blue-700"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Kaydediliyor...
            </>
          ) : (
            <>
              Kaydet ve Devam Et
              <ArrowRight className="w-4 h-4 ml-2" />
            </>
          )}
        </Button>
      </div>
    </div>
  )

  // Step 3: Test Connection
  const renderTestStep = () => (
    <div className="space-y-6">
      <div className="text-center mb-8">
        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <TestTube className="w-8 h-8 text-green-600" />
        </div>
        <h2 className="text-2xl font-bold text-slate-900">Bağlantı Testi</h2>
        <p className="text-slate-600 mt-2">Bitrix24 bağlantınızı test edin</p>
      </div>

      {/* Test Button */}
      <div className="flex justify-center">
        <Button
          size="lg"
          onClick={handleTestConnection}
          disabled={isLoading}
          className="bg-green-600 hover:bg-green-700 px-8"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-5 h-5 mr-2 animate-spin" />
              Test Ediliyor...
            </>
          ) : (
            <>
              <TestTube className="w-5 h-5 mr-2" />
              Bağlantıyı Test Et
            </>
          )}
        </Button>
      </div>

      {/* Test Result */}
      {testResult && (
        <Card className={testResult.success ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}>
          <CardContent className="p-6">
            <div className="flex items-start gap-4">
              {testResult.success ? (
                <CheckCircle2 className="w-8 h-8 text-green-600 flex-shrink-0" />
              ) : (
                <AlertCircle className="w-8 h-8 text-red-600 flex-shrink-0" />
              )}
              <div className="flex-1">
                <h3 className={`font-semibold ${testResult.success ? 'text-green-800' : 'text-red-800'}`}>
                  {testResult.message}
                </h3>
                {testResult.data && (
                  <div className="mt-3 space-y-2 text-sm text-green-700">
                    <p><strong>Portal:</strong> {testResult.data.portal_url}</p>
                    <p><strong>Kullanıcı:</strong> {testResult.data.user_name}</p>
                    <p><strong>Anlaşma Sayısı:</strong> {testResult.data.deals_count}</p>
                    <p><strong>Kişi Sayısı:</strong> {testResult.data.contacts_count}</p>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Navigation */}
      <div className="flex justify-between pt-4">
        <Button variant="outline" onClick={() => setCurrentStep(2)}>
          <ArrowLeft className="w-4 h-4 mr-2" />
          Geri
        </Button>
        <Button 
          onClick={() => setCurrentStep(4)}
          disabled={!testResult?.success}
          className="bg-purple-600 hover:bg-purple-700"
        >
          Kurulumu Tamamla
          <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    </div>
  )

  // Step 4: Complete
  const renderCompleteStep = () => (
    <div className="text-center space-y-6">
      <div className="flex justify-center">
        <div className="w-24 h-24 bg-gradient-to-br from-green-400 to-green-600 rounded-full flex items-center justify-center">
          <CheckCircle2 className="w-14 h-14 text-white" />
        </div>
      </div>
      
      <div>
        <h2 className="text-3xl font-bold text-slate-900 mb-3">
          Tebrikler! 🎊
        </h2>
        <p className="text-lg text-slate-600 max-w-md mx-auto">
          Kurulum başarıyla tamamlandı. Artık Bitrix24 verilerinizi Google Sheets&apos;e aktarmaya başlayabilirsiniz.
        </p>
      </div>

      <div className="bg-green-50 border border-green-200 rounded-xl p-6 max-w-md mx-auto">
        <h4 className="font-semibold text-green-800 mb-3">Sonraki Adımlar</h4>
        <ul className="text-left text-sm text-green-700 space-y-2">
          <li className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" />
            Dashboard&apos;dan verilerinizi görüntüleyin
          </li>
          <li className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" />
            Sheet Sync ile Google Sheets&apos;e aktarın
          </li>
          <li className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" />
            AI özet özelliğini deneyin
          </li>
        </ul>
      </div>

      <Button 
        size="lg" 
        onClick={handleComplete}
        className="mt-8 bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700"
      >
        Dashboard&apos;a Git
        <ArrowRight className="w-5 h-5 ml-2" />
      </Button>
    </div>
  )

  const renderCurrentStep = () => {
    switch (currentStep) {
      case 1: return renderWelcomeStep()
      case 2: return renderBitrixStep()
      case 3: return renderTestStep()
      case 4: return renderCompleteStep()
      default: return renderWelcomeStep()
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 py-4">
        <div className="container mx-auto px-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Image
              src="/icon-64.png"
              alt="BitSheet24"
              width={40}
              height={40}
              className="rounded-lg"
            />
            <div>
              <h1 className="font-bold text-xl text-slate-900">BitSheet24</h1>
              <p className="text-xs text-slate-500">Kurulum Sihirbazı</p>
            </div>
          </div>
          <Button variant="ghost" onClick={() => router.push('/dashboard')}>
            Atla
          </Button>
        </div>
      </header>

      {/* Progress Steps */}
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-center mb-8">
          <div className="flex items-center gap-2">
            {steps.map((step, index) => (
              <div key={step.id} className="flex items-center">
                <div 
                  className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold transition-colors ${
                    step.completed 
                      ? 'bg-green-500 text-white' 
                      : currentStep === step.id 
                        ? 'bg-blue-600 text-white' 
                        : 'bg-slate-200 text-slate-500'
                  }`}
                >
                  {step.completed ? <CheckCircle2 className="w-5 h-5" /> : step.id}
                </div>
                {index < steps.length - 1 && (
                  <div className={`w-12 h-1 mx-2 rounded ${
                    step.completed ? 'bg-green-500' : 'bg-slate-200'
                  }`} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Step Title */}
        <div className="text-center mb-8">
          <span className="text-sm text-slate-500">
            Adım {currentStep} / {steps.length}
          </span>
        </div>

        {/* Main Content */}
        <Card className="max-w-2xl mx-auto shadow-lg">
          <CardContent className="p-8">
            {renderCurrentStep()}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
