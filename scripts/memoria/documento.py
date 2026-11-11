"""La clase Memoria: el documento de Word y las piezas con que se escribe cada capítulo.

Cada capítulo (scripts/memoria/capitulos/*.py) es una función que recibe la Memoria y le va
pidiendo piezas, en el orden en que deben aparecer:

    m.titulo("Matriz de rigidez local", nivel=2)        título numerado (entra al índice)
    m.parrafo("La barra tiene **12 GDL** y su eje es $x$.")   texto: **negrita**, `código`, $fórmula$
    m.lista(["uno", "dos"])                             viñetas
    m.ecuacion(r"K = T^{\\mathsf{T}} k T", cita="…")     ecuación de Word, con su cita debajo
    m.tabla(["a", "b"], [["1", "2"]])                   tabla
    m.matriz(etiquetas, celdas)                         matriz grande, como tabla de fórmulas
    m.codigo(funcion)                                   el código vigente de una función (sin comentarios)
    m.figura(fig, "pie")                                una figura de matplotlib
    m.nota("…")                                       aviso (limitaciones, hallazgos pendientes)

Así el contenido se lee de corrido en el capítulo y todo el formato (A4, Arial 11, títulos
numerados, como el documento de referencia del proyecto) vive aquí, en un solo lugar.
El documento se arma con python-docx; las ecuaciones, con ecuaciones.py.
"""
import ast
import inspect
import io
import re
import textwrap
import tokenize
from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Mm, Pt, RGBColor

from scripts.memoria.ecuaciones import omml, omml_centrada

RAIZ = Path(__file__).resolve().parents[2]

FUENTE = "Arial"
FUENTE_CODIGO = "Consolas"
TAMANO = 11                          # del texto, en puntos
MARGEN_CM = 2.54
ANCHO_UTIL_CM = 21.0 - 2 * MARGEN_CM   # A4 menos los márgenes
GRIS = RGBColor(0x59, 0x59, 0x59)
FONDO_CODIGO = "F2F2F2"
FONDO_ENCABEZADO = "D9D9D9"
ANCHO_CONSOLAS = 0.55                # ancho de una letra de Consolas, en veces su tamaño
TAMANO_CODIGO = 8.5                  # el normal; un listado con renglones largos baja hasta el mínimo
TAMANO_CODIGO_MINIMO = 5.0

# Texto con marcas: $fórmula$, **negrita** (puede llevar fórmulas adentro), *cursiva* y `código`
MARCAS = re.compile(r"(\$[^$]+\$|\*\*.+?\*\*|\*[^*]+\*|`[^`]+`)")
EXPONENTES = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")
LINEAS_SIN_PARTIR = 40               # un listado hasta de este largo no se parte entre dos páginas


def _fuente(estilo, nombre, tamano=None, negrita=None, color=None, cursiva=None):
    """Pone la fuente de un estilo. Los estilos de la plantilla traen fuentes "del tema" (Calibri),
    que mandan sobre el nombre: hay que quitarlas para que valga el nuestro."""
    estilo.font.name = nombre
    rfonts = estilo.element.get_or_add_rPr().get_or_add_rFonts()
    for atributo in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
        if rfonts.get(qn(f"w:{atributo}")) is not None:
            del rfonts.attrib[qn(f"w:{atributo}")]
    for atributo in ("eastAsia", "cs"):
        rfonts.set(qn(f"w:{atributo}"), nombre)
    if tamano is not None:
        estilo.font.size = Pt(tamano)
    if negrita is not None:
        estilo.font.bold = negrita
    if cursiva is not None:
        estilo.font.italic = cursiva
    if color is not None:
        estilo.font.color.rgb = color


def _sombrear(celda, color):
    """Fondo de una celda de tabla."""
    sombra = OxmlElement("w:shd")
    sombra.set(qn("w:val"), "clear")
    sombra.set(qn("w:color"), "auto")
    sombra.set(qn("w:fill"), color)
    celda._tc.get_or_add_tcPr().append(sombra)


