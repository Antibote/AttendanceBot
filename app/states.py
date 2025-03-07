from aiogram.fsm.state import StatesGroup, State


class CreateGroup(StatesGroup):
    name = State()


class CreateStudents(StatesGroup):
    group_id = State()
    students = State()