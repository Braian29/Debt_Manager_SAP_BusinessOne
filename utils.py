import locale

locale.setlocale(locale.LC_ALL, 'es_AR.utf8')

def format_number(value):
    if value is None:
       return ""
    try:
       return locale.format_string('%.2f', value, grouping=True)
    except ValueError:
        return str(value)