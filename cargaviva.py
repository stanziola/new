import tkinter as tk
from tkinter import ttk

# ASCE 7-05, Tabla 4-1: cargas vivas mínimas uniformes y concentradas
# Sec. 4.3: se diseña para la uniforme o la concentrada, la que produzca mayores efectos.
# Salvo que se indique otra, la concentrada actúa sobre 0.58 m2 (762 mm de lado).
AREA_CONC_DEFECTO = 0.58  # m2

FILAS = []


def r(nombre, psf=None, kn=None, lb=None, kn_c=None, detalle=""):
    FILAS.append({
        "nombre": nombre, "q_psf": psf, "q": kn,
        "P_lb": lb, "P": kn_c, "detalle": detalle,
    })


NOTA_A = ("Alternativa concentrada: 3,000 lb (13.35 kN) sobre 114 mm x 114 mm (huella de gato) para "
          "garajes de hasta 9 pasajeros; o 2,250 lb (10 kN) por rueda en estacionamientos mecánicos "
          "sin losa, solo autos.")
NOTA_D = ("Además de la carga vertical, se aplican fuerzas horizontales de balanceo: 24 lb/ft (0.35 kN/m) "
          "paralela a la fila y 10 lb/ft (0.15 kN/m) perpendicular, no simultáneas.")

r("Sistemas de piso elevado: uso oficina", 50, 2.40, 2000, 8.90)
r("Sistemas de piso elevado: uso computadoras", 100, 4.79, 2000, 8.90)
r("Armerías y salones de entrenamiento", 150, 7.18)
r("Áreas de reunión y teatros: asientos fijos (fijados al piso)", 60, 2.87)
r("Áreas de reunión y teatros: vestíbulos", 100, 4.79)
r("Áreas de reunión y teatros: asientos móviles", 100, 4.79)
r("Áreas de reunión y teatros: plataformas", 100, 4.79)
r("Áreas de reunión y teatros: pisos de escenario", 150, 7.18)
r("Balcones (exteriores)", 100, 4.79)
r("Balcones: solo viviendas uni y bifamiliares, hasta 100 ft2 (9.3 m2)", 60, 2.87)
r("Boleras, salas de billar y áreas recreativas similares", 75, 3.59)
r("Pasarelas de mantenimiento (catwalks)", 40, 1.92, 300, 1.33)
r("Corredores: primer piso", 100, 4.79)
r("Corredores: otros pisos",
  detalle="Igual que la ocupación servida, salvo lo indicado. Sin valor propio en la tabla.")
r("Salones de baile", 100, 4.79)
r("Terrazas y techos tipo deck (patio y techo)",
  detalle="Igual que el área servida o el tipo de ocupación. Sin valor propio en la tabla.")
r("Comedores y restaurantes", 100, 4.79)
r("Rejilla de cuarto de máquinas de ascensor", None, None, 300, 1.33,
  "Concentrada sobre un área de 4 in2 (2,580 mm2).")
r("Placa de piso liviano (finish light floor plate)", None, None, 200, 0.89,
  "Concentrada sobre un área de 1 in2 (645 mm2).")
r("Escaleras de incendio", 100, 4.79)
r("Escaleras de incendio: solo vivienda unifamiliar", 40, 1.92)
r("Escaleras fijas (fixed ladders)", detalle="Ver Sección 4.4. Sin valor en la tabla.")
r("Garajes: solo vehículos de pasajeros", 40, 1.92, 3000, 13.35, NOTA_A)
r("Garajes: camiones y buses", 40, 1.92,
  detalle="Se diseña con un método aprobado que contenga cargas de camiones y buses.")
r("Gimnasios: pisos principales y balcones", 100, 4.79)
r("Pasamanos, barandas y barras de apoyo", detalle="Ver Sección 4.4. Sin valor en la tabla.")
r("Hospitales: salas de operación y laboratorios", 60, 2.87, 1000, 4.45)
r("Hospitales: habitaciones de pacientes", 40, 1.92, 1000, 4.45)
r("Hospitales: corredores sobre el primer piso", 80, 3.83, 1000, 4.45)
r("Bibliotecas: salas de lectura", 60, 2.87, 1000, 4.45)
r("Bibliotecas: salas de estantería (stack rooms)", 150, 7.18, 1000, 4.45,
  "Aplica a estantes dobles no móviles con: altura nominal de unidad <= 90 in (2,290 mm); "
  "profundidad nominal de estante <= 12 in (305 mm) por cara; pasillos entre filas >= 36 in (914 mm).")
r("Bibliotecas: corredores sobre el primer piso", 80, 3.83, 1000, 4.45)
r("Manufactura: liviana", 125, 6.00, 2000, 8.90)
r("Manufactura: pesada", 250, 11.97, 3000, 13.40)
r("Marquesinas", 75, 3.59)
r("Oficinas: salas de archivo y computadoras",
  detalle="Se diseñan para cargas mayores según la ocupación prevista. Sin valor propio en la tabla.")
