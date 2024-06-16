from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

def parse_proxy(proxy_str):
    # Try different proxy formats
    if '@' in proxy_str:
        # login:password@hostname:port or hostname:port@login:password
        parts = proxy_str.split('@')
        credentials, host_port = parts if ':' in parts[0] else parts[::-1]
        login, password = credentials.split(':')
        hostname, port = host_port.split(':')
    elif proxy_str.count(':') == 3:
        # login:password:hostname:port
        login, password, hostname, port = proxy_str.split(':')
    elif proxy_str.count(':') == 1:
        # hostname:port
        hostname, port = proxy_str.split(':')
        login, password = None, None
    else:
        raise ValueError('Invalid proxy format')
    
    proxy_url = f"http://{hostname}:{port}"
    if login and password:
        proxy_url = f"http://{login}:{password}@{hostname}:{port}"
    
    return {"http": proxy_url, "https": proxy_url}

@app.route('/proxy', methods=['POST'])
def use_proxy():
    data = request.json
    proxy_str = data.get('proxy')

    try:
        proxies = parse_proxy(proxy_str)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # First request
    try:
        post_response = requests.post('https://pixelscan.net/s/api/ci', proxies=proxies)
        post_response.raise_for_status()
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

    # Second request
    try:
        get_response = requests.get('http://ipinfo.io/json/', proxies=proxies)
        get_response.raise_for_status()
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500
    
    # try:
    #     ipqs = requests.get('http://127.0.0.1:5005/check_ip', proxies=proxies)
    #     ipqs.raise_for_status()
    # except requests.RequestException as e:
    #     return jsonify({"error": str(e)}), 500

    return jsonify({
        "pixelscan_response": post_response.json(),
        "ip_api_response": get_response.json(),
        # "ipqs_response": ipqs.json()
    })

if __name__ == '__main__':
    app.run(debug=True)
