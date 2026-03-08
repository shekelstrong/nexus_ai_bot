from aiogram.fsm.state import State, StatesGroup

class GenState(StatesGroup):
    # Для обычных моделей (ждем промпт или файл)
    waiting_for_input = State()
    
    # Состояние для блокировки повторных запросов во время генерации
    generating = State()  # Генерация в процессе

    # Для сложных сценариев (Motion Control, First-Last)
    waiting_for_first_image = State()   # Ждем картинку персонажа / первого кадра
    waiting_for_second_image = State()  # Ждем второй кадр (для First-Last)
    waiting_for_reference_video = State() # Ждем видео с движением (для Motion Control)