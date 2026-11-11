"""Lo que solo Word sabe hacer: llenar el índice (con sus números de página) y exportar a PDF.

El índice de un documento de Word es un "campo": Word lo calcula cuando lo actualiza, porque solo él
sabe en qué página cae cada título. El generador escribe el campo vacío y aquí se le pide a Word
(oculto, en una instancia aparte de la que tenga abierta el usuario) que lo actualice y guarde.
Usa pywin32 (win32com), que maneja Word como lo haría una macro.
"""
from pathlib import Path

PDF = 17                                   # wdExportFormatPDF


def actualizar(ruta, pdf=None):
    """Abre el .docx en Word, actualiza el índice y los campos, y guarda. Con `pdf`, exporta además
    a esa ruta. Devuelve None si salió bien, o el texto del problema (Word no está, archivo en uso…)."""
    try:
        import pythoncom
        import win32com.client
    except ImportError:
        return "falta pywin32 (pip install pywin32)"
    ruta = Path(ruta).resolve()
    pythoncom.CoInitialize()
    word = documento = None
    try:
        word = win32com.client.DispatchEx("Word.Application")     # instancia aparte, invisible
        word.Visible = False
        word.DisplayAlerts = 0
        documento = word.Documents.Open(str(ruta), ReadOnly=False, AddToRecentFiles=False)
        for indice in documento.TablesOfContents:
            indice.Update()
        documento.Fields.Update()
        documento.Save()
        if pdf is not None:
            documento.ExportAsFixedFormat(str(Path(pdf).resolve()), PDF)
        return None
    except Exception as e:                  # noqa: BLE001 (cualquier falla de Word se informa, no se propaga)
        return f"Word no pudo actualizar el documento: {e}"
    finally:
        if documento is not None:
            documento.Close(False)
        if word is not None:
            word.Quit()
        pythoncom.CoUninitialize()
