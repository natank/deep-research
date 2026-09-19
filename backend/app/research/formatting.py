from app.research.schemas import ResearchContext


def format_research_context(context: ResearchContext) -> str:
    lines = [
        "<untrusted-research-topic>",
        context.topic,
        "</untrusted-research-topic>",
    ]
    if context.clarification_answers:
        lines.extend(
            [
                "<untrusted-clarification>",
                *[
                    f"{index}. question_id={answer.question_id}\n"
                    f"question={answer.question}\nanswer={answer.answer}"
                    for index, answer in enumerate(context.clarification_answers, start=1)
                ],
                "</untrusted-clarification>",
            ]
        )
    return "\n".join(lines)
