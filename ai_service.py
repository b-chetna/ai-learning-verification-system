import json
import ollama


MODEL_NAME = "llama3.2:1b"


def generate_quiz_questions(subject, topic, count=5, difficulty="Medium"):
    """Generate multiple-choice questions using the local Ollama model."""
    prompt = f"""
Create exactly {count} multiple-choice quiz questions.

Subject: {subject}
Topic: {topic}
Difficulty: {difficulty}

Return valid JSON only, in this format:
{{
  "questions": [
    {{
      "question_text": "Question text",
      "option_a": "Option A",
      "option_b": "Option B",
      "option_c": "Option C",
      "option_d": "Option D",
      "correct_answer": "A",
      "explanation": "Short explanation"
    }}
  ]
}}

Requirements:
- Generate exactly {count} questions.
- correct_answer must be A, B, C, or D.
- All four options must be different and non-empty.
- All four options must have different meanings, not just different wording.
- Never repeat an option within the same question.
- Check option_a, option_b, option_c, and option_d before returning each question.
- Ensure exactly one option is correct and the other three are plausible but incorrect.
- If any options are duplicates, regenerate those options before returning the JSON.
- Include only one correct answer per question.
- Keep every question relevant to the subject and topic.
- Do not include Markdown fences or extra text outside the JSON.
"""
    response = ollama.chat(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        format="json",
        options={"temperature": 0.2},
    )
    data = json.loads(response.message.content)
    questions = data.get("questions")
    if not isinstance(questions, list) or len(questions) != count:
        actual = len(questions) if isinstance(questions, list) else 0
        raise ValueError(f"Expected {count} questions, but the AI returned {actual}.")

    required_fields = (
        "question_text", "option_a", "option_b", "option_c", "option_d",
        "correct_answer", "explanation",
    )
    cleaned_questions = []
    for index, item in enumerate(questions, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Question {index} has an invalid format.")
        for field in required_fields:
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError(f"Question {index} is missing the field: {field}")
        item = {field: item[field].strip() for field in required_fields}
        item["correct_answer"] = item["correct_answer"].upper()
        if item["correct_answer"] not in {"A", "B", "C", "D"}:
            raise ValueError(f"Question {index} has an invalid correct answer.")
        options = [item[f"option_{letter.lower()}"] for letter in "ABCD"]
        if len({option.casefold() for option in options}) != 4:
            raise ValueError(f"Question {index} contains duplicate options.")
        cleaned_questions.append(item)
    return cleaned_questions


def generate_question_hint(question, options):
    """Generate a hint without sending the correct answer to the model."""
    prompt = f"""
Give a short, useful hint to help a student reason through this question.
Do not reveal the correct answer or answer letter.
Do not eliminate all but one option.

Question: {question}

Options:
{options}

Return only the hint.
"""
    response = ollama.chat(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.4},
    )
    hint = response.message.content.strip()
    if not hint:
        raise ValueError("The AI returned an empty hint.")
    return hint
