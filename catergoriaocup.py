import tkinter as tk
from tkinter import ttk

# ASCE 7-05, Tabla 1-1: (tipo de estructura, categoría, detalle)
TABLA_1_1 = [
    ("Instalaciones agrícolas", "I", ""),
    ("Ciertas instalaciones temporales", "I", ""),
    ("Instalaciones menores de almacenamiento", "I", ""),

    ("Todas las demás estructuras", "II",
     "Aplica a lo que no esté listado en las Categorías I, III y IV."),

    ("Estructuras donde se congregan más de 300 personas en un área", "III", ""),
    ("Guarderías con capacidad mayor a 150", "III", ""),
    ("Escuelas primarias o secundarias con capacidad mayor a 250", "III", ""),
    ("Universidades o educación de adultos con capacidad mayor a 500", "III", ""),
    ("Centros de salud con 50 o más pacientes residentes, sin cirugía ni emergencias", "III", ""),
    ("Cárceles y centros de detención", "III", ""),
    ("Plantas generadoras de energía", "III",
     "Potencial de impacto económico sustancial o interrupción masiva de la vida civil. "
     "Las plantas de cogeneración que no suministran a la red nacional son Categoría II."),
    ("Plantas de tratamiento de agua", "III",
     "Potencial de impacto económico sustancial o interrupción masiva de la vida civil (si no es Cat. IV)."),
    ("Plantas de tratamiento de aguas residuales", "III",
     "Potencial de impacto económico sustancial o interrupción masiva de la vida civil (si no es Cat. IV)."),
    ("Centros de telecomunicaciones", "III",
     "Potencial de impacto económico sustancial o interrupción masiva de la vida civil (si no es Cat. IV)."),
    ("Estructuras con cantidades de sustancias tóxicas o explosivas peligrosas para el público", "III",
     "Incluye instalaciones que fabrican, procesan, manejan, almacenan, usan o desechan combustibles, "
     "químicos o desechos peligrosos, o explosivos. Pueden ser Categoría II si una evaluación de peligro "
     "(Sec. 1.5.2) demuestra, a satisfacción de la autoridad competente, que una liberación no amenaza al público."),

    ("Hospitales y centros de salud con cirugía o atención de emergencias", "IV", ""),
    ("Bomberos, rescate, ambulancias, policía y garajes de vehículos de emergencia", "IV", ""),
    ("Refugios designados para sismo, huracán u otra emergencia", "IV", ""),
    ("Centros designados de preparación, comunicación y operación de emergencias", "IV", ""),
    ("Plantas generadoras y servicios públicos requeridos en una emergencia", "IV", ""),
    ("Estructuras auxiliares requeridas para operar estructuras IV en emergencia", "IV",
     "Ej.: torres de comunicación, tanques de combustible, torres de enfriamiento, subestaciones eléctricas, "
     "tanques de agua contra incendio."),
    ("Torres de control aéreo, centros de tráfico aéreo y hangares de emergencia", "IV", ""),
    ("Almacenamiento de agua y bombeo para presión contra incendio", "IV", ""),
    ("Estructuras con funciones críticas de defensa nacional", "IV", ""),
    ("Estructuras con sustancias altamente tóxicas sobre la cantidad umbral", "IV",
     "El umbral lo define la autoridad competente. Pueden ser Categoría II con evaluación de peligro "
     "(Sec. 1.5.2). No se permite la reducción si la estructura también funciona como instalación esencial."),
]

COLORES = {"I": "#e8f5e9", "II": "#e3f2fd", "III": "#fff3e0", "IV": "#ffebee"}


def main():
    root = tk.Tk()
    root.title("ASCE 7-05, Tabla 1-1: Categoría de ocupación")
    root.geometry("1500x700")

    style = ttk.Style()
    style.configure("Treeview", font=("Segoe UI", 11), rowheight=30)
    style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"))

    frame = ttk.Frame(root)
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    tree = ttk.Treeview(frame, columns=("tipo", "cat", "detalle"),
                        show="headings", selectmode="browse")
    tree.heading("tipo", text="Tipo de estructura")
    tree.heading("cat", text="Categoría")
    tree.heading("detalle", text="Detalle")
    tree.column("tipo", width=620, anchor="w")
    tree.column("cat", width=90, anchor="center")
    tree.column("detalle", width=1400, anchor="w")

    for cat, color in COLORES.items():
        tree.tag_configure(cat, background=color)

    for i, (tipo, cat, detalle) in enumerate(TABLA_1_1):
        tree.insert("", "end", iid=str(i), values=(tipo, cat, detalle), tags=(cat,))

    sy = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    sx = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
    tree.grid(row=0, column=0, sticky="nsew")
    sy.grid(row=0, column=1, sticky="ns")
    sx.grid(row=1, column=0, sticky="ew")
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)

    resultado = tk.StringVar(value="Selecciona una estructura")
    detalle_txt = tk.StringVar()

    ttk.Label(root, textvariable=resultado, font=("Segoe UI", 22, "bold")).pack(pady=(5, 0))
    ttk.Label(root, textvariable=detalle_txt, font=("Segoe UI", 11),
              wraplength=1400, justify="center").pack(pady=(0, 10))

    def al_seleccionar(_):
        sel = tree.selection()
        if not sel:
            return
        tipo, cat, detalle = TABLA_1_1[int(sel[0])]
        resultado.set(f"Categoría de ocupación {cat}")
        detalle_txt.set(f"{tipo}\n{detalle}" if detalle else tipo)

    tree.bind("<<TreeviewSelect>>", al_seleccionar)
    root.mainloop()


if __name__ == "__main__":
    main()