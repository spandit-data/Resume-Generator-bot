"""State machine for resume conversation in Hindi."""

from typing import TypedDict


class UserState(TypedDict):
    step: int
    answers: dict[int, str]
    is_fresher: bool | None


# Questions for experienced users (all 10)
EXPERIENCED_QUESTIONS: list[str] = [
    "Namaste! Main aapka resume banane mein madad karunga. Sabse pehle aapka poora naam kya hai?",
    "Aapki umar kitni hai?",
    "Aap kaunse shehar mein kaam dhundh rahe hain?",
    "Aap kaunsi job dhundh rahe hain? Jaise delivery, field sales, warehouse picker, ya kuch aur?",
    "Kya aapne pehle kahi kaam kiya hai? Agar haan, toh kahan aur kya kaam kiya tha?",
    "Wahan aapne kitne time tak kaam kiya? (Jaise 6 mahine, 1 saal)",
    "Kya aapke paas koi vehicle hai? Jaise cycle, bike, ya car?",
    "Aapki padhai kitni hui hai? (Jaise 10th pass, 12th pass, ITI)",
    "Aapne yeh padhai kab poori ki? Matlb kaunse saal mein pass hua? (Jaise 2018, 2020 — agar yaad nahi toh 'pata nahi' bolein)",
    "Aapka mobile number kya hai?",
]

# Questions for fresher users (skip work experience questions, add hobbies)
FRESHER_QUESTIONS: list[str] = [
    "Namaste! Main aapka resume banane mein madad karunga. Sabse pehle aapka poora naam kya hai?",
    "Aapki umar kitni hai?",
    "Aap kaunse shehar mein kaam dhundh rahe hain?",
    "Aap kaunsi job dhundh rahe hain? Jaise delivery, field sales, warehouse picker, ya kuch aur?",
    "Kya aapke paas koi vehicle hai? Jaise cycle, bike, ya car?",
    "Aapki padhai kitni hui hai? (Jaise 10th pass, 12th pass, ITI)",
    "Aapne yeh padhai kab poori ki? Matlb kaunse saal mein pass hua? (Jaise 2018, 2020 — agar yaad nahi toh 'pata nahi' bolein)",
    "Aapka mobile number kya hai?",
    "Aapke kya hobbies hain? Jaise cricket khelna, music sunna, cooking, etc.?",
]

# Questions asked before selecting fresher/experienced
INITIAL_QUESTION = "Namaste! 🙏\n\nMain aapka resume banane mein madad karunga.\n\nKya aap fresher hai ya phir aapke paas pehle ka experience hai?"

FINAL_MESSAGE = (
    "Shukriya! Aapka resume taiyaar ho raha hai...\nThoda wait karein ⏳"
)

user_states: dict[int, UserState] = {}


def get_state(user_id: int) -> UserState:
    if user_id not in user_states:
        user_states[user_id] = {"step": 0, "answers": {}, "is_fresher": None}
    return user_states[user_id]


def reset_state(user_id: int) -> UserState:
    user_states[user_id] = {"step": 0, "answers": {}, "is_fresher": None}
    return user_states[user_id]


def save_answer(user_id: int, step: int, answer: str) -> None:
    state = get_state(user_id)
    state["answers"][step] = answer


def next_step(user_id: int) -> int:
    state = get_state(user_id)
    state["step"] += 1
    return state["step"]


def clear_state(user_id: int) -> None:
    if user_id in user_states:
        del user_states[user_id]


def set_fresher_status(user_id: int, is_fresher: bool) -> None:
    state = get_state(user_id)
    state["is_fresher"] = is_fresher


def get_questions(is_fresher: bool | None) -> list[str]:
    """Return the appropriate questions based on fresher status."""
    if is_fresher is None:
        return []
    elif is_fresher:
        return FRESHER_QUESTIONS
    else:
        return EXPERIENCED_QUESTIONS


def get_current_question(step: int, is_fresher: bool | None) -> str | None:
    questions = get_questions(is_fresher)
    if step < len(questions):
        return questions[step]
    return None


def is_complete(step: int, is_fresher: bool | None) -> bool:
    questions = get_questions(is_fresher)
    return step >= len(questions)


def is_awaiting_fresher_selection(user_id: int) -> bool:
    """Check if user is at the initial fresher/experienced selection."""
    state = get_state(user_id)
    return state["is_fresher"] is None