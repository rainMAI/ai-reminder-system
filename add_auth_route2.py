with open('web_server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the line with @app.route('/web-reminder') and insert before it
insert_idx = None
for i, line in enumerate(lines):
    if "@app.route('/web-reminder')" in line:
        insert_idx = i
        break

if insert_idx:
    auth_route = '''# Static files - Auth page
@app.route("/static/auth.html")
def auth_page():
    """认证页面"""
    try:
        return send_from_directory("static", "auth.html")
    except FileNotFoundError:
        return "Auth page not found", 404

'''
    lines.insert(insert_idx, auth_route)
    
    with open('web_server.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("Auth route added successfully")
else:
    print("Could not find insertion point")
