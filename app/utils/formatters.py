def format_attendance_table(report_data: dict) -> str:
    dates = report_data['dates']
    students = report_data['students']
    
    # Рассчитываем ширину колонок
    max_name_len = max(len(student['name']) for student in students) if students else 10
    student_col = max(max_name_len, 10)  # Минимальная ширина для заголовка "Студент"
    date_col = 8    # Ширина для дат DD.MM
    total_col = 6   # Итог
    miss_col = 10   # Пропуски
    ill_col = 10    # Болезни

    # Создаем разделитель строк
    separator = (
        f"+{'-' * (student_col + 2)}" +
        f"+{'+'.join(['-' * (date_col + 2) for _ in dates])}" +
        f"+{'-' * (total_col + 2)}" +
        f"+{'-' * (miss_col + 2)}" +
        f"+{'-' * (ill_col + 2)}+"
    )

    # Формируем заголовок
    header = (
        f"| {'Студент'.ljust(student_col)} |" +
        "|".join([f" {d.strftime('%d.%m').center(date_col)} " for d in dates]) + "|" +
        f" {'Итог'.center(total_col)} |" +
        f" {'Пропуски'.center(miss_col)} |" +
        f" {'Болезни'.center(ill_col)} |"
    )

    # Собираем таблицу
    table = ["```", separator, header, separator]
    
    for student in students:
        # Формируем строку с данными
        name = student['name'].ljust(student_col)
        dates_cells = []
        
        for d in dates:
            status = str(student.get(d, "—"))
            dates_cells.append(f" {status.center(date_col)} ")
            
        total = str(student.get('Итог', '—')).center(total_col)
        misses = str(student.get('Пропуски', 0)).center(miss_col)
        ills = str(student.get('Болезни', 0)).center(ill_col)
        
        row = (
            f"| {name} |" +
            "|".join(dates_cells) + "|" +
            f" {total} |" +
            f" {misses} |" +
            f" {ills} |"
        )
        
        table.extend([row, separator])
    
    table.append("```")
    return "\n".join(table)