r("Oficinas: vestíbulos y corredores del primer piso", 100, 4.79, 2000, 8.90)
r("Oficinas: oficinas", 50, 2.40, 2000, 8.90)
r("Oficinas: corredores sobre el primer piso", 80, 3.83, 2000, 8.90)
r("Instituciones penales: bloques de celdas", 40, 1.92)
r("Instituciones penales: corredores", 100, 4.79)
r("Residencial, viviendas uni y bifamiliares: áticos no habitables sin almacenamiento", 10, 0.48)
r("Residencial, viviendas uni y bifamiliares: áticos no habitables con almacenamiento", 20, 0.96)
r("Residencial, viviendas uni y bifamiliares: áticos habitables y dormitorios", 30, 1.44)
r("Residencial, viviendas uni y bifamiliares: todas las demás áreas excepto escaleras y balcones", 40, 1.92)
r("Residencial, hoteles y multifamiliares: habitaciones privadas y corredores que las sirven", 40, 1.92)
r("Residencial, hoteles y multifamiliares: salas públicas y corredores que las sirven", 100, 4.79)
r("Tribunas de revista, graderías y bleachers", 100, 4.79, detalle=NOTA_D)
r("Techos: planos, inclinados y curvos ordinarios", 20, 0.96,
  detalle="Si la carga viva reducida es menor a 20 psf (0.96 kN/m2) según 4.9.1 y se aplica a miembros "
          "continuos, la carga reducida va en tramos adyacentes o alternos, el caso más desfavorable.")
r("Techos: usados para paseo", 60, 2.87)
r("Techos: jardines o áreas de reunión", 100, 4.79)
r("Techos: otros fines especiales",
  detalle="Cargas apropiadas según la autoridad competente. Sin valor en la tabla.")
r("Toldos y marquesinas: tela sobre estructura rígida liviana", 5, 0.24, detalle="No reducible.")
r("Toldos y marquesinas: toda otra construcción", 20, 0.96)
r("Miembros primarios de techo expuestos a piso de trabajo: cuerda inferior de cerchas o miembros que "
  "soportan techos sobre manufactura, almacenes y talleres de reparación", None, None, 2000, 8.90,
  "Concentrada en un solo nudo del panel inferior o en cualquier punto del miembro primario.")
r("Miembros primarios de techo expuestos a piso de trabajo: otras ocupaciones", None, None, 300, 1.33)
r("Superficies de techo sujetas a trabajadores de mantenimiento", None, None, 300, 1.33)
r("Escuelas: aulas", 40, 1.92, 1000, 4.45)
r("Escuelas: corredores sobre el primer piso", 80, 3.83, 1000, 4.45)
r("Escuelas: corredores del primer piso", 100, 4.79, 1000, 4.45)
r("Tragaluces, nervios de claraboya y cielos accesibles", None, None, 200, 0.89)
r("Aceras, accesos vehiculares y patios con tránsito de camiones", 250, 11.97, 8000, 35.60,
  "Concentrada de rueda sobre 114 mm x 114 mm (huella de gato). También considerar otras cargas "
  "uniformes según un método aprobado con cargas de camiones.")
r("Estadios y arenas: graderías (bleachers)", 100, 4.79, detalle=NOTA_D)
r("Estadios y arenas: asientos fijos (fijados al piso)", 60, 2.87, detalle=NOTA_D)
r("Escaleras y salidas", 100, 4.79, 300, 1.33,
  "Concentrada mínima en peldaños: 300 lb (1.33 kN) sobre un área de 4 in2 (2,580 mm2).")
r("Escaleras y salidas: solo viviendas uni y bifamiliares", 40, 1.92)
r("Áreas de almacenamiento sobre cielos", 20, 0.96)
r("Almacenes: livianos", 125, 6.00, detalle="Se diseñan para cargas mayores si el almacenamiento previsto lo requiere.")
r("Almacenes: pesados", 250, 11.97, detalle="Se diseñan para cargas mayores si el almacenamiento previsto lo requiere.")
r("Tiendas, minoristas: primer piso", 100, 4.79, 1000, 4.45)
r("Tiendas, minoristas: pisos superiores", 75, 3.59, 1000, 4.45)
r("Tiendas, mayoristas: todos los pisos", 125, 6.00, 1000, 4.45)
r("Barreras vehiculares", detalle="Ver Sección 4.4. Sin valor en la tabla.")
r("Pasarelas y plataformas elevadas (excepto vías de salida)", 60, 2.87)
r("Patios y terrazas peatonales", 100, 4.79)


def verificar(area_m2, fila):
    """Compara la carga uniforme total sobre el área contra la concentrada mínima.

    Verificación simplificada por carga total: q*A vs P. Si P > q*A, la concentrada
    puede controlar. La verificación exacta se hace con efectos (M, V) y la luz del elemento.
    """
    q, P = fila["q"], fila["P"]
    if q is None and P is None:
        return {"estado": "sin_valor"}
    W = q * area_m2 if q is not None else None
    if q is None:
        controla = "concentrada"
    elif P is None:
        controla = "uniforme"
    else:
        controla = "concentrada" if P > W else "uniforme"
    area_limite = P / q if (q and P) else None
    return {"estado": "ok", "q": q, "P": P, "W": W,
            "controla": controla, "area_limite": area_limite}


