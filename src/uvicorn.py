def run(app: str, host: str='0.0.0.0', port: int=8000, reload: bool=False):
    print(f'uvicorn mock run {app} {host}:{port}')
