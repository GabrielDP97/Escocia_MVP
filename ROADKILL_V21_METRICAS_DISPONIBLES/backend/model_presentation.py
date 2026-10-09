"""Nombres de modelos para los textos mostrados en la aplicación."""
import re


def model_names(value):
    if isinstance(value, dict):
        return {key: model_names(item) for key, item in value.items()}
    if isinstance(value, list):
        return [model_names(item) for item in value]
    if isinstance(value, str):
        value = re.sub(r'\bRetos?\s+5,\s*8\s+o\s+9\b', 'Random Forest, MLP y LSTM', value, flags=re.I)
        for number, name in [(5, 'Random Forest'), (8, 'MLP'), (9, 'LSTM'), (7, 'clasificación documental'), (6, 'K-Means')]:
            value = re.sub(r'\bReto\s*0?' + str(number) + r'\b', name, value, flags=re.I)
        value = value.replace('benchmark 05/08/09', 'benchmark de modelos')
        return value
    return value
