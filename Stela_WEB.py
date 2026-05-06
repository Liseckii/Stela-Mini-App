    # Сборка экрана БЕЗ ft.Center
    main_layout = ft.Column(
        controls=[
            # Сфера
            ft.Container(content=sphere, alignment=ft.alignment.center),
            ft.Container(height=10), # Отступ
            # Чат
            ft.Container(
                content=chat_log, 
                padding=10, 
                bgcolor="#111111", 
                border_radius=15, 
                width=350
            ),
            # Поле ввода
            ft.Container(
                content=ft.Row([
                    input_f, 
                    ft.IconButton(ft.icons.SEND, on_click=run_cmd, icon_color=accent)
                ]),
                width=350
            )
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER, # Центрируем всё по горизонтали
        alignment=ft.MainAxisAlignment.CENTER,            # Центрируем всё по вертикали
        expand=True
    )

    page.add(main_layout)
    page.update()
