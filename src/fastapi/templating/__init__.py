class Jinja2Templates:
    def __init__(self, directory: str):
        self.directory = directory

    def TemplateResponse(self, name: str, context: dict):
        return {'template': name, 'context': context}
