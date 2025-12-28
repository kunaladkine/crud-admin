from app import app as server

def handler(event, context):
    return server(event, context)
