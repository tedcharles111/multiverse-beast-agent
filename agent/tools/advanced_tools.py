# agent/tools/advanced_tools.py
import os
import subprocess
import json
import time
import tempfile
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

def crawl_website(url: str) -> str:
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, 'lxml')
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text(separator='\n', strip=True)
        return text[:5000]
    except Exception as e:
        return f"Crawl failed: {str(e)}"

def screenshot_full_page(url: str, output_path: str = None) -> str:
    if not output_path:
        output_path = os.path.join(tempfile.gettempdir(), f"screenshot_{int(time.time())}.png")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        page.goto(url, wait_until='networkidle')
        page.screenshot(path=output_path, full_page=True)
        browser.close()
    return output_path

def check_code_errors(project_path: str) -> dict:
    errors = {}
    try:
        result = subprocess.run(
            ['npx', 'eslint', '.', '--ext', '.js,.jsx,.ts,.tsx', '--format', 'json'],
            cwd=project_path,
            capture_output=True,
            text=True
        )
        if result.stdout:
            errors['eslint'] = json.loads(result.stdout)
    except Exception as e:
        errors['eslint_error'] = str(e)
    py_errors = []
    for root, _, files in os.walk(project_path):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    subprocess.run(['python', '-m', 'py_compile', filepath], check=True, capture_output=True)
                except subprocess.CalledProcessError as e:
                    py_errors.append({'file': filepath, 'error': e.stderr})
    if py_errors:
        errors['python'] = py_errors
    return errors if errors else {"status": "no errors detected"}

def purchase_domain(domain: str, provider: str = 'namecom') -> dict:
    if provider.lower() == 'namecom':
        api_user = os.getenv('NAME_COM_PROD_USER')
        api_token = os.getenv('NAME_COM_PROD_TOKEN')
        url = f'https://api.name.com/v4/domains'
        headers = {'Api-Username': api_user, 'Api-Token': api_token}
        payload = {'domain': {'domainName': domain}}
        resp = requests.post(url, json=payload, headers=headers)
    elif provider.lower() == 'godaddy':
        key = os.getenv('GODADDY_API_KEY')
        secret = os.getenv('GODADDY_API_SECRET')
        url = f'https://api.godaddy.com/v1/domains/purchase'
        headers = {'Authorization': f'sso-key {key}:{secret}'}
        payload = {'domain': domain, 'consent': {'agreedAt': 'Multiverse', 'agreedBy': 'user'}}
        resp = requests.post(url, json=payload, headers=headers)
    else:
        return {"error": f"Provider {provider} not supported."}
    return resp.json()

def deploy_netlify(project_path: str) -> str:
    token = os.getenv('NETLIFY_AUTH_TOKEN')
    if not token:
        return "Netlify token not configured."
    subprocess.run(['npm', 'run', 'build'], cwd=project_path, shell=True)
    cmd = f'npx netlify deploy --prod --dir=dist --auth={token}'
    result = subprocess.run(cmd, cwd=project_path, shell=True, capture_output=True, text=True)
    return result.stdout

def deploy_vercel(project_path: str) -> str:
    token = os.getenv('VERCEL_TOKEN')
    if not token:
        return "Vercel token not configured."
    subprocess.run(['npm', 'run', 'build'], cwd=project_path, shell=True)
    cmd = f'npx vercel deploy --prod --token={token}'
    result = subprocess.run(cmd, cwd=project_path, shell=True, capture_output=True, text=True)
    return result.stdout

def deploy_cloudflare(project_path: str) -> str:
    token = os.getenv('CLOUDFLARE_API_TOKEN')
    account_id = os.getenv('CLOUDFLARE_ACCOUNT_ID')
    if not token or not account_id:
        return "Cloudflare credentials missing."
    subprocess.run(['npm', 'run', 'build'], cwd=project_path, shell=True)
    cmd = f'npx wrangler pages deploy dist --project-name=multiverse-app --commit-dirty=true'
    result = subprocess.run(cmd, cwd=project_path, shell=True, capture_output=True, text=True)
    return result.stdout

def deploy_anonymous(project_path: str) -> str:
    subprocess.run(['npm', 'run', 'build'], cwd=project_path, shell=True)
    cmd = f'npx surge dist'
    result = subprocess.run(cmd, cwd=project_path, shell=True, capture_output=True, text=True)
    return result.stdout

def signup_and_get_api_key(service: str) -> dict:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        if service == 'example':
            page.goto('https://example.com/signup')
        browser.close()
    return {"api_key": "extracted_key"}