def texto_resultado(area, fila):
    v = verificar(area, fila)
    if v["estado"] == "sin_valor":
        return "Sin valor numérico en la Tabla 4-1", "gray"
    partes = []
    if v["q"] is not None:
        partes.append(f"Uniforme: {v['q']:.2f} kN/m² x {area:g} m² = {v['W']:.2f} kN")
    else:
        partes.append("Uniforme: no definida")
    if v["P"] is not None:
        partes.append(f"Concentrada mínima: P = {v['P']:.2f} kN")
    else:
        partes.append("Concentrada: no definida")
    if v["controla"] == "concentrada":
        veredicto = "CONTROLA LA CONCENTRADA"
        if v["W"] is not None:
            veredicto += f" (P > q·A)"
        color = "#c62828"
    else:
        veredicto = "CONTROLA LA UNIFORME"
        if v["P"] is not None:
            veredicto += " (P ≤ q·A)"
        color = "#2e7d32"
    texto = "\n".join(partes) + "\n" + veredicto
    if v["area_limite"] is not None:
        texto += f"\nÁrea límite P/q = {v['area_limite']:.2f} m² (con menos área que ésta, P > q·A)"
    return texto, color


def main():
    root = tk.Tk()
    root.title("ASCE 7-05, Tabla 4-1: Cargas vivas mínimas")
    root.geometry("1500x820")

    style = ttk.Style()
    style.configure("Treeview", font=("Segoe UI", 11), rowheight=28)
    style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"))

    top = ttk.Frame(root)
    top.pack(fill="x", padx=10, pady=8)
    ttk.Label(top, text="Área (m²):", font=("Segoe UI", 12, "bold")).pack(side="left")
    area_var = tk.StringVar(value="10")
    ttk.Entry(top, textvariable=area_var, width=10, font=("Segoe UI", 12)).pack(side="left", padx=8)
    ttk.Label(top, text="La concentrada actúa sobre 0.58 m² (762 mm de lado) salvo que el detalle indique otra área.",
              font=("Segoe UI", 10)).pack(side="left", padx=15)

    frame = ttk.Frame(root)
    frame.pack(fill="both", expand=True, padx=10)

    cols = ("uso", "unif", "conc", "detalle")
    tree = ttk.Treeview(frame, columns=cols, show="headings", selectmode="browse")
    tree.heading("uso", text="Ocupación o uso")
    tree.heading("unif", text="Uniforme psf (kN/m²)")
    tree.heading("conc", text="Conc. lb (kN)")
    tree.heading("detalle", text="Detalle")
    tree.column("uso", width=620, anchor="w")
    tree.column("unif", width=150, anchor="center")
    tree.column("conc", width=140, anchor="center")
    tree.column("detalle", width=1800, anchor="w")
    tree.tag_configure("sinvalor", foreground="gray")

    for i, f in enumerate(FILAS):
        unif = f"{f['q_psf']:g} ({f['q']:.2f})" if f["q"] is not None else ""
        conc = f"{f['P_lb']:,} ({f['P']:.2f})" if f["P"] is not None else ""
        tag = "sinvalor" if f["q"] is None and f["P"] is None else ""
        tree.insert("", "end", iid=str(i),
                    values=(f["nombre"], unif, conc, f["detalle"]), tags=(tag,))

    sy = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    sx = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
    tree.grid(row=0, column=0, sticky="nsew")
    sy.grid(row=0, column=1, sticky="ns")
    sx.grid(row=1, column=0, sticky="ew")
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)

    titulo = tk.StringVar(value="Selecciona un tipo de uso")
    resultado = tk.StringVar()
    detalle = tk.StringVar()
    ttk.Label(root, textvariable=titulo, font=("Segoe UI", 12, "bold"),
              wraplength=1400, justify="center").pack(pady=(8, 0))
    lbl = tk.Label(root, textvariable=resultado, font=("Segoe UI", 15, "bold"), justify="center")
    lbl.pack(pady=4)
    ttk.Label(root, textvariable=detalle, font=("Segoe UI", 10),
              wraplength=1400, justify="center").pack(pady=(0, 8))

    def actualizar(*_):
        sel = tree.selection()
        if not sel:
            return
        fila = FILAS[int(sel[0])]
        titulo.set(fila["nombre"])
        detalle.set(fila["detalle"])
        try:
            area = float(area_var.get().replace(",", "."))
            if area <= 0:
                raise ValueError
        except ValueError:
            resultado.set("Ingresa un área válida (m²)")
            lbl.config(fg="gray")
            return
        texto, color = texto_resultado(area, fila)
        resultado.set(texto)
        lbl.config(fg=color)

    tree.bind("<<TreeviewSelect>>", actualizar)
    area_var.trace_add("write", actualizar)
    root.mainloop()

if __name__ == "__main__":
    main()