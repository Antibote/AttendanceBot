import re
from aiogram import F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import date, datetime
from app.utils import formatters
import app.keyboard as kb
import app.database.requests as rq
import app.states as st
from aiogram.types import BufferedInputFile

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await rq.set_teacher(message.from_user.id)
    await message.answer("Выбрать команду:", reply_markup=kb.main)

@router.callback_query(F.data == 'create_group_students')
async def create_group_students(callback: CallbackQuery, state: FSMContext):
    await callback.answer('Создаем группу')
    await state.set_state(st.CreateGroup.name)
    await callback.message.edit_text('Введите название группы')


@router.message(st.CreateGroup.name)
async def create_name_group(message: Message, state: FSMContext):
    await state.update_data(name = message.text)
    data = await state.get_data()
    teacher = await rq.get_teacher(message.from_user.id)
    await rq.create_group(data['name'], teacher.id)
    await message.answer(f"Группа создалась и называется она {data["name"]}",
                         reply_markup= kb.main)


@router.callback_query(F.data == 'select_group_students')
async def select_group_students(callback: CallbackQuery):
    await callback.answer('Шаманим с группой')
    teacher = await rq.get_teacher(callback.from_user.id)
    await callback.message.edit_text('Тут действия над группой', 
                                     reply_markup= await kb.groups(teacher.id))
    
@router.callback_query(F.data.startswith('group_'))
async def get_group(callback: CallbackQuery):
    parts = callback.data.split('_')
    group_id = int(parts[1])
    group_name = ' '.join(parts[2:])
    await callback.message.edit_text(
        f"Группа: {group_name} (ID: {group_id})",
        reply_markup=kb.select_group(group_id)
    )
    await callback.answer()

@router.callback_query(F.data == 'delete_group_students')
async def delete_group_students(callback: CallbackQuery):
    teacher = await rq.get_teacher(callback.from_user.id)
    await callback.message.edit_text(
        "Выберите группу для удаления:", 
        reply_markup=await kb.delete_groups(teacher.id)
    )

@router.callback_query(F.data.startswith('confirm_delete_'))
async def confirm_delete(callback: CallbackQuery):
    group_id = int(callback.data.split('_')[-1])
    await callback.message.edit_text(
        "Вы уверены, что хотите удалить группу?",
        reply_markup=kb.confirm_delete_keyboard(group_id)
    )

@router.callback_query(F.data.startswith('final_delete_'))
async def final_delete(callback: CallbackQuery):
    group_id = int(callback.data.split('_')[-1])
    await rq.delete_group(group_id)
    await callback.message.edit_text(
        "Группа и все связанные данные удалены!",
        reply_markup=kb.main
    )
    await callback.answer()

@router.callback_query(F.data == 'to_main')
async def cmd_main(callback: CallbackQuery):
    await callback.message.edit_text("Выбрать команду:", reply_markup=kb.main)

@router.callback_query(F.data.startswith('add_students_'))
async def add_students_of_group(callback: CallbackQuery, state: FSMContext):
    group_id = int(callback.data.split('_')[2])
    await state.update_data(group_id=group_id)
    await state.set_state(st.CreateStudents.students)
    await callback.message.answer(
        'Введите имена студентов:\n'
        '• Через запятую и пробел: "Иван, Мария, Петр"\n'
        '• Или с новой строки:\n'
        'Иван\n'
        'Мария\n'
        'Петр'
    )

@router.message(st.CreateStudents.students)
async def create_students(message: Message, state: FSMContext):
    data = await state.get_data()
    group_id = data['group_id']
    
    # Обрабатываем оба варианта ввода
    students = [name.strip() for name in re.split(r', |\n', message.text) if name.strip()]
    
    if not students:
        return await message.answer("Не найдено ни одного имени! Попробуйте снова.")
    
    try:
        group = await rq.get_group_by_id(group_id)
        if not group:
            return await message.answer("Группа не найдена!")
            
        await rq.add_students(students, group_id)
        await message.answer(
            f"Добавлено {len(students)} студентов в группу {group.name}:\n" 
            + "\n".join(f"• {name}" for name in students),
            reply_markup=kb.main
        )
        
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")

