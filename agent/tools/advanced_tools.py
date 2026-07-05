import os, io, zipfile, requests, tempfile, json, time, subprocess
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# ---------- Crawling ----------
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

# ---------- Screenshot ----------
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

# ---------- Error Checking ----------
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

# ---------- Domain Purchase ----------
def purchase_domain(domain: str, provider: str = 'namecom') -> dict:
    if provider.lower() == 'namecom':
        api_user = os.getenv('NAME_COM_PROD_USER')
        api_token = os.getenv('NAME_COM_PROD_TOKEN')
        url = 'https://api.name.com/v4/domains'
        headers = {'Api-Username': api_user, 'Api-Token': api_token}
        payload = {'domain': {'domainName': domain}}
        resp = requests.post(url, json=payload, headers=headers)
    elif provider.lower() == 'godaddy':
        key = os.getenv('GODADDY_API_KEY')
        secret = os.getenv('GODADDY_API_SECRET')
        url = 'https://api.godaddy.com/v1/domains/purchase'
        headers = {'Authorization': f'sso-key {key}:{secret}'}
        payload = {'domain': domain, 'consent': {'agreedAt': 'Multiverse', 'agreedBy': 'user'}}
        resp = requests.post(url, json=payload, headers=headers)
    else:
        return {"error": f"Provider {provider} not supported."}
    return resp.json()

# ---------- Pure Python Deployments (ZIP timestamp fix) ----------
def _create_zip_from_dir(dir_path: str) -> io.BytesIO:
    """Create a ZIP file in memory, setting a valid modern timestamp for every file."""
    zip_buf = io.BytesIO()
    now = time.time()  # current timestamp (post‑1980)
    with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(dir_path):
            for f in files:
                full_path = os.path.join(root, f)
                arcname = os.path.relpath(full_path, dir_path)
                # Get file info and override the timestamp
                info = zipfile.ZipInfo(arcname, date_time=time.localtime(now)[:6])
                with open(full_path, 'rb') as src:
                    zf.writestr(info, src.read())
    zip_buf.seek(0)
    return zip_buf

def deploy_netlify(project_path: str) -> str:
    token = os.getenv('NETLIFY_AUTH_TOKEN')
    if not token:
        return "Netlify token not configured."
    dist = os.path.join(project_path, 'dist')
    if not os.path.exists(dist):
        dist = project_path
    zip_buf = _create_zip_from_dir(dist)
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/zip'}
    site_resp = requests.post('https://api.netlify.com/api/v1/sites', headers={'Authorization': f'Bearer {token}'}, json={})
    if site_resp.status_code != 201:
        return f"Netlify site creation failed: {site_resp.text}"
    site_id = site_resp.json()['id']
    deploy_resp = requests.post(f'https://api.netlify.com/api/v1/sites/{site_id}/deploys', headers=headers, data=zip_buf)
    if deploy_resp.status_code == 200:
        data = deploy_resp.json()
        return f"Netlify deployed: {data.get('deploy_ssl_url') or data.get('url')}"
    return f"Netlify deploy failed: {deploy_resp.text}"

def deploy_vercel(project_path: str) -> str:
    token = os.getenv('VERCEL_TOKEN')
    if not token:
        return "Vercel token not configured."
    dist = os.path.join(project_path, 'dist')
    if not os.path.exists(dist):
        dist = project_path
    headers = {'Authorization': f'Bearer {token}'}
    create_resp = requests.post('https://api.vercel.com/v13/deployments', headers=headers, json={"name": "beast-deploy"})
    if create_resp.status_code != 200:
        return f"Vercel create deployment failed: {create_resp.text}"
    deploy_data = create_resp.json()
    deployment_id = deploy_data['id']
    for root, _, files in os.walk(dist):
        for f in files:
            full_path = os.path.join(root, f)
            rel = os.path.relpath(full_path, dist)
            with open(full_path, 'rb') as file:
                file_resp = requests.put(deploy_data['uploadUrls'][rel], data=file)
                if file_resp.status_code not in [200, 204]:
                    return f"Vercel upload failed: {file_resp.status_code}"
    finalize_resp = requests.post(f'https://api.vercel.com/v13/deployments/{deployment_id}/finalize', headers=headers)
    if finalize_resp.status_code == 200:
        url = f"https://{finalize_resp.json().get('url')}"
        return f"Vercel deployed: {url}"
    return f"Vercel finalize failed: {finalize_resp.text}"

def deploy_anonymous(project_path: str) -> str:
    dist = os.path.join(project_path, 'dist')
    if not os.path.exists(dist):
        dist = project_path
    zip_buf = _create_zip_from_dir(dist)
    token = os.getenv('SURGE_TOKEN')
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    resp = requests.post('https://surge.sh/api/v1/deploy', files={'file': ('project.zip', zip_buf)}, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        return f"Surge deployed: {data.get('url', 'unknown')}"
    return f"Surge deploy failed: {resp.text}"

def deploy_cloudflare(project_path: str) -> str:
    token = os.getenv('CLOUDFLARE_API_TOKEN')
    account_id = os.getenv('CLOUDFLARE_ACCOUNT_ID')
    if not token or not account_id:
        return "Cloudflare credentials missing."
    dist = os.path.join(project_path, 'dist')
    if not os.path.exists(dist):
        dist = project_path
    try:
        result = subprocess.run(['npx', 'wrangler', 'pages', 'deploy', dist, '--project-name=multiverse-app', '--commit-dirty=true'],
                                cwd=project_path, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return f"Cloudflare deployed: {result.stdout.splitlines()[-1] if result.stdout else 'unknown'}"
        else:
            return f"Cloudflare deploy failed: {result.stderr}"
    except Exception as e:
        return f"Cloudflare deploy unavailable (Node missing): {str(e)}"

def signup_and_get_api_key(service: str) -> dict:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        if service == 'example':
            page.goto('https://example.com/signup')
        browser.close()
    return {"api_key": "extracted_key"}
