from aiogram.fsm.state import State, StatesGroup


class ReferenceFlow(StatesGroup):
    """Function 1 — generate by reference image (2 variants)."""
    waiting_reference = State()       # waiting for reference photo
    waiting_panties = State()         # 2 prompts ready, waiting for panties photo
    choosing_extras = State()         # panties saved, showing extras menu
    waiting_extras_text = State()     # user typing extras description
    waiting_extras_image = State()    # user sending extras photo


class StyleFlow(StatesGroup):
    """Function 2 — generate by preset style (5 variants)."""
    waiting_panties = State()         # waiting for panties photo
    choosing_style = State()          # panties saved, showing style menu
    choosing_extras = State()         # style chosen, showing extras menu
    waiting_extras_text = State()
    waiting_extras_image = State()


class DescribeFlow(StatesGroup):
    """Function 3 — describe style in words (1 variant)."""
    waiting_description = State()     # waiting for text description
    waiting_panties = State()         # prompt ready, waiting for panties photo
    choosing_extras = State()
    waiting_extras_text = State()
    waiting_extras_image = State()
