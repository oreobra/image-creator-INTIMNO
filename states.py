from aiogram.fsm.state import State, StatesGroup


class ReferenceFlow(StatesGroup):
    """Function 1 — generate by reference image (2 variants), aware of panties material/color."""
    waiting_panties = State()         # waiting for panties photo(s) — analyzed for material/color
    waiting_reference = State()       # panties analyzed, waiting for reference photo
    choosing_extras = State()         # prompts ready, showing extras menu
    waiting_extras_text = State()     # user typing extras description
    waiting_extras_image = State()    # user sending extras photo


class DescribeFlow(StatesGroup):
    """Function 2 — describe style in words (1 variant), aware of panties material/color."""
    waiting_panties = State()         # waiting for panties photo(s) — analyzed for material/color
    waiting_description = State()     # panties analyzed, waiting for text description
    choosing_extras = State()
    waiting_extras_text = State()
    waiting_extras_image = State()


class StyleFlow(StatesGroup):
    """Function 3 — pick one of 5 preset styles (3 variants), aware of panties material/color."""
    waiting_panties = State()         # waiting for panties photo(s) — analyzed for material/color
    choosing_style = State()          # panties analyzed, waiting for style choice
    choosing_extras = State()
    waiting_extras_text = State()
    waiting_extras_image = State()


class FeedbackFlow(StatesGroup):
    """Shared post-generation feedback step, across all flows — a short guided Q&A."""
    waiting_consent = State()           # asking whether the user wants to answer a few quick questions
    waiting_dynamic_question = State()  # walking through the AI-generated, generation-specific questions
    waiting_comment = State()           # optional free-text comment