@router.callback_query(F.data.startswith('mark_attendance_'))
async def start_marking(callback: CallbackQuery):
    group_id = int(callback.data.split('_')[2])
    today = date.today()
    
    # Создаем записи для всех студентов
    await rq.create_attendance_records(group_id, today)
    
    # Получаем актуальные данные группы
    group = await rq.get_group_by_id(group_id)
    
    await callback.message.edit_text(
        f"Отметка посещаемости · {group.name}",
        reply_markup=await kb.attendance_list(
            group_id=group_id,
            group_name=group.name,
            lesson_date=today
        )
    )
    

@router.callback_query(F.data.startswith("set_status_"))
async def set_status(callback: CallbackQuery):
    parts = callback.data.split('_')
    student_id = int(parts[2])
    group_id = int(parts[3])
    lesson_date = datetime.strptime(parts[4], "%Y-%m-%d").date()
    
    await callback.message.edit_text(
        "Выберите статус:",
        reply_markup=kb.attendance_buttons(student_id, group_id, lesson_date)
    )

@router.callback_query(F.data.startswith("attendance_"))
async def save_attendance(callback: CallbackQuery):
    parts = callback.data.split('_')
    student_id = int(parts[1])
    status = parts[2]
    group_id = int(parts[3])
    lesson_date = date.fromisoformat(parts[4])  # Упрощенный парсинг даты
    
    # Получаем данные группы
    group = await rq.get_group_by_id(group_id)
    
    # Обновляем или создаем запись
    await rq.update_attendance(student_id, lesson_date, status)
    
    # Обновляем клавиатуру
    await callback.message.edit_reply_markup(
        reply_markup=await kb.attendance_list(
            group_id=group_id,
            group_name=group.name,
            lesson_date=lesson_date
        )
    )
    await callback.answer("✅ Статус обновлен")

@router.callback_query(F.data.startswith('student_'))
async def show_student_details(callback: CallbackQuery):
    student_id = int(callback.data.split('_')[1])
    # Здесь можно реализовать логику просмотра деталей студента
    await callback.answer(f"Студент ID: {student_id}")

@router.callback_query(F.data.startswith('show_report_'))
async def show_attendance_report(callback: CallbackQuery):
    group_id = int(callback.data.split('_')[2])
    report_data = await rq.get_attendance_report(group_id)
    
    await callback.message.answer(
        f"Страница {report_data['current_page']}:\n{formatters.format_attendance_table(report_data)}",
        parse_mode="MarkdownV2",
        reply_markup=kb.dates_pagination(
            group_id=group_id,
            current_page=report_data['current_page'],
            total_pages=report_data['total_pages']
        )
    )
    await callback.answer()

@router.callback_query(F.data.startswith('dates_page_'))
async def handle_dates_pagination(callback: CallbackQuery):
    _,_, group_id, page = callback.data.split('_')
    report_data = await rq.get_attendance_report(int(group_id), int(page))
    
    if int(page) > report_data['total_pages']:
        await callback.answer("Текущая страница — максимальная")
        return
    
    await callback.message.edit_text(
        f"Страница {report_data['current_page']}:\n{formatters.format_attendance_table(report_data)}",
        parse_mode="MarkdownV2",
        reply_markup=kb.dates_pagination(
            group_id=int(group_id),
            current_page=int(page),
            total_pages=report_data['total_pages']
        )
    )
    await callback.answer()

@router.callback_query(F.data.startswith('refresh_report_'))
async def refresh_report(callback: CallbackQuery):
    group_id = int(callback.data.split('_')[2])
    # Повторная загрузка данных
    await show_attendance_report(callback)

@router.callback_query(F.data.startswith('export_excel_'))
async def export_excel_handler(callback: CallbackQuery):
    try:
        group_id = int(callback.data.split('_')[2])
        
        # Проверка прав доступа
        teacher = await rq.get_teacher(callback.from_user.id)
        if not await rq.check_group_owner(group_id, teacher.id):
            return await callback.answer("⛔ Нет доступа!")
        
        # Генерация Excel-файла
        filename, excel_buffer = await rq.export_to_excel(group_id)
        
        # Отправка файла
        await callback.message.answer_document(
            document=BufferedInputFile(
                excel_buffer.getvalue(),
                filename=filename
            ),
            caption=f"📊 Отчет группы {filename.split('_')[0]}"
        )
        await callback.answer()
        
    except Exception as e:
        await callback.answer(f"Ошибка экспорта: {str(e)}")