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
