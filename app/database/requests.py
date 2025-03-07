from datetime import date
from app.database.models import async_session
from app.database.models import Teacher, Group, Student, Attendance
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload


from openpyxl import Workbook
from io import BytesIO


async def set_teacher(tg_id):
    async with async_session() as session:
        teacher = await session.scalar(select(Teacher).where(Teacher.tg_id == tg_id))

        if not teacher:
            session.add(Teacher(tg_id = tg_id))
            await session.commit()

async def get_teacher(tg_id):
    async with async_session() as session:
        teacher = await session.scalar(select(Teacher).where(Teacher.tg_id == tg_id))
        return teacher

async def create_group(name, teacher_id):
    async with async_session() as session:
        session.add(Group(name = name, teacher_id = teacher_id))
        await session.commit()
    
async def get_groups(teacher_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(Group).where(Group.teacher_id == teacher_id)
        )
        return result.scalars().all()

async def get_group_by_id(group_id: int) -> Group:
    async with async_session() as session:
        return await session.get(Group, group_id)

async def check_group_owner(group_id: int, teacher_id: int) -> bool:
    async with async_session() as session:
        group = await session.get(Group, group_id)
        return group.teacher_id == teacher_id if group else False
    
    
async def add_students(list_students, id_group):
    async with async_session() as session:
        for student in list_students:
            session.add(Student(name = student, group_id = id_group))
            await session.commit()

async def get_students(group_id):
    async with async_session() as session:
        return await session.scalars(select(Student).where(Student.group == group_id))
    
async def delete_group(group_id: int):
    async with async_session() as session:
        async with session.begin():
            group = await session.get(Group, group_id)
            if group:
                await session.delete(group)
            await session.commit()

async def get_students_by_group(group_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(Student).where(Student.group_id == group_id)
        )
        return result.scalars().all()

async def create_attendance_records(group_id: int, lesson_date: date):
    async with async_session() as session:
        students = await get_students_by_group(group_id)
        async with session.begin():
            for student in students:
                if not await session.execute(
                    select(Attendance).where(
                        (Attendance.student_id == student.id) &
                        (Attendance.lesson_date == lesson_date)
                    )):
                    session.add(Attendance(
                        student_id=student.id,
                        lesson_date=lesson_date,
                        status="unmarked"
                    ))
            await session.commit()

async def update_attendance(student_id: int, lesson_date: date, status: str):
    async with async_session() as session:
        async with session.begin():
            attendance = await session.execute(
                select(Attendance).where(
                    (Attendance.student_id == student_id) &
                    (Attendance.lesson_date == lesson_date)
                ))
            attendance = attendance.scalar()
            if attendance:
                attendance.status = status
            await session.commit()

async def get_attendance_status(student_id: int, lesson_date: date):
    async with async_session() as session:
        result = await session.execute(
            select(Attendance.status).where(
                (Attendance.student_id == student_id) &
                (Attendance.lesson_date == lesson_date)
            )
        )
        return result.scalar()
    
async def update_attendance(student_id: int, lesson_date: date, status: str):
    async with async_session() as session:
        async with session.begin():
            # Пытаемся найти существующую запись
            attendance = await session.scalar(
                select(Attendance).where(
                    (Attendance.student_id == student_id) &
                    (Attendance.lesson_date == lesson_date)
                )
            )
            
            if not attendance:
                # Если записи нет - создаем новую
                attendance = Attendance(
                    student_id=student_id,
                    lesson_date=lesson_date,
                    status=status
                )
                session.add(attendance)
            else:
                # Если запись есть - обновляем статус
                attendance.status = status
                
            await session.commit()

async def get_attendance_report(group_id: int, page: int = 1, dates_per_page: int = 6) -> dict:
    async with async_session() as session:
        # Получаем все уникальные даты для группы
        dates_result = await session.execute(
            select(Attendance.lesson_date)
            .join(Student)
            .where(Student.group_id == group_id)
            .distinct()
            .order_by(Attendance.lesson_date)
        )
        all_dates = [date[0] for date in dates_result.all()]
        
        # Пагинация дат
        total_pages = (len(all_dates) + dates_per_page - 1) // dates_per_page
        start_idx = (page - 1) * dates_per_page
        current_dates = all_dates[start_idx:start_idx + dates_per_page]

        # Исправленный запрос студентов
        students_result = await session.execute(
            select(Student)
            .where(Student.group_id == group_id)
            .options(joinedload(Student.attendances))
            .execution_options(populate_existing=True)
        )
        students = students_result.unique().scalars().all()

        # Формируем отчет
        report = []
        for student in students:
            student_data = {"name": student.name}
            
            # Заполняем данные по текущим датам
            for date in current_dates:
                status = next(
                    (attendance.status 
                     for attendance in student.attendances 
                     if attendance.lesson_date == date),
                    "—"
                )
                student_data[date] = status
            
            # Расчет итоговых показателей
            total_marks = []
            absences = 0
            illnesses = 0
            for attendance in student.attendances:
                if attendance.status.isdigit() and 2 <= int(attendance.status) <= 5:
                    total_marks.append(int(attendance.status))
                elif attendance.status == "не тут":
                    absences += 1
                elif attendance.status == "болеет":
                    illnesses += 1
            
            student_data["Итог"] = round(sum(total_marks)/len(total_marks), 1) if total_marks else "—"
            student_data["Пропуски"] = absences
            student_data["Болезни"] = illnesses
            
            report.append(student_data)
        
        return {
            "dates": current_dates,
            "students": report,
            "total_pages": total_pages,
            "current_page": page,
            "group_name": (await session.get(Group, group_id)).name
        }
    
async def export_to_excel(group_id: int) -> tuple[str, BytesIO]:
    report_data = await get_attendance_report(group_id)
    group = await get_group_by_id(group_id)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Посещаемость"

    # Заголовки
    headers = ["Студент"] + [d.strftime("%d.%m.%Y") for d in report_data['dates']] + ["Итог", "Пропуски", "Болезни"]
    ws.append(headers)

    for student in report_data['students']:
        row = [student['name']]
        absences = 0
        illnesses = 0
        total_marks = []
        
        # Собираем данные по датам
        for date in report_data['dates']:
            status = student.get(date, "—")
            row.append(status)
            
            # Подсчет показателей
            if status == 'не тут':
                absences += 1
            elif status == 'болеет':
                illnesses += 1
            elif isinstance(status, str) and status.isdigit() and 2 <= int(status) <= 5:
                total_marks.append(int(status))
        
        # Расчет среднего балла
        avg = sum(total_marks) / len(total_marks) if total_marks else "—"
        avg = round(avg, 1) if isinstance(avg, float) else avg
        
        # Добавляем итоговые колонки
        row.extend([avg, absences, illnesses])
        ws.append(row)
    
    # Сохраняем файл
    excel_buffer = BytesIO()
    wb.save(excel_buffer)
    excel_buffer.seek(0)
    
    filename = f"{group.name}_посещаемость_{date.today().strftime('%Y-%m-%d')}.xlsx"
    return filename, excel_buffer