def _campo(parrafo, instruccion, texto=""):
    """Un campo de Word (el índice, el número de página): Word lo calcula al actualizarlo."""
    def marca(tipo):
        m = OxmlElement("w:fldChar")
        m.set(qn("w:fldCharType"), tipo)
        return m

    codigo = OxmlElement("w:instrText")
    codigo.set(qn("xml:space"), "preserve")
    codigo.text = instruccion
    r = parrafo.add_run()._r
    r.append(marca("begin"))
    r.append(codigo)
    r.append(marca("separate"))
    if texto:
        t = OxmlElement("w:t")
        t.text = texto
        r.append(t)
    r.append(marca("end"))


def _limpiar(fuente):
    """El código sin docstrings ni comentarios, y sin renglones en blanco seguidos. Los docstrings se
    encuentran con ast (el árbol del código) y los comentarios con tokenize (sus piezas), así no se
    confunde un # dentro de un texto con un comentario."""
    lineas = fuente.splitlines()
    borrar = set()                                     # renglones que se quitan enteros
    for nodo in ast.walk(ast.parse(fuente)):
        cuerpo = getattr(nodo, "body", None)
        if (isinstance(cuerpo, list) and cuerpo and isinstance(cuerpo[0], ast.Expr)
                and isinstance(cuerpo[0].value, ast.Constant) and isinstance(cuerpo[0].value.value, str)):
            borrar.update(range(cuerpo[0].lineno - 1, cuerpo[0].end_lineno))
    cortes = {}                                        # renglón -> columna donde empieza su comentario
    for pieza in tokenize.generate_tokens(io.StringIO(fuente).readline):
        if pieza.type == tokenize.COMMENT:
            cortes[pieza.start[0] - 1] = pieza.start[1]
    limpias = []
    for k, linea in enumerate(lineas):
        if k in borrar:
            continue
        if k in cortes:
            linea = linea[:cortes[k]].rstrip()
            if not linea.strip():
                continue                               # era solo un comentario
        if not linea.strip() and (not limpias or not limpias[-1].strip()):
            continue                                   # un solo renglón en blanco seguido
        limpias.append(linea)
    return "\n".join(limpias).strip("\n")


def numero(valor, cifras=4):
    """Un número para el documento: con `cifras` significativas, el signo menos de imprenta y los
    exponentes como potencias de 10 (1.2·10⁻¹⁶ en vez de 1.2e-16)."""
    if valor == 0:
        return "0"
    texto = f"{valor:.{cifras}g}"
    if "e" in texto:
        base, exponente = texto.split("e")
        texto = f"{base}·10{str(int(exponente)).translate(EXPONENTES)}"
    return texto.replace("-", "−")


