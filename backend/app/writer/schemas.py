from pydantic import BaseModel, Field


class ChartDataPoint(BaseModel):
    label: str
    value: float


class ChartData(BaseModel):
    title: str
    points: list[ChartDataPoint]


class Report(BaseModel):
    topic: str
    summary: str = Field(description="A narrative summary of the research findings.")
    insights: list[str] = Field(description="Key insights, one per list item.")
    chart: ChartData
