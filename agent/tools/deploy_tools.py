# agent/tools/deploy_tools.py
import os
import paramiko
from scp import SCPClient
from config import DEPLOY_HOST, DEPLOY_USER, DEPLOY_KEY_PATH, DEPLOY_WEB_ROOT

def deploy_via_ssh(local_dir: str, remote_dir: str = None) -> bool:
    """
    Deploy a local project directory to a remote server via SSH/SCP.
    Requires DEPLOY_* config set.
    """
    if not all([DEPLOY_HOST, DEPLOY_USER, DEPLOY_KEY_PATH]):
        raise ValueError("Deployment config missing. Check .env")

    remote_path = remote_dir or DEPLOY_WEB_ROOT
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        hostname=DEPLOY_HOST,
        username=DEPLOY_USER,
        key_filename=DEPLOY_KEY_PATH
    )

    with SCPClient(ssh.get_transport()) as scp:
        scp.put(local_dir, remote_path, recursive=True)

    ssh.close()
    return True

# You can add more deployment methods: FTP, Vercel CLI, Netlify API, etc.
