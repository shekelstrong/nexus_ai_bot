from aiogram.fsm.state import StatesGroup, State

class GenerationStates(StatesGroup):
    chatting = State()