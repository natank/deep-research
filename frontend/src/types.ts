export interface SourceArticle {
  title: string
  url: string
  content: string
  score: number
}

export interface ChartDataPoint {
  label: string
  value: number
}

export interface ChartData {
  title: string
  points: ChartDataPoint[]
}

export interface Report {
  topic: string
  summary: string
  insights: string[]
  chart: ChartData
}

export interface EmailResult {
  status: string
  recipient: string
  report_id: string
  filename: string
}

export interface ResearchResult {
  report: Report
  sources: SourceArticle[]
  email: EmailResult
}

export type OrchestrationMode = 'code' | 'agent'

export interface ClarificationQuestion {
  id: string
  question: string
  purpose: string
}

export interface ClarificationDecision {
  needs_clarification: boolean
  questions: ClarificationQuestion[]
}

export interface ClarificationAnswer {
  question_id: string
  question: string
  answer: string
}
