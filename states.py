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


class FeedbackFlow(StatesGroup):
    """Shared post-generation feedback step, across all flows."""
    waiting_feedback = State()        # generation just finished, waiting for optional feedback
