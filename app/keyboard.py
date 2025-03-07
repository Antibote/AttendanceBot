from datetime import date
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

import app.database.requests as rq

main = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text = "😇Создать группу студентов", callback_data = 'create_group_students')],
    [InlineKeyboardButton(text = '👌Выбрать группу студентов', callback_data = 'select_group_students')],
    [InlineKeyboardButton(text = '🥵Удадить группу студентов', callback_data = 'delete_group_students')]
])

def select_group(group_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📝 Отметить студентов", 
            callback_data=f"mark_attendance_{group_id}"
        )],
        [InlineKeyboardButton(
            text='📊 Посмотреть результат', 
            callback_data=f"show_report_{group_id}"
        )],
        [InlineKeyboardButton(
            text='➕ Добавить студентов', 
            callback_data=f"add_students_{group_id}"
        )],
        [InlineKeyboardButton(
            text='⬅️ На главную', 
            callback_data='to_main'
        )]
    ])

async def delete_groups(teacher_id: int):
    keyboard = InlineKeyboardBuilder()
    groups = await rq.get_groups(teacher_id)
    for group in groups:
        keyboard.add(InlineKeyboardButton(
            text=group.name, 
            callback_data=f"confirm_delete_{group.id}"
        ))
    keyboard.add(InlineKeyboardButton(
        text="⬅️На главную", 
        callback_data='to_main'
    ))
    return keyboard.adjust(1).as_markup()

async def confirm_delete_keyboard(group_id: int):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(
        text="✅ Да", 
        callback_data=f"final_delete_{group_id}"
    ))
    keyboard.add(InlineKeyboardButton(
        text="❌ Нет", 
        callback_data="to_main"
    ))
    return keyboard.adjust(2).as_markup()

async def groups(teacher_id):
    keyboard = InlineKeyboardBuilder()
    groups = await rq.get_groups(teacher_id)
    for group in groups:
        keyboard.add(InlineKeyboardButton(text = group.name, callback_data=f"group_{group.id}_{group.name}"))
    keyboard.add(InlineKeyboardButton(text = "⬅️На главную", callback_data = 'to_main'))
    return keyboard.adjust(1).as_markup()

def attendance_buttons(student_id: int, group_id: int, lesson_date: date):
    keyboard = InlineKeyboardBuilder()
    for text, status in [("✅ Присутствует", "на месте"), ("❌ Отсутствует", "не тут"),("🤒 Болеет", "болеет"),("2", "2"),("3", "3"),("4", "4"),("5", "5")]:
        keyboard.add(InlineKeyboardButton(text=text,callback_data=f"attendance_{student_id}_{status}_{group_id}_{lesson_date}"))
    keyboard.add(InlineKeyboardButton(text = "На главную", callback_data = 'to_main'))
    return keyboard.adjust(1).as_markup()

async def attendance_list(group_id: int, group_name: str, lesson_date: date):
    keyboard = InlineKeyboardBuilder()
    students = await rq.get_students_by_group(group_id)
    
    for student in students:
        keyboard.row(
            InlineKeyboardButton(
                text=f"🎓 {student.name}",
                callback_data=f"studentinfo_{student.id}"  # Изменяем формат
            )
        )
        status = await rq.get_attendance_status(student.id, lesson_date)
        keyboard.row(
            InlineKeyboardButton(
                text=status if status else "❓ Не отмечен",
                callback_data=f"set_status_{student.id}_{group_id}_{lesson_date}"
            )
        )
    
    keyboard.row(
        InlineKeyboardButton(
            text="📅 " + lesson_date.strftime("%d.%m.%Y"),
            callback_data="change_date"
        )
    )
    keyboard.row(
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"group_{group_id}_{group_name}"  # Убедимся в корректности
        )
    )
    return keyboard.as_markup()



def dates_pagination(group_id: int, current_page: int, total_pages: int):
    kb = InlineKeyboardBuilder()
    
    # Кнопки пагинации
    if current_page > 1:
        kb.button(text="⬅️", callback_data=f"dates_page_{group_id}_{current_page-1}")
    kb.button(text=f"{current_page}/{total_pages}", callback_data="ignore")
    if current_page < total_pages:
        kb.button(text="➡️", callback_data=f"dates_page_{group_id}_{current_page+1}")
    
    # Дополнительные кнопки
    kb.row(
        InlineKeyboardButton(text="📊 Представить в Excel", callback_data=f"export_excel_{group_id}"),
        InlineKeyboardButton(text="🔄 Обновить", callback_data=f"refresh_report_{group_id}"),
        InlineKeyboardButton(text="⬅️ К группе", callback_data=f"group_{group_id}")
    )
    
    return kb.as_markup()