class Memoria:
    def __init__(self):
        self.doc = Document()
        self._numeros = [0, 0, 0]          # numeración de los títulos: capítulo, sección, subsección
        self._figuras = 0
        self._pagina()
        self._estilos()

    # ---------- Formato ----------
    def _pagina(self):
        """A4 con márgenes de 2.54 cm y el número de página al pie (la portada no lo lleva)."""
        seccion = self.doc.sections[0]
        seccion.page_width, seccion.page_height = Mm(210), Mm(297)
        for lado in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
            setattr(seccion, lado, Cm(MARGEN_CM))
        seccion.different_first_page_header_footer = True
        pie = seccion.footer.paragraphs[0]
        pie.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _campo(pie, "PAGE", "1")
        for run in pie.runs:
            run.font.size = Pt(9)

    def _estilos(self):
        estilos = self.doc.styles
        normal = estilos["Normal"]
        _fuente(normal, FUENTE, TAMANO)
        normal.paragraph_format.line_spacing = 1.15
        normal.paragraph_format.space_after = Pt(6)
        for nombre, tamano, antes, despues in (("Heading 1", 16, 0, 10), ("Heading 2", 13, 14, 6),
                                               ("Heading 3", 11.5, 10, 4)):
            _fuente(estilos[nombre], FUENTE, tamano, negrita=True, color=RGBColor(0, 0, 0))
            formato = estilos[nombre].paragraph_format
            formato.space_before, formato.space_after = Pt(antes), Pt(despues)
            formato.keep_with_next = True
        for nombre in ("List Bullet", "Caption"):
            _fuente(estilos[nombre], FUENTE)

        def nuevo(nombre, fuente=FUENTE, tamano=TAMANO, **formato):
            estilo = estilos.add_style(nombre, WD_STYLE_TYPE.PARAGRAPH)
            estilo.base_style = normal
            _fuente(estilo, fuente, tamano, color=formato.pop("color", None), cursiva=formato.pop("cursiva", None))
            for clave, valor in formato.items():
                setattr(estilo.paragraph_format, clave, valor)
            return estilo

        nuevo("Cita", tamano=9, color=GRIS, alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(10))
        nuevo("Origen", tamano=8, color=GRIS, space_before=Pt(6), space_after=Pt(2), keep_with_next=True)
        nuevo("Codigo", fuente=FUENTE_CODIGO, tamano=TAMANO_CODIGO, line_spacing=1.0, space_after=Pt(0))
        nuevo("Pie", tamano=9, color=GRIS, alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(10))
        nuevo("Nota", tamano=10, cursiva=True, left_indent=Cm(0.6), space_before=Pt(4), space_after=Pt(8))
        nuevo("Celda", tamano=9, line_spacing=1.0, space_before=Pt(1.5), space_after=Pt(1.5))
        nuevo("Matriz", tamano=6.5, line_spacing=1.0, space_after=Pt(0), alignment=WD_ALIGN_PARAGRAPH.CENTER)

    # ---------- Texto ----------
    def _escribir(self, parrafo, texto, tamano=None, negrita=False, cursiva=False):
        """Escribe en el párrafo un texto con marcas: $fórmula$ (ecuación de Word dentro del renglón),
        **negrita**, *cursiva* y `código`. La negrita y la cursiva pueden llevar otras marcas adentro
        (por ejemplo una fórmula): por eso la función se llama a sí misma con lo de adentro."""
        for parte in MARCAS.split(texto):
            if not parte:
                continue
            if parte.startswith("$"):
                parrafo._p.append(omml(parte[1:-1]))
            elif parte.startswith("**"):
                self._escribir(parrafo, parte[2:-2], tamano, True, cursiva)
            elif parte.startswith("*"):
                self._escribir(parrafo, parte[1:-1], tamano, negrita, True)
            else:
                codigo = parte.startswith("`")
                run = parrafo.add_run(parte[1:-1] if codigo else parte)
                run.bold, run.italic = negrita or None, cursiva or None
                if codigo:
                    run.font.name = FUENTE_CODIGO
                    run.font.size = Pt((tamano or TAMANO) - 1)
                elif tamano is not None:
                    run.font.size = Pt(tamano)
        return parrafo

    def titulo(self, texto, nivel=1):
        """Título numerado ("2.", "2.1.", "2.1.1."). Cada capítulo (nivel 1) empieza página."""
        self._numeros[nivel - 1] += 1
        for k in range(nivel, len(self._numeros)):
            self._numeros[k] = 0
        numero_ = ".".join(str(n) for n in self._numeros[:nivel]) + "."
        parrafo = self.doc.add_heading(f"{numero_} {texto}", level=nivel)
        if nivel == 1:
            parrafo.paragraph_format.page_break_before = True
        return parrafo

    def parrafo(self, texto):
        return self._escribir(self.doc.add_paragraph(), texto)

    def lista(self, items):
        for item in items:
            self._escribir(self.doc.add_paragraph(style="List Bullet"), item)

    def nota(self, texto):
        """Un aviso: limitaciones, hallazgos pendientes, cosas a tener en cuenta."""
        return self._escribir(self.doc.add_paragraph(style="Nota"), texto)

    def ecuacion(self, latex, cita=None):
        """Una ecuación de Word en su propio renglón, centrada. `cita`: de dónde sale (norma, cláusula
        y página del PDF) o qué línea del programa la calcula; va debajo, en letra chica."""
        parrafo = self.doc.add_paragraph()
        parrafo.paragraph_format.space_before = Pt(4)
        parrafo.paragraph_format.space_after = Pt(2 if cita else 8)
        parrafo.paragraph_format.keep_with_next = bool(cita)
        parrafo._p.append(omml_centrada(latex))
        if cita:
            self._escribir(self.doc.add_paragraph(style="Cita"), cita, tamano=9)

    def salto(self):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    # ---------- Portada e índice ----------
    def portada(self, titulo, subtitulos, autor, datos):
        """Primera página: título, de qué trata, autor y los datos de esta versión."""
        def linea(texto, tamano, negrita=False, antes=0, color=None):
            p = self.doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(antes)
            run = p.add_run(texto)
            run.font.size, run.bold = Pt(tamano), negrita
            if color is not None:
                run.font.color.rgb = color

        linea(titulo, 30, negrita=True, antes=150)
        for k, texto in enumerate(subtitulos):
            linea(texto, 16 if k == 0 else 13, antes=10 if k == 0 else 2)
        linea(autor, 14, negrita=True, antes=110)
        for k, texto in enumerate(datos):
            linea(texto, 10, antes=24 if k == 0 else 0, color=GRIS)
        self.salto()

    def indice(self):
        """El índice es un campo de Word: lo llena Word (word.actualizar) con los títulos y sus páginas."""
        p = self.doc.add_paragraph()
        run = p.add_run("Índice")
        run.bold, run.font.size = True, Pt(16)
        p.paragraph_format.space_after = Pt(10)
        _campo(self.doc.add_paragraph(), r'TOC \o "1-3" \h \z \u',
               "Abre el documento en Word y actualiza este índice (clic derecho → Actualizar campo).")

    # ---------- Tablas ----------
    def _tabla(self, filas, columnas, anchos_cm=None):
        tabla = self.doc.add_table(rows=filas, cols=columnas)
        tabla.style = "Table Grid"
        tabla.alignment = WD_TABLE_ALIGNMENT.CENTER
        if anchos_cm is not None:
            tabla.autofit = False
            for fila in tabla.rows:
                for celda, ancho in zip(fila.cells, anchos_cm):
                    celda.width = Cm(ancho)
        return tabla

    def _despues_de_tabla(self):
        """Un poco de aire debajo de una tabla (Word no deja poner espacio en la tabla misma)."""
        p = self.doc.add_paragraph()
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 0.6

    def tabla(self, encabezados, filas, anchos_cm=None, tamano=9, centrar=()):
        """Tabla con encabezado sombreado. Las celdas aceptan las mismas marcas que parrafo().
        centrar: columnas (por número, desde 0) que van centradas."""
        tabla = self._tabla(len(filas) + 1, len(encabezados), anchos_cm)
        for k, texto in enumerate(encabezados):
            celda = tabla.rows[0].cells[k]
            _sombrear(celda, FONDO_ENCABEZADO)
            celda.paragraphs[0].style = "Celda"
            if k in centrar:
                celda.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            self._escribir(celda.paragraphs[0], texto, tamano, negrita=True)
        for i, fila in enumerate(filas, start=1):
            for k, texto in enumerate(fila):
                p = tabla.rows[i].cells[k].paragraphs[0]
                p.style = "Celda"
                if k in centrar:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                self._escribir(p, str(texto), tamano)
        self._despues_de_tabla()
        return tabla

    def matriz(self, etiquetas, celdas, esquina=""):
        """Una matriz grande (la 12×12) como tabla: cada celda es una fórmula corta en LaTeX y las
        celdas vacías son ceros. `etiquetas`: las de las filas y las columnas (en LaTeX)."""
        n = len(etiquetas)
        ancho = ANCHO_UTIL_CM / (n + 1)
        tabla = self._tabla(n + 1, n + 1, [ancho] * (n + 1))

        def poner(celda, latex, sombreada=False):
            p = celda.paragraphs[0]
            p.style = "Matriz"
            if sombreada:
                _sombrear(celda, FONDO_ENCABEZADO)
            if latex:
                p._p.append(omml(latex))

        poner(tabla.rows[0].cells[0], esquina, True)
        for k, etiqueta in enumerate(etiquetas, start=1):
            poner(tabla.rows[0].cells[k], etiqueta, True)
            poner(tabla.rows[k].cells[0], etiqueta, True)
        for i, fila in enumerate(celdas, start=1):
            for j, latex in enumerate(fila, start=1):
                poner(tabla.rows[i].cells[j], latex)
        self._despues_de_tabla()
        return tabla

    # ---------- Código y figuras ----------
    def codigo(self, objeto, origen=None, limpio=True):
        """El código de una función, una clase o un módulo, tal como está hoy en el programa
        (inspect.getsource lo lee del archivo), con el archivo de donde sale. También acepta un texto.
        limpio: sin docstrings ni comentarios (la explicación ya está en el texto del documento).
        Si algún renglón es muy largo, la letra se achica lo necesario para que quepa sin partirse."""
        if isinstance(objeto, str):
            fuente = objeto
        else:
            fuente = textwrap.dedent(inspect.getsource(objeto))
            if limpio:
                fuente = _limpiar(fuente)
            if origen is None:
                archivo = Path(inspect.getsourcefile(objeto)).resolve().relative_to(RAIZ).as_posix()
                nombre = getattr(objeto, "__qualname__", None)
                origen = f"{archivo} · {nombre}" if nombre and not inspect.ismodule(objeto) else archivo
        lineas = fuente.rstrip().expandtabs(4).splitlines()
        largo = max(len(linea) for linea in lineas)
        ancho_pt = (ANCHO_UTIL_CM - 0.5) / 2.54 * 72            # el de la celda, menos sus márgenes
        tamano = min(TAMANO_CODIGO, ancho_pt / (ANCHO_CONSOLAS * largo))
        tamano = max(TAMANO_CODIGO_MINIMO, int(tamano * 2) / 2)  # de medio en medio punto, hacia abajo
        if origen:
            self.doc.add_paragraph(origen, style="Origen")
        tabla = self._tabla(1, 1, [ANCHO_UTIL_CM])
        celda = tabla.rows[0].cells[0]
        _sombrear(celda, FONDO_CODIGO)
        if len(lineas) <= LINEAS_SIN_PARTIR:                    # un listado corto no se parte entre páginas
            tabla.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        for k, linea in enumerate(lineas):
            p = celda.paragraphs[0] if k == 0 else celda.add_paragraph()
            p.style = "Codigo"
            run = p.add_run(linea)
            run.font.size = Pt(tamano)
        self._despues_de_tabla()

    def figura(self, fig, pie, ancho_cm=13.5):
        """Una figura de matplotlib, centrada, con su pie numerado."""
        imagen = io.BytesIO()
        fig.savefig(imagen, format="png", dpi=200, bbox_inches="tight")
        imagen.seek(0)
        self.doc.add_picture(imagen, width=Cm(ancho_cm))
        self.doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        self.doc.paragraphs[-1].paragraph_format.keep_with_next = True
        self._figuras += 1
        self._escribir(self.doc.add_paragraph(style="Pie"), f"**Figura {self._figuras}.** {pie}", tamano=9)

    # ---------- Guardar ----------
    def guardar(self, ruta):
        ruta = Path(ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        self.doc.save(str(ruta))
        return ruta


def pedir_actualizacion_al_abrir(ruta):
    """Si Word no pudo actualizar el índice ahora, el documento queda marcado para que Word lo haga
    al abrirlo (pregunta si actualiza los campos: hay que decir que sí)."""
    doc = Document(str(ruta))
    ajustes = doc.settings.element
    marca = OxmlElement("w:updateFields")
    marca.set(qn("w:val"), "true")
    ajustes.append(marca)
    doc.save(str(ruta))
