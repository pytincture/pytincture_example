from pytincture.dataclass import backend_for_frontend

@backend_for_frontend
class py_ui_data:
    def dataset(self):
        return open("dataset.json", "r").read()
    