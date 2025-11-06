def response_ok(data: dict = None):
    return {"success": True, "data": data or {}, "error": None}

def response_error(code: int, message: str):
    return {"success": False, "data": None, "error": {"code": code, "message": message}}
