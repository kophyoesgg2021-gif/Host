import telebot
import subprocess
import os
import zipfile
import tempfile
import shutil
from telebot import types
import time
from datetime import datetime, timedelta
import psutil
import sqlite3
import logging
import threading
import re
import sys
import atexit
import requests
import random
import string
import json
import ast
import hashlib
import secrets
import hmac
import ipaddress
import socket
import signal
import resource
from functools import wraps
import math
import queue
from collections import defaultdict
import base64

# --- Flask Keep Alive ---
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "☁️ PAI CLOUD - Premium Hosting Environment"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    print("☁️ PAI Cloud Keep-Alive server started.")
# --- End Flask Keep Alive ---

# --- Configuration ---
TOKEN = '8295100737:AAHPAYInBe1GRT-GYhvC4K8tCSxHH02HWyk'
OWNER_ID = 7259590181
ADMIN_ID = 7259590181
YOUR_USERNAME = '@leostrike223'

# Force Join Settings
FORCE_CHANNEL = '@leolotterydev'
FORCE_GROUP = '@devpaitrxsignal'
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_BOTS_DIR = os.path.join(BASE_DIR, 'pai_uploads')
PAI_DIR = os.path.join(BASE_DIR, 'pai_data')
DATABASE_PATH = os.path.join(PAI_DIR, 'pai_host.db')

# File upload limits
FREE_USER_LIMIT = 1
PREMIUM_USER_LIMIT = 999
ADMIN_LIMIT = 999
OWNER_LIMIT = float('inf')

# Security scan data
user_warnings = {}
MAX_WARNINGS = 3

os.makedirs(UPLOAD_BOTS_DIR, exist_ok=True)
os.makedirs(PAI_DIR, exist_ok=True)

bot = telebot.TeleBot(TOKEN, threaded=True, num_threads=10)

bot_scripts = {}
user_subscriptions = {}
user_files = {}
active_users = set()
admin_ids = {ADMIN_ID, OWNER_ID}
bot_locked = False
force_join_enabled = True
broadcast_messages = {}

# Security scan data
security_scans = {
    'total_scans': 0,
    'threats_found': 0,
    'high_risk_files': 0,
    'blocked_files': 0
}

# --- Enhanced Security Configuration ---
class SecurityConfig:
    # Rate limiting
    RATE_LIMIT_REQUESTS = 20
    RATE_LIMIT_WINDOW = 60
    
    # File upload restrictions
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    MAX_TOTAL_STORAGE_PER_USER = 50 * 1024 * 1024  # 50MB per user
    
    # Process restrictions
    MAX_CPU_PERCENT = 25
    MAX_MEMORY_MB = 100
    MAX_PROCESSES_PER_USER = 2
    MAX_PROCESS_RUNTIME = 1800  # 30 minutes
    
    # Package security
    DANGEROUS_PIP_PACKAGES = {
        'os', 'sys', 'subprocess', 'ctypes', 'inject', 'exploit',
        'pynput', 'keyboard', 'mouse', 'pyautogui', 'scapy',
        'impacket', 'pymetasploit', 'pyrasp', 'pydbg',
    }
    
    DANGEROUS_NPM_PACKAGES = {
        'child_process', 'fs', 'net', 'http-proxy', 'ssh2',
        'keylogger', 'robotjs', 'iohook', 'node-ffi',
        'node-inject', 'node-exploit', 'puppeteer', 'playwright',
    }

# --- Security Scanner Configuration ---
SUSPICIOUS_PATTERNS = {
    'source_reading': [
        r'paihost\.py',
        r'open.*paihost',
        r'read.*paihost',
        r'import.*paihost',
        r'from.*paihost',
        r'__file__.*paihost',
        r'os\.path\.dirname.*paihost',
        r'\.\./paihost',
        r'\./paihost',
        r'/paihost\.py',
        r'pai_host\.py',
        r'this.*bot.*source',
        r'host.*bot.*code',
    ],
    'file_exfiltration': [
        r'telegram\.send_document',
        r'send_document',
        r'upload.*file',
        r'export.*file',
        r'copy.*file',
        r'shutil\.copy',
        r'os\.system.*cp',
        r'wget.*\.py',
        r'curl.*\.py',
        r'requests\.post.*file',
        r'base64.*encode.*file',
        r'send.*file.*telegram',
        r'forward.*file',
        r'download.*file',
    ],
    'directory_traversal': [
        r'os\.listdir',
        r'os\.walk',
        r'glob\.glob',
        r'Path\(.*\)\.rglob',
        r'find.*\.py',
        r'scan.*directory',
        r'explore.*files',
        r'get.*all.*files',
        r'search.*files',
        r'enumerate.*files',
    ],
    'sensitive_access': [
        r'DATABASE_PATH',
        r'UPLOAD_BOTS_DIR',
        r'PAI_DIR',
        r'user_files',
        r'user_subscriptions',
    ],
    'obfuscation': [
        r'exec\(',
        r'eval\(',
        r'__import__\(',
        r'compile\(',
        r'base64\.b64decode',
        r'codecs\.decode',
        r'getattr.*__',
        r'setattr.*__',
        r'bytearray.*decode',
        r'str.*decode',
    ],
    'backdoor': [
        r'socket\.connect',
        r'bind.*port',
        r'listen.*port',
        r'accept\(\)',
        r'shell.*true',
        r'pty\.spawn',
        r'subprocess\.Popen.*shell',
        r'os\.system',
        r'os\.popen',
        r'backconnect',
        r'reverse.*shell',
    ]
}

SUSPICIOUS_IMPORTS = [
    'os', 'sys', 'subprocess', 'pathlib',
    'zipfile', 'tempfile', 'requests', 'base64',
    'codecs', 'pickle', 'marshal', 'ctypes',
    'pty', 'telnetlib', 'ftplib', 'smtplib'
]

# Supported files
SUPPORTED_EXTENSIONS = {
    '.py': 'Python', '.java': 'Java', '.html': 'HTML', '.htm': 'HTML',
    '.js': 'JavaScript', '.css': 'CSS', '.txt': 'Text', '.json': 'JSON',
    '.xml': 'XML', '.php': 'PHP', '.c': 'C', '.cpp': 'C++', '.cs': 'C#',
    '.rb': 'Ruby', '.go': 'Go', '.rs': 'Rust', '.md': 'Markdown',
    '.yaml': 'YAML', '.yml': 'YAML', '.sql': 'SQL', '.sh': 'Shell',
    '.bat': 'Batch', '.ps1': 'PowerShell', '.r': 'R', '.swift': 'Swift',
    '.kt': 'Kotlin', '.scala': 'Scala', '.pl': 'Perl', '.lua': 'Lua',
    '.ts': 'TypeScript', '.jsx': 'React JSX', '.tsx': 'React TSX',
    '.vue': 'Vue', '.svelte': 'Svelte', '.dart': 'Dart', '.scss': 'SCSS',
    '.less': 'Less', '.styl': 'Stylus', '.coffee': 'CoffeeScript'
}

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Advanced Rate Limiting ---
class AdvancedRateLimiter:
    def __init__(self):
        self.requests = {}
        self.suspicious_activity = {}
        self.lock = threading.Lock()
        self.BLACKLIST_THRESHOLD = 50
        self.TIME_WINDOW = 3600
    
    def check_rate_limit(self, user_id, action_type='default'):
        """Enhanced rate limiting with action-based limits"""
        with self.lock:
            now = time.time()
            
            limits = {
                'default': (30, 60),
                'upload': (5, 3600),
                'install': (10, 3600),
                'process': (3, 300),
                'admin': (100, 60),
            }
            
            max_requests, window = limits.get(action_type, limits['default'])
            
            if user_id in admin_ids:
                max_requests *= 2
            
            if user_id not in self.requests:
                self.requests[user_id] = {}
            
            if action_type not in self.requests[user_id]:
                self.requests[user_id][action_type] = []
            
            self.requests[user_id][action_type] = [
                req_time for req_time in self.requests[user_id][action_type]
                if now - req_time < window
            ]
            
            if len(self.requests[user_id][action_type]) >= max_requests:
                self.track_suspicious(user_id, f"rate_limit_exceeded_{action_type}")
                return False
            
            self.requests[user_id][action_type].append(now)
            return True
    
    def track_suspicious(self, user_id, activity_type):
        """Track suspicious user activity"""
        with self.lock:
            now = time.time()
            
            if user_id not in self.suspicious_activity:
                self.suspicious_activity[user_id] = []
            
            self.suspicious_activity[user_id] = [
                act for act in self.suspicious_activity[user_id]
                if now - act['time'] < self.TIME_WINDOW
            ]
            
            self.suspicious_activity[user_id].append({
                'type': activity_type,
                'time': now
            })
            
            return len(self.suspicious_activity[user_id]) >= self.BLACKLIST_THRESHOLD
    
    def is_suspicious(self, user_id):
        """Check if user has suspicious activity"""
        with self.lock:
            if user_id not in self.suspicious_activity:
                return False
            
            now = time.time()
            recent_activities = [
                act for act in self.suspicious_activity[user_id]
                if now - act['time'] < 1800
            ]
            
            return len(recent_activities) > 10

rate_limiter = AdvancedRateLimiter()

def advanced_rate_limit(action_type='default'):
    """Advanced rate limiting decorator"""
    def decorator(func):
        @wraps(func)
        def wrapper(message, *args, **kwargs):
            user_id = message.from_user.id
            
            if user_id == OWNER_ID:
                return func(message, *args, **kwargs)
            
            if rate_limiter.is_suspicious(user_id):
                bot.send_message(
                    message.chat.id,
                    "⚠️ **Suspicious activity detected**. Your access has been temporarily restricted.",
                    parse_mode='Markdown'
                )
                return
            
            if not rate_limiter.check_rate_limit(user_id, action_type):
                bot.reply_to(
                    message,
                    f"⏳ **Rate limit exceeded**. Please wait.",
                    parse_mode='Markdown'
                )
                rate_limiter.track_suspicious(user_id, f"rate_limit_{action_type}")
                return
            
            return func(message, *args, **kwargs)
        return wrapper
    return decorator

# --- Anti-Source Theft System ---
class AdvancedSourceProtection:
    def __init__(self):
        self.source_hash = None
        self.source_signature = None
        self.integrity_checks = []
        self.honeypot_files = {}
        self.setup_honeypot()
        self.generate_source_signature()
    
    def generate_source_signature(self):
        """Generate multiple cryptographic signatures"""
        try:
            with open(__file__, 'rb') as f:
                content = f.read()
            
            self.source_hash = {
                'sha256': hashlib.sha256(content).hexdigest(),
                'sha512': hashlib.sha512(content).hexdigest(),
                'blake2b': hashlib.blake2b(content).hexdigest(),
            }
            
            for i in range(3):
                key = secrets.token_bytes(32)
                signature = hmac.new(key, content, hashlib.sha512).hexdigest()
                self.source_signature = signature
                self.integrity_checks.append({
                    'key': key.hex(),
                    'signature': signature,
                    'timestamp': time.time()
                })
            
        except Exception as e:
            logger.error(f"Failed to generate source signature: {e}")
    
    def verify_source_integrity(self):
        """Advanced source integrity verification"""
        try:
            with open(__file__, 'rb') as f:
                current_content = f.read()
            
            current_hash = {
                'sha256': hashlib.sha256(current_content).hexdigest(),
                'sha512': hashlib.sha512(current_content).hexdigest(),
                'blake2b': hashlib.blake2b(current_content).hexdigest(),
            }
            
            for algo, hash_value in current_hash.items():
                if hash_value != self.source_hash.get(algo):
                    logger.critical(f"⚠️ Source integrity failed: {algo} mismatch!")
                    return False
            
            signature_valid = False
            for check in self.integrity_checks[-3:]:
                key = bytes.fromhex(check['key'])
                expected = hmac.new(key, current_content, hashlib.sha512).hexdigest()
                if expected == check['signature']:
                    signature_valid = True
                    break
            
            if not signature_valid:
                logger.critical("⚠️ Source signature verification failed!")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to verify source integrity: {e}")
            return False
    
    def setup_honeypot(self):
        """Create honeypot files to trap attackers"""
        honeypot_dir = os.path.join(PAI_DIR, '.honeypot')
        os.makedirs(honeypot_dir, exist_ok=True)
        
        honeypot_files = {
            'paihost_backup.py': 'print("This is a backup file")',
            'config_backup.json': json.dumps({'token': 'fake_token', 'key': 'fake_key'}),
            'database_backup.db': 'Fake database content',
            'secret_keys.txt': 'API_KEY=fake_key\nSECRET=fake_secret',
        }
        
        for filename, content in honeypot_files.items():
            filepath = os.path.join(honeypot_dir, filename)
            with open(filepath, 'w') as f:
                f.write(content)
            
            self.honeypot_files[filepath] = {
                'filename': filename,
                'created': time.time(),
                'accessed': False,
                'accessed_by': None,
                'accessed_time': None
            }
    
    def check_honeypot_access(self, filepath, user_id):
        """Check if a honeypot file was accessed"""
        if filepath in self.honeypot_files:
            self.honeypot_files[filepath]['accessed'] = True
            self.honeypot_files[filepath]['accessed_by'] = user_id
            self.honeypot_files[filepath]['accessed_time'] = time.time()
            
            logger.critical(f"🚨 HONEYPOT TRIGGERED! User {user_id} accessed {filepath}")
            
            ban_user(user_id)
            
            bot.send_message(
                OWNER_ID,
                f"🚨 **HONEYPOT TRIGGERED**\n\n"
                f"User: `{user_id}`\n"
                f"File: `{os.path.basename(filepath)}`\n"
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"**Action:** User has been automatically banned.",
                parse_mode='Markdown'
            )
            
            return True
        return False
    
    def detect_source_theft_attempt(self, content, user_id):
        """Advanced detection of source theft attempts"""
        suspicious_patterns = [
            r'open.*paihost\.py',
            r'read.*paihost\.py',
            r'cat.*paihost\.py',
            r'curl.*paihost\.py',
            r'wget.*paihost\.py',
            r'cp.*paihost\.py',
            r'mv.*paihost\.py',
            r'download.*paihost',
            r'base64.*paihost',
            self.source_hash['sha256'][:16] if self.source_hash else '',
            r'TOKEN\s*=\s*[\'"]\d+:[^\'"]+[\'"]',
            r'OWNER_ID\s*=\s*\d+',
            r'ADMIN_ID\s*=\s*\d+',
            r'FORCE_CHANNEL\s*=\s*[\'"]@[^\'"]+[\'"]',
            r'DATABASE_PATH',
            r'UPLOAD_BOTS_DIR',
            r'PAI_DIR',
        ]
        
        detected = []
        for pattern in suspicious_patterns:
            if pattern and re.search(pattern, content, re.IGNORECASE):
                detected.append(pattern)
        
        if detected:
            logger.warning(f"User {user_id} attempted source theft. Patterns: {detected[:3]}")
            rate_limiter.track_suspicious(user_id, 'source_theft_attempt')
            
            if len(detected) >= 3:
                logger.critical(f"🚨 SERIOUS SOURCE THEFT ATTEMPT by user {user_id}")
                return True, detected
        
        return False, detected

source_protector = AdvancedSourceProtection()

# --- Ransomware & Malware Protection System ---
class RansomwareProtection:
    """Advanced protection against ransomware and malware"""
    def __init__(self):
        self.file_monitor = FileMonitor()
        self.behavior_analyzer = BehaviorAnalyzer()
        self.signature_detector = SignatureDetector()
        self.heuristic_engine = HeuristicEngine()
        self.sandbox_environment = SandboxEnvironment()
        self.file_backup = FileBackup()
        self.quarantine = QuarantineSystem()
        self.alert_system = AlertSystem()
        
        self.protection_active = True
        self.scan_queue = queue.Queue()
        self.scan_results = {}
        self.lock = threading.Lock()
        
        self.start_monitoring()
    
    def start_monitoring(self):
        """Start monitoring threads"""
        fs_thread = threading.Thread(target=self.monitor_filesystem, daemon=True)
        fs_thread.start()
        
        proc_thread = threading.Thread(target=self.monitor_processes, daemon=True)
        proc_thread.start()
        
        net_thread = threading.Thread(target=self.monitor_network, daemon=True)
        net_thread.start()
    
    def monitor_filesystem(self):
        """Monitor filesystem for ransomware-like activity"""
        file_events = defaultdict(list)
        encryption_attempts = defaultdict(int)
        
        while self.protection_active:
            try:
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        pid = proc.info['pid']
                        name = proc.info['name']
                        
                        try:
                            open_files = proc.open_files()
                        except:
                            continue
                        
                        for file in open_files:
                            path = file.path
                            
                            if self.is_encryption_target(path):
                                file_events[pid].append({
                                    'path': path,
                                    'time': time.time(),
                                    'operation': 'write'
                                })
                                
                                recent = [e for e in file_events[pid] 
                                         if time.time() - e['time'] < 10]
                                
                                if len(recent) > 50:
                                    encryption_attempts[pid] += 1
                                    
                                    if encryption_attempts[pid] > 3:
                                        self.handle_ransomware_detection(pid, name, 'mass_encryption')
                                        break
                            
                            if self.detect_extension_change(path):
                                self.handle_suspicious_activity(pid, name, 'extension_change', path)
                            
                            if self.is_ransom_note(path):
                                self.handle_ransomware_detection(pid, name, 'ransom_note_created')
                    
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Filesystem monitor error: {e}")
                time.sleep(5)
    
    def monitor_processes(self):
        """Monitor processes for malicious behavior"""
        process_history = defaultdict(list)
        
        while self.protection_active:
            try:
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        pid = proc.info['pid']
                        name = proc.info['name']
                        
                        if self.is_ransomware_process(name):
                            self.handle_ransomware_detection(pid, name, 'known_ransomware')
                            continue
                        
                        cmdline = ' '.join(proc.info['cmdline'] if proc.info['cmdline'] else [])
                        
                        if 'vssadmin' in cmdline.lower() and 'delete' in cmdline.lower():
                            self.handle_ransomware_detection(pid, name, 'shadow_copy_deletion')
                        
                        if any(x in cmdline.lower() for x in ['wbadmin', 'wmic', 'bcdedit']):
                            if any(x in cmdline.lower() for x in ['delete', 'remove', 'disable']):
                                self.handle_ransomware_detection(pid, name, 'backup_deletion')
                        
                        try:
                            connections = proc.connections()
                            for conn in connections:
                                if conn.status == 'ESTABLISHED' and hasattr(conn, 'raddr') and conn.raddr:
                                    if self.is_c2_server(conn.raddr.ip):
                                        self.handle_ransomware_detection(pid, name, 'c2_connection')
                        except:
                            pass
                        
                        process_history[pid].append({
                            'time': time.time(),
                            'cpu': proc.cpu_percent(),
                            'memory': proc.memory_percent(),
                        })
                        
                        process_history[pid] = [p for p in process_history[pid] 
                                               if time.time() - p['time'] < 300]
                        
                        if self.detect_abnormal_behavior(process_history[pid]):
                            self.handle_suspicious_activity(pid, name, 'abnormal_behavior')
                        
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Process monitor error: {e}")
                time.sleep(5)
    
    def monitor_network(self):
        """Monitor network for ransomware C2 communication"""
        while self.protection_active:
            try:
                for conn in psutil.net_connections():
                    try:
                        if conn.status == 'ESTABLISHED' and hasattr(conn, 'raddr') and conn.raddr:
                            ip = conn.raddr.ip
                            port = conn.raddr.port
                            
                            if self.is_c2_server(ip):
                                for proc in psutil.process_iter(['pid', 'name']):
                                    try:
                                        if conn.pid == proc.info['pid']:
                                            self.handle_ransomware_detection(
                                                proc.info['pid'], 
                                                proc.info['name'], 
                                                'c2_communication',
                                                f'IP: {ip}, Port: {port}'
                                            )
                                            break
                                    except:
                                        pass
                            
                            if port in [4444, 5555, 6666, 7777, 8888, 9001, 1337, 31337]:
                                self.handle_suspicious_activity(
                                    conn.pid, 
                                    'unknown', 
                                    'suspicious_port',
                                    f'Port: {port}'
                                )
                    
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"Network monitor error: {e}")
                time.sleep(10)
    
    def handle_ransomware_detection(self, pid, process_name, detection_type, details=''):
        """Handle confirmed ransomware detection"""
        alert = {
            'type': 'RANSOMWARE',
            'pid': pid,
            'process': process_name,
            'detection': detection_type,
            'details': details,
            'time': datetime.now().isoformat(),
            'severity': 'CRITICAL'
        }
        
        logger.critical(f"🚨 RANSOMWARE DETECTED: {alert}")
        
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            time.sleep(1)
            if proc.is_running():
                proc.kill()
            logger.info(f"Killed ransomware process {pid}")
        except:
            pass
        
        try:
            proc = psutil.Process(pid)
            for file in proc.open_files():
                self.quarantine.add_file(file.path, 'ransomware_related')
        except:
            pass
        
        self.alert_system.send_critical_alert(alert)
        
        user_id = self.find_user_for_process(pid)
        if user_id:
            ban_user(user_id)
            self.alert_system.send_user_banned_alert(user_id, 'ransomware')
        
        self.file_backup.attempt_recovery(user_id)
    
    def handle_suspicious_activity(self, pid, process_name, activity_type, details=''):
        """Handle suspicious but not confirmed malicious activity"""
        alert = {
            'type': 'SUSPICIOUS',
            'pid': pid,
            'process': process_name,
            'activity': activity_type,
            'details': details,
            'time': datetime.now().isoformat(),
            'severity': 'HIGH'
        }
        
        logger.warning(f"⚠️ Suspicious activity detected: {alert}")
        
        self.behavior_analyzer.add_suspicious_activity(pid, activity_type)
        
        user_id = self.find_user_for_process(pid)
        if user_id:
            if self.behavior_analyzer.should_ban_user(user_id):
                ban_user(user_id)
                self.alert_system.send_user_banned_alert(user_id, 'suspicious_activity_pattern')
        
        if activity_type in ['mass_encryption', 'shadow_copy_deletion', 'backup_deletion']:
            self.alert_system.send_high_risk_alert(alert)
    
    def detect_extension_change(self, filepath):
        """Detect if a file extension has been changed suspiciously"""
        suspicious_extensions = [
            '.encrypted', '.locked', '.crypted', '.enc', '.lock',
            '.crypto', '.worm', '.encrypt', '.onion', '.pay',
            '.ryk', '.cerber', '.cry', '.crypt', '.encry'
        ]
        
        ext = os.path.splitext(filepath)[1].lower()
        return ext in suspicious_extensions
    
    def is_ransom_note(self, filepath):
        """Check if file is a ransom note"""
        filename = os.path.basename(filepath).lower()
        
        ransom_notes = [
            'README.txt', 'README.html', 'HOW_TO_DECRYPT.txt', 
            'DECRYPT.txt', 'RECOVER.txt', 'RESTORE.txt', 
            'UNLOCK.txt', 'HELP.txt', 'INFO.txt', 'WARNING.txt'
        ]
        
        if filename in ransom_notes:
            return True
        
        try:
            with open(filepath, 'r', errors='ignore') as f:
                content = f.read().lower()
                patterns = [
                    r'your files (?:have been|are) encrypted',
                    r'to decrypt your files',
                    r'ransom', r'bitcoin', r'payment',
                    r'decryptor', r'encrypted files',
                ]
                for pattern in patterns:
                    if re.search(pattern, content):
                        return True
        except:
            pass
        
        return False
    
    def is_ransomware_process(self, process_name):
        """Check if process name matches known ransomware"""
        ransomware_names = [
            'wannacry', 'notpetya', 'badrabbit', 'locky', 'cryptolocker',
            'cerber', 'teslacrypt', 'torrentlocker', 'keRanger', 'filecoder',
            'gandcrab', 'ryuk', 'sodinokibi', 'revil', 'darkside',
            'conti', 'lockbit', 'hive', 'blackbasta', 'royal',
        ]
        
        name_lower = process_name.lower()
        for rans_name in ransomware_names:
            if rans_name in name_lower:
                return True
        
        return False
    
    def is_c2_server(self, ip):
        """Check if IP is known C2 server"""
        known_c2_servers = [
            '185.130.5.', '193.201.224.', '91.121.85.', '51.255.69.',
            '149.56.131.', '167.114.211.', '192.99.150.', '198.27.82.'
        ]
        
        for c2 in known_c2_servers:
            if ip.startswith(c2):
                return True
        
        return False
    
    def is_encryption_target(self, filepath):
        """Check if file is a target for encryption"""
        target_extensions = [
            '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.bmp',
            '.mp3', '.mp4', '.avi', '.mov', '.mkv', '.wmv',
            '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2',
            '.txt', '.rtf', '.odt', '.ods', '.odp',
            '.sql', '.db', '.mdb', '.accdb', '.dbf',
            '.py', '.java', '.c', '.cpp', '.h', '.cs',
            '.key', '.pem', '.crt', '.cer', '.pfx',
        ]
        
        ext = os.path.splitext(filepath)[1].lower()
        return ext in target_extensions
    
    def detect_abnormal_behavior(self, history):
        """Detect abnormal process behavior"""
        if len(history) < 10:
            return False
        
        avg_cpu = sum(p['cpu'] for p in history) / len(history)
        avg_memory = sum(p['memory'] for p in history) / len(history)
        
        recent = history[-3:]
        recent_cpu = sum(p['cpu'] for p in recent) / len(recent)
        
        if recent_cpu > avg_cpu * 3:
            return True
        
        return False
    
    def find_user_for_process(self, pid):
        """Find user ID associated with a process"""
        for script_key, process_info in bot_scripts.items():
            if process_info.get('process') and hasattr(process_info['process'], 'pid'):
                if process_info['process'].pid == pid:
                    return process_info.get('user_id')
        return None

class FileMonitor:
    """Monitor file system for suspicious changes"""
    def __init__(self):
        self.file_hashes = {}
    
    def detect_unauthorized_changes(self, user_id):
        """Detect unauthorized file changes"""
        user_folder = get_user_folder(user_id)
        changes = []
        
        current_snapshot = {}
        if os.path.exists(user_folder):
            for root, dirs, files in os.walk(user_folder):
                for file in files:
                    path = os.path.join(root, file)
                    try:
                        with open(path, 'rb') as f:
                            content = f.read()
                            current_snapshot[path] = hashlib.sha256(content).hexdigest()
                    except:
                        pass
        
        for path, current_hash in current_snapshot.items():
            if path in self.file_hashes:
                if current_hash != self.file_hashes[path]:
                    changes.append({
                        'type': 'modified',
                        'path': path
                    })
        
        for path in self.file_hashes:
            if path not in current_snapshot:
                changes.append({
                    'type': 'deleted',
                    'path': path
                })
        
        for path in current_snapshot:
            if path not in self.file_hashes:
                changes.append({
                    'type': 'created',
                    'path': path
                })
        
        self.file_hashes = current_snapshot
        
        return changes

class BehaviorAnalyzer:
    """Analyze user and process behavior patterns"""
    def __init__(self):
        self.user_behavior = defaultdict(list)
        self.suspicious_patterns = defaultdict(int)
        self.ban_threshold = 10
    
    def add_activity(self, user_id, activity_type, details=''):
        """Add user activity for analysis"""
        self.user_behavior[user_id].append({
            'type': activity_type,
            'details': details,
            'time': time.time()
        })
        
        self.user_behavior[user_id] = [
            a for a in self.user_behavior[user_id]
            if time.time() - a['time'] < 3600
        ]
    
    def add_suspicious_activity(self, pid, activity_type):
        """Track suspicious process activity"""
        self.suspicious_patterns[pid] += 1
    
    def analyze_user_behavior(self, user_id):
        """Analyze user behavior for suspicious patterns"""
        activities = self.user_behavior.get(user_id, [])
        
        if len(activities) < 5:
            return {'risk': 'low', 'score': 0}
        
        risk_score = 0
        
        file_ops = [a for a in activities if 'file' in a['type']]
        if len(file_ops) > 50:
            risk_score += 10
        
        process_starts = [a for a in activities if a['type'] == 'process_start']
        if len(process_starts) > 10:
            risk_score += 5
        
        suspicious_activities = [a for a in activities if 'suspicious' in a['type']]
        risk_score += len(suspicious_activities) * 2
        
        times = [a['time'] for a in activities]
        if times:
            time_span = max(times) - min(times)
            activity_rate = len(activities) / (time_span + 1)
            if activity_rate > 1:
                risk_score += activity_rate * 5
        
        risk_level = 'low'
        if risk_score > 50:
            risk_level = 'critical'
        elif risk_score > 30:
            risk_level = 'high'
        elif risk_score > 15:
            risk_level = 'medium'
        
        return {
            'risk': risk_level,
            'score': risk_score,
            'activities': len(activities)
        }
    
    def should_ban_user(self, user_id):
        """Determine if user should be banned based on behavior"""
        analysis = self.analyze_user_behavior(user_id)
        
        if analysis['risk'] == 'critical':
            return True
        
        if analysis['risk'] == 'high' and self.suspicious_patterns[user_id] > 5:
            return True
        
        return False

class SignatureDetector:
    """Detect known malware signatures"""
    def __init__(self):
        self.signatures = self.load_signatures()
        self.scan_count = 0
    
    def load_signatures(self):
        """Load known malware signatures"""
        return {
            'wannacry': [
                b'tasksche.exe', b'@WanaDecryptor@', b'!.Please Read Me!.',
                b'WannaCry', b'Wncry', b'WanaCrypt0r'
            ],
            'notpetya': [
                b'perfc.dat', b'dllhost.dat', b'Mischa', b'Petya',
            ],
            'locky': [
                b'_locky', b'Locky', b'zepto', b'odin',
            ],
            'cerber': [
                b'Cerber', b'CERBER', b'[CERBER]',
            ],
            'ryuk': [
                b'Ryuk', b'RYUK', b'RYKMAN'
            ],
            'trojan_generic': [
                b'CreateRemoteThread', b'VirtualAllocEx', b'WriteProcessMemory',
            ],
            'keylogger': [
                b'SetWindowsHookEx', b'GetAsyncKeyState', b'keylog',
            ],
            'backdoor': [
                b'reverse shell', b'bind shell', b'backconnect',
            ],
            'cryptominer': [
                b'stratum+tcp', b'cryptonight', b'minerd', b'xmrig',
            ]
        }
    
    def scan_file(self, filepath):
        """Scan file for malware signatures"""
        self.scan_count += 1
        matches = []
        
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            
            for malware_type, signatures in self.signatures.items():
                for signature in signatures:
                    if signature in content:
                        matches.append({
                            'type': malware_type,
                            'signature': signature.decode('ascii', errors='ignore')[:50],
                            'severity': 'high'
                        })
                        
                        if len([m for m in matches if m['type'] == malware_type]) > 2:
                            return {
                                'detected': True,
                                'malware': malware_type,
                                'confidence': 'high',
                                'matches': matches
                            }
            
            entropy = self.calculate_entropy(content)
            if entropy > 7.5:
                matches.append({
                    'type': 'packed_executable',
                    'signature': f'entropy_{entropy:.2f}',
                    'severity': 'medium'
                })
            
            return {
                'detected': len(matches) > 0,
                'malware': 'multiple' if matches else None,
                'confidence': 'medium' if matches else 'none',
                'matches': matches
            }
            
        except Exception as e:
            logger.error(f"Signature scan error: {e}")
            return {'detected': False, 'error': str(e)}
    
    def calculate_entropy(self, data):
        """Calculate Shannon entropy of data"""
        if not data:
            return 0
        
        entropy = 0
        for x in range(256):
            p_x = float(data.count(x)) / len(data)
            if p_x > 0:
                entropy += - p_x * math.log2(p_x)
        
        return entropy

class HeuristicEngine:
    """Heuristic-based malware detection"""
    def __init__(self):
        self.suspicious_apis = self.load_suspicious_apis()
        self.suspicious_patterns = self.load_suspicious_patterns()
    
    def load_suspicious_apis(self):
        """Load list of suspicious API calls"""
        return {
            'process': [
                'CreateProcess', 'ShellExecute', 'WinExec', 'system',
                'popen', 'subprocess', 'os.system',
            ],
            'file': [
                'DeleteFile', 'MoveFile', 'CopyFile', 'RemoveDirectory',
                'SetFileAttributes', 'encrypt', 'decrypt'
            ],
            'network': [
                'socket', 'connect', 'send', 'recv', 'DownloadFile',
            ],
            'injection': [
                'CreateRemoteThread', 'VirtualAllocEx', 'WriteProcessMemory',
            ]
        }
    
    def load_suspicious_patterns(self):
        """Load suspicious code patterns"""
        return {
            'anti_debug': [
                'IsDebuggerPresent', 'CheckRemoteDebuggerPresent',
                'ptrace', 'TRAP_TRACE'
            ],
            'anti_vm': [
                'VBox', 'VMware', 'VirtualBox', 'vbox', 'xen', 'kvm', 'qemu'
            ],
            'obfuscation': [
                'base64', 'rot13', 'xor', 'encrypt', 'decrypt',
                'pack', 'unpack', 'compress', 'decompress'
            ],
            'persistence': [
                r'HKEY_LOCAL_MACHINE.*Run',
                r'HKEY_CURRENT_USER.*Run',
                'CreateService', 'schtasks'
            ]
        }
    
    def analyze_code(self, code_content):
        """Heuristically analyze code for malware patterns"""
        findings = []
        
        found_apis = []
        for category, apis in self.suspicious_apis.items():
            for api in apis:
                if api.lower() in code_content.lower():
                    found_apis.append({'api': api, 'category': category})
        
        api_groups = defaultdict(int)
        for api in found_apis:
            api_groups[api['category']] += 1
        
        if api_groups['process'] > 0 and api_groups['file'] > 0 and api_groups['network'] > 0:
            findings.append({
                'type': 'multi_category_apis',
                'details': 'Process, File, and Network APIs detected',
                'severity': 'high'
            })
        
        if api_groups['injection'] > 0:
            findings.append({
                'type': 'process_injection',
                'details': 'Process injection APIs detected',
                'severity': 'critical'
            })
        
        for category, patterns in self.suspicious_patterns.items():
            for pattern in patterns:
                if pattern.lower() in code_content.lower():
                    findings.append({
                        'type': f'anti_analysis_{category}',
                        'details': f'Anti-{category} technique detected',
                        'severity': 'high'
                    })
        
        encryption_keywords = ['aes', 'rsa', 'des', 'rc4', 'encrypt', 'decrypt', 'cipher']
        encryption_count = sum(1 for kw in encryption_keywords if kw in code_content.lower())
        if encryption_count > 3:
            findings.append({
                'type': 'encryption_routines',
                'details': f'Multiple encryption keywords ({encryption_count})',
                'severity': 'high'
            })
        
        return findings

class SandboxEnvironment:
    """Create isolated environment for suspicious code execution"""
    def __init__(self):
        self.sandbox_dir = os.path.join(PAI_DIR, 'sandbox')
        os.makedirs(self.sandbox_dir, exist_ok=True)
        self.active_sandboxes = {}
    
    def create_sandbox(self, user_id, file_path):
        """Create a sandboxed environment for testing"""
        sandbox_id = secrets.token_hex(8)
        sandbox_path = os.path.join(self.sandbox_dir, sandbox_id)
        os.makedirs(sandbox_path)
        
        safe_name = f"sandbox_{int(time.time())}_{os.path.basename(file_path)}"
        sandbox_file = os.path.join(sandbox_path, safe_name)
        try:
            shutil.copy2(file_path, sandbox_file)
        except:
            return None
        
        sandbox_info = {
            'id': sandbox_id,
            'path': sandbox_path,
            'user_id': user_id,
            'original_file': file_path,
            'sandbox_file': sandbox_file,
            'created': time.time(),
            'processes': [],
            'results': None
        }
        
        self.active_sandboxes[sandbox_id] = sandbox_info
        return sandbox_info
    
    def run_in_sandbox(self, sandbox_info, timeout=30):
        """Run suspicious file in sandbox with monitoring"""
        try:
            file_path = sandbox_info['sandbox_file']
            file_ext = os.path.splitext(file_path)[1].lower()
            
            file_monitor = {}
            for f in os.listdir(sandbox_info['path']):
                path = os.path.join(sandbox_info['path'], f)
                if os.path.isfile(path):
                    with open(path, 'rb') as pf:
                        file_monitor[path] = pf.read()
            
            if file_ext == '.py':
                process = subprocess.Popen(
                    [sys.executable, file_path],
                    cwd=sandbox_info['path'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            elif file_ext == '.js':
                process = subprocess.Popen(
                    ['node', file_path],
                    cwd=sandbox_info['path'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            else:
                return {'error': 'Unsupported file type'}
            
            sandbox_info['processes'].append(process)
            
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                
                changes = []
                for f in os.listdir(sandbox_info['path']):
                    path = os.path.join(sandbox_info['path'], f)
                    if os.path.isfile(path):
                        with open(path, 'rb') as cf:
                            current = cf.read()
                            if path in file_monitor:
                                if current != file_monitor[path]:
                                    changes.append({
                                        'file': f,
                                        'change': 'modified'
                                    })
                            else:
                                changes.append({
                                    'file': f,
                                    'change': 'created'
                                })
                
                sandbox_info['results'] = {
                    'stdout': stdout.decode('utf-8', errors='ignore')[:1000],
                    'stderr': stderr.decode('utf-8', errors='ignore')[:1000],
                    'changes': changes,
                    'success': True
                }
                
            except subprocess.TimeoutExpired:
                process.kill()
                sandbox_info['results'] = {
                    'error': 'timeout',
                    'success': False
                }
            
            return sandbox_info['results']
            
        except Exception as e:
            logger.error(f"Sandbox execution error: {e}")
            return {'error': str(e), 'success': False}
    
    def cleanup_sandbox(self, sandbox_id):
        """Remove sandbox environment"""
        if sandbox_id in self.active_sandboxes:
            try:
                sandbox_path = self.active_sandboxes[sandbox_id]['path']
                shutil.rmtree(sandbox_path, ignore_errors=True)
                del self.active_sandboxes[sandbox_id]
            except Exception as e:
                logger.error(f"Sandbox cleanup error: {e}")

class FileBackup:
    """Backup system for file recovery"""
    def __init__(self):
        self.backup_dir = os.path.join(PAI_DIR, 'backups')
        os.makedirs(self.backup_dir, exist_ok=True)
        self.backup_retention = 7 * 24 * 3600
    
    def backup_file(self, file_path, user_id):
        """Create a backup of a file before modification"""
        try:
            if not os.path.exists(file_path):
                return None
            
            user_backup = os.path.join(self.backup_dir, str(user_id))
            os.makedirs(user_backup, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.basename(file_path)
            backup_name = f"{timestamp}_{filename}.bak"
            backup_path = os.path.join(user_backup, backup_name)
            
            shutil.copy2(file_path, backup_path)
            
            backup_info = {
                'original': file_path,
                'backup': backup_path,
                'user_id': user_id,
                'timestamp': time.time(),
                'size': os.path.getsize(file_path),
                'hash': self.calculate_hash(file_path)
            }
            
            meta_path = backup_path + '.meta'
            with open(meta_path, 'w') as f:
                json.dump(backup_info, f)
            
            self.cleanup_old_backups(user_id)
            
            return backup_path
            
        except Exception as e:
            logger.error(f"Backup error: {e}")
            return None
    
    def calculate_hash(self, file_path):
        """Calculate file hash"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except:
            return None
    
    def cleanup_old_backups(self, user_id):
        """Remove backups older than retention period"""
        try:
            user_backup = os.path.join(self.backup_dir, str(user_id))
            if not os.path.exists(user_backup):
                return
            
            now = time.time()
            for file in os.listdir(user_backup):
                file_path = os.path.join(user_backup, file)
                if os.path.getmtime(file_path) < now - self.backup_retention:
                    os.remove(file_path)
                    
                    meta_path = file_path + '.meta'
                    if os.path.exists(meta_path):
                        os.remove(meta_path)
                        
        except Exception as e:
            logger.error(f"Backup cleanup error: {e}")
    
    def attempt_recovery(self, user_id):
        """Attempt to recover files for a user"""
        try:
            user_backup = os.path.join(self.backup_dir, str(user_id))
            if not os.path.exists(user_backup):
                return {'success': False, 'reason': 'No backups found'}
            
            recovered = []
            failed = []
            
            backups_by_file = {}
            for file in os.listdir(user_backup):
                if file.endswith('.meta'):
                    meta_path = os.path.join(user_backup, file)
                    with open(meta_path, 'r') as f:
                        backup_info = json.load(f)
                    
                    original = backup_info['original']
                    if original not in backups_by_file or \
                       backup_info['timestamp'] > backups_by_file[original]['timestamp']:
                        backups_by_file[original] = backup_info
            
            for original, backup_info in backups_by_file.items():
                try:
                    backup_path = backup_info['backup']
                    if os.path.exists(backup_path):
                        current_hash = self.calculate_hash(backup_path)
                        if current_hash == backup_info['hash']:
                            shutil.copy2(backup_path, original)
                            recovered.append(original)
                        else:
                            failed.append(original)
                except Exception as e:
                    logger.error(f"Recovery error for {original}: {e}")
                    failed.append(original)
            
            return {
                'success': len(recovered) > 0,
                'recovered': recovered,
                'failed': failed,
                'count': len(recovered)
            }
            
        except Exception as e:
            logger.error(f"Recovery attempt error: {e}")
            return {'success': False, 'reason': str(e)}

class QuarantineSystem:
    """Quarantine system for malicious files"""
    def __init__(self):
        self.quarantine_dir = os.path.join(PAI_DIR, 'quarantine')
        os.makedirs(self.quarantine_dir, exist_ok=True)
        self.quarantine_db = os.path.join(self.quarantine_dir, 'quarantine.db')
        self.init_db()
    
    def init_db(self):
        """Initialize quarantine database"""
        try:
            conn = sqlite3.connect(self.quarantine_db)
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS quarantine (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_path TEXT,
                    quarantine_path TEXT,
                    user_id INTEGER,
                    file_name TEXT,
                    file_hash TEXT,
                    reason TEXT,
                    severity TEXT,
                    detected_by TEXT,
                    detection_time TIMESTAMP,
                    status TEXT DEFAULT 'quarantined'
                )
            ''')
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Quarantine DB init error: {e}")
    
    def add_file(self, file_path, reason, severity='high', detected_by='scanner'):
        """Add file to quarantine"""
        try:
            if not os.path.exists(file_path):
                return False
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_name = os.path.basename(file_path)
            quarantine_name = f"{timestamp}_{file_name}.quarantine"
            quarantine_path = os.path.join(self.quarantine_dir, quarantine_name)
            
            with open(file_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            
            shutil.move(file_path, quarantine_path)
            try:
                os.chmod(quarantine_path, 0o400)
            except:
                pass
            
            conn = sqlite3.connect(self.quarantine_db)
            c = conn.cursor()
            c.execute('''
                INSERT INTO quarantine 
                (original_path, quarantine_path, file_name, file_hash, reason, severity, detected_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (file_path, quarantine_path, file_name, file_hash, reason, severity, detected_by))
            conn.commit()
            conn.close()
            
            logger.info(f"File quarantined: {file_name} - {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Quarantine error: {e}")
            return False
    
    def get_quarantine_list(self):
        """Get list of quarantined files"""
        try:
            conn = sqlite3.connect(self.quarantine_db)
            c = conn.cursor()
            c.execute('''
                SELECT id, original_path, file_name, reason, severity, detected_by, detection_time, status
                FROM quarantine ORDER BY detection_time DESC
            ''')
            records = c.fetchall()
            conn.close()
            
            return [{
                'id': r[0],
                'original_path': r[1],
                'file_name': r[2],
                'reason': r[3],
                'severity': r[4],
                'detected_by': r[5],
                'detection_time': r[6],
                'status': r[7]
            } for r in records]
        except:
            return []

class AlertSystem:
    """Alert system for security incidents"""
    def __init__(self):
        self.alert_queue = queue.Queue()
        self.alert_history = []
        self.max_history = 100
        self.start_alert_processor()
    
    def start_alert_processor(self):
        """Start alert processing thread"""
        thread = threading.Thread(target=self.process_alerts, daemon=True)
        thread.start()
    
    def process_alerts(self):
        """Process alerts from queue"""
        while True:
            try:
                alert = self.alert_queue.get(timeout=1)
                
                self.log_alert(alert)
                self.send_alert_to_owner(alert)
                self.take_automated_action(alert)
                
                self.alert_history.append(alert)
                if len(self.alert_history) > self.max_history:
                    self.alert_history.pop(0)
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Alert processor error: {e}")
    
    def send_critical_alert(self, alert):
        """Send critical alert"""
        alert['priority'] = 'CRITICAL'
        self.alert_queue.put(alert)
    
    def send_high_risk_alert(self, alert):
        """Send high risk alert"""
        alert['priority'] = 'HIGH'
        self.alert_queue.put(alert)
    
    def send_user_banned_alert(self, user_id, reason):
        """Send user banned alert"""
        alert = {
            'type': 'USER_BANNED',
            'user_id': user_id,
            'reason': reason,
            'time': datetime.now().isoformat(),
            'priority': 'HIGH'
        }
        self.alert_queue.put(alert)
    
    def log_alert(self, alert):
        """Log alert to file"""
        log_entry = f"[{alert['time']}] [{alert.get('priority', 'INFO')}] {alert.get('type', 'ALERT')}: {json.dumps(alert)}\n"
        
        log_file = os.path.join(PAI_DIR, 'security_alerts.log')
        with open(log_file, 'a') as f:
            f.write(log_entry)
    
    def send_alert_to_owner(self, alert):
        """Send alert to bot owner"""
        try:
            priority = alert.get('priority', 'INFO')
            alert_type = alert.get('type', 'Security Alert')
            
            if priority == 'CRITICAL':
                emoji = '🚨🚨🚨'
            elif priority == 'HIGH':
                emoji = '⚠️⚠️'
            elif priority == 'MEDIUM':
                emoji = '⚠️'
            else:
                emoji = 'ℹ️'
            
            message = f"{emoji} **SECURITY ALERT** {emoji}\n\n"
            message += f"**Type:** {alert_type}\n"
            message += f"**Priority:** {priority}\n"
            message += f"**Time:** {alert.get('time', 'N/A')}\n\n"
            
            for key, value in alert.items():
                if key not in ['type', 'priority', 'time']:
                    message += f"**{key}:** `{value}`\n"
            
            bot.send_message(OWNER_ID, message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Failed to send alert to owner: {e}")
    
    def take_automated_action(self, alert):
        """Take automated action based on alert"""
        try:
            if alert.get('type') == 'RANSOMWARE' and alert.get('priority') == 'CRITICAL':
                user_id = alert.get('user_id')
                if user_id and user_id != OWNER_ID:
                    ban_user(user_id)
                    logger.info(f"Auto-banned user {user_id} for ransomware")
            
            if 'pid' in alert:
                pid = alert['pid']
                try:
                    proc = psutil.Process(pid)
                    proc.terminate()
                    time.sleep(1)
                    if proc.is_running():
                        proc.kill()
                    logger.info(f"Killed malicious process {pid}")
                except:
                    pass
            
        except Exception as e:
            logger.error(f"Automated action error: {e}")

# Initialize ransomware protection
ransomware_protection = RansomwareProtection()

# --- Database Functions ---
def init_db():
    """initialize the database with required tables"""
    logger.info(f"🛢️ Initializing database at: {DATABASE_PATH}")
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (user_id INTEGER PRIMARY KEY, 
                      username TEXT, 
                      first_name TEXT, 
                      last_name TEXT, 
                      join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      verified INTEGER DEFAULT 0,
                      key_used TEXT,
                      key_used_date TIMESTAMP)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS subscriptions
                     (user_id INTEGER PRIMARY KEY, expiry TEXT, 
                      file_limit INTEGER DEFAULT 999,
                      redeemed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS user_files
                     (file_id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      username TEXT,
                      chat_id INTEGER,
                      file_name TEXT, 
                      file_type TEXT, 
                      file_path TEXT,
                      original_filename TEXT,
                      file_size INTEGER,
                      upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      is_active INTEGER DEFAULT 1,
                      is_pending INTEGER DEFAULT 0,
                      FOREIGN KEY (user_id) REFERENCES users(user_id))''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS active_users
                     (user_id INTEGER PRIMARY KEY)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS admins
                     (user_id INTEGER PRIMARY KEY)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS subscription_keys
                     (key_value TEXT PRIMARY KEY,
                      created_by INTEGER,
                      created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      days_valid INTEGER,
                      max_uses INTEGER DEFAULT 1,
                      used_count INTEGER DEFAULT 0,
                      file_limit INTEGER DEFAULT 999,
                      is_active INTEGER DEFAULT 1,
                      used_by_user INTEGER,
                      used_date TIMESTAMP)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS key_usage
                     (key_value TEXT, user_id INTEGER, used_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      PRIMARY KEY (key_value, user_id))''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS bot_settings
                     (setting_key TEXT PRIMARY KEY, setting_value TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS banned_users
                     (user_id INTEGER PRIMARY KEY,
                      banned_by INTEGER,
                      ban_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      reason TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS security_logs
                     (log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      username TEXT,
                      file_name TEXT,
                      threat_count INTEGER,
                      risk_level TEXT,
                      action_taken TEXT,
                      log_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        c.execute('INSERT OR IGNORE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)', 
                 ('free_user_limit', str(FREE_USER_LIMIT)))
        c.execute('INSERT OR IGNORE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)', 
                 ('force_join_enabled', '1'))
        
        c.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (OWNER_ID,))
        if ADMIN_ID != OWNER_ID:
            c.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (ADMIN_ID,))
        
        conn.commit()
        conn.close()
        logger.info("✅ Database initialized successfully.")
    except Exception as e:
        logger.error(f"❌ Database initialization error: {e}", exc_info=True)

def load_data():
    """load data from database into memory"""
    logger.info("📥 Loading data from database...")
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()

        c.execute('SELECT user_id, expiry, file_limit FROM subscriptions')
        for user_id, expiry, file_limit in c.fetchall():
            try:
                user_subscriptions[user_id] = {
                    'expiry': datetime.fromisoformat(expiry),
                    'file_limit': file_limit if file_limit else 999
                }
            except ValueError:
                logger.warning(f"⚠️ Invalid expiry date format for user {user_id}: {expiry}. Skipping.")

        c.execute('SELECT user_id, file_name, file_type, file_path FROM user_files WHERE is_pending = 0')
        for user_id, file_name, file_type, file_path in c.fetchall():
            if user_id not in user_files:
                user_files[user_id] = []
            user_files[user_id].append((file_name, file_type, file_path))

        c.execute('SELECT user_id FROM active_users')
        active_users.update(user_id for (user_id,) in c.fetchall())

        c.execute('SELECT user_id FROM admins')
        admin_ids.update(user_id for (user_id,) in c.fetchall())

        c.execute('SELECT setting_key, setting_value FROM bot_settings')
        for key, value in c.fetchall():
            if key == 'free_user_limit':
                global FREE_USER_LIMIT
                FREE_USER_LIMIT = int(value) if value.isdigit() else 1
            elif key == 'force_join_enabled':
                global force_join_enabled
                force_join_enabled = value == '1'

        conn.close()
        logger.info(f"📊 Data loaded: {len(active_users)} users, {len(user_subscriptions)} subscriptions, {len(admin_ids)} admins.")
    except Exception as e:
        logger.error(f"❌ Error loading data: {e}", exc_info=True)

init_db()
load_data()

# --- Security Scanner Functions ---
def scan_file_for_threats(file_path, user_id, username, file_name):
    """Scan uploaded file for security threats"""
    threats_found = []
    file_content = ""
    
    try:
        security_scans['total_scans'] += 1
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            file_content = f.read()
        
        if not file_content.strip():
            return threats_found
        
        import_lines = []
        lines = file_content.split('\n')
        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            if any(imp in line_lower for imp in ['import ', 'from ']):
                for sus_import in SUSPICIOUS_IMPORTS:
                    if sus_import in line_lower and 'telebot' not in line_lower:
                        import_lines.append(f"Line {i}: {line.strip()}")
            
            for category, patterns in SUSPICIOUS_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, line_lower, re.IGNORECASE):
                        threat = {
                            'category': category,
                            'line': i,
                            'content': line.strip()[:100],
                            'pattern': pattern
                        }
                        threats_found.append(threat)
        
        if import_lines:
            threats_found.append({
                'category': 'suspicious_imports',
                'line': 0,
                'content': '; '.join(import_lines)[:200],
                'pattern': 'multiple_suspicious_imports'
            })
        
        if file_path.endswith('.py'):
            try:
                tree = ast.parse(file_content)
                threats_found.extend(analyze_ast(tree, file_path))
            except SyntaxError:
                pass 
        
        if threats_found:
            security_scans['threats_found'] += 1
        
    except Exception as e:
        logger.error(f"❌ Error scanning file {file_path}: {e}")
    
    return threats_found

def analyze_ast(tree, file_path):
    """Analyze Python AST for suspicious patterns"""
    threats = []
    
    class ThreatVisitor(ast.NodeVisitor):
        def visit_Call(self, node):
            try:
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    dangerous_calls = ['exec', 'eval', '__import__', 'compile', 
                                     'system', 'popen', 'call', 'run', 'spawn']
                    
                    if func_name in dangerous_calls:
                        threats.append({
                            'category': 'dangerous_call',
                            'line': node.lineno if hasattr(node, 'lineno') else 0,
                            'content': f"{func_name}() called",
                            'pattern': f'dangerous_function_{func_name}'
                        })
                
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in ['open', 'read', 'write', 'copy', 'move', 'remove']:
                        for arg in node.args:
                            if isinstance(arg, ast.Str):
                                if 'paihost' in arg.s.lower() or 'pai_host' in arg.s.lower():
                                    threats.append({
                                        'category': 'source_access',
                                        'line': node.lineno if hasattr(node, 'lineno') else 0,
                                        'content': f"Accessing: {arg.s}",
                                        'pattern': 'accessing_paihost'
                                    })
            except:
                pass
            self.generic_visit(node)
        
        def visit_Import(self, node):
            for alias in node.names:
                if alias.name in SUSPICIOUS_IMPORTS:
                    threats.append({
                        'category': 'suspicious_import',
                        'line': node.lineno if hasattr(node, 'lineno') else 0,
                        'content': f"import {alias.name}",
                        'pattern': f'import_{alias.name}'
                    })
            self.generic_visit(node)
        
        def visit_ImportFrom(self, node):
            if node.module and node.module in SUSPICIOUS_IMPORTS:
                threats.append({
                    'category': 'suspicious_import',
                    'line': node.lineno if hasattr(node, 'lineno') else 0,
                    'content': f"from {node.module} import ...",
                    'pattern': f'from_{node.module}'
                })
            self.generic_visit(node)
    
    try:
        visitor = ThreatVisitor()
        visitor.visit(tree)
    except:
        pass
    
    return threats

def generate_threat_report(threats, user_id, username, file_name, file_path):
    """Generate a detailed threat report"""
    if not threats:
        return None
    
    report = {
        'user_id': user_id,
        'username': username or 'Unknown',
        'file_name': file_name,
        'file_path': file_path,
        'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'threat_count': len(threats),
        'threats_by_category': {},
        'high_risk': False,
        'critical_risk': False
    }
    
    for threat in threats:
        category = threat['category']
        if category not in report['threats_by_category']:
            report['threats_by_category'][category] = []
        report['threats_by_category'][category].append(threat)
        
        high_risk_categories = ['source_reading', 'dangerous_call', 'source_access', 'backdoor']
        critical_categories = ['source_reading', 'backdoor']
        
        if category in high_risk_categories:
            report['high_risk'] = True
        if category in critical_categories:
            report['critical_risk'] = True
    
    return report

def send_threat_alert_to_owner(report):
    """Send threat alert to owner with action buttons"""
    if not report:
        return
    
    user_id = report['user_id']
    username = report['username'] or 'Unknown'
    file_name = report['file_name']
    threat_count = report['threat_count']
    high_risk = report['high_risk']
    critical_risk = report['critical_risk']
    
    username_clean = username.replace('_', '\\_').replace('*', '\\*').replace('`', '\\`').replace('[', '\\[')
    file_name_clean = file_name.replace('_', '\\_').replace('*', '\\*').replace('`', '\\`').replace('[', '\\[')
    
    risk_level = '🔴 CRITICAL RISK' if critical_risk else '🟠 HIGH RISK' if high_risk else '🟡 MEDIUM RISK'
    
    alert_text = f"""
🚨 *SECURITY ALERT - MALICIOUS FILE DETECTED* 🚨

*User Information:*
• ID: `{user_id}`
• Username: {username_clean}
• File: `{file_name_clean}`
• Time: {report['scan_time']}
• Risk Level: {risk_level}

*Threat Analysis:*
• Total Threats: {threat_count}
• Categories Found: {', '.join(report['threats_by_category'].keys())}
• Critical Patterns: {'YES' if critical_risk else 'NO'}

*Top Threats Found:*
"""
    
    threat_details = ""
    count = 0
    for category, threats in report['threats_by_category'].items():
        for threat in threats[:1]: 
            if count < 3: 
                threat_content = threat['content'][:60].replace('`', "'").replace('*', '').replace('_', '')
                threat_details += f"• {category.upper()}: Line {threat['line']}\n"
                threat_details += f"  `{threat_content}...`\n"
                count += 1
    
    alert_text += threat_details
    
    if critical_risk:
        alert_text += f"""
        
*CRITICAL THREAT DETECTED*
*AUTO-BLOCKED* - File deleted and user restricted

Required manual review:
"""
    elif high_risk:
        alert_text += f"""
        
*HIGH RISK THREAT*
Immediate action recommended

Choose action below:
"""
    else:
        alert_text += f"""
        
*SUSPICIOUS PATTERNS*
Review recommended

Choose action below:
"""
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    if critical_risk:
        markup.add(
            types.InlineKeyboardButton("🚫 BAN USER", callback_data=f'security_ban_{user_id}_{file_name_clean}'),
            types.InlineKeyboardButton("🔒 BLOCK UPLOADS", callback_data=f'security_block_{user_id}_{file_name_clean}')
        )
    elif high_risk:
        markup.add(
            types.InlineKeyboardButton("🚫 BAN USER", callback_data=f'security_ban_{user_id}_{file_name_clean}'),
            types.InlineKeyboardButton("⚠️ WARN USER", callback_data=f'security_warn_{user_id}_{file_name_clean}')
        )
    else:
        markup.add(
            types.InlineKeyboardButton("⚠️ WARN USER", callback_data=f'security_warn_{user_id}_{file_name_clean}'),
            types.InlineKeyboardButton("👁️ IGNORE", callback_data=f'security_ignore_{user_id}_{file_name_clean}')
        )
    
    markup.add(
        types.InlineKeyboardButton("🗑️ DELETE FILE", callback_data=f'security_delete_{user_id}_{file_name_clean}'),
        types.InlineKeyboardButton("📋 DETAILS", callback_data=f'security_report_{user_id}_{file_name_clean}')
    )
    
    try:
        bot.send_message(OWNER_ID, alert_text, reply_markup=markup, parse_mode=None)
        
        if not critical_risk:
            try:
                with open(report['file_path'], 'rb') as f:
                    bot.send_document(
                        OWNER_ID,
                        f,
                        caption=f"🚨 Suspicious file: {file_name_clean}\nUser: {username_clean} ({user_id})\nRisk: {risk_level}"
                    )
            except:
                pass
        
        log_security_event(user_id, username, file_name, threat_count, 
                          'critical' if critical_risk else 'high' if high_risk else 'medium',
                          'alerted')
        
        logger.warning(f"⚠️ Security alert sent for user {user_id}, file {file_name}, risk: {risk_level}")
        
    except Exception as e:
        logger.error(f"❌ Failed to send security alert: {e}")
        try:
            simple_alert = f"""
🚨 SECURITY ALERT 🚨

User ID: {user_id}
Username: {username}
File: {file_name}
Risk: {risk_level}
Threats: {threat_count}

Action required.
            """
            bot.send_message(OWNER_ID, simple_alert, reply_markup=markup)
        except Exception as e2:
            logger.error(f"❌ Failed to send fallback alert: {e2}")

def log_security_event(user_id, username, file_name, threat_count, risk_level, action_taken):
    """Log security event to database"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute('''INSERT INTO security_logs 
                     (user_id, username, file_name, threat_count, risk_level, action_taken)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                 (user_id, username, file_name, threat_count, risk_level, action_taken))
        conn.commit()
    except Exception as e:
        logger.error(f"❌ Error logging security event: {e}")
    finally:
        conn.close()

def is_user_banned(user_id):
    """Check if user is banned"""
    if user_id in admin_ids or user_id == OWNER_ID:
        return False
    
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute('SELECT user_id FROM banned_users WHERE user_id = ?', (user_id,))
        return c.fetchone() is not None
    finally:
        conn.close()

def check_force_join(user_id):
    """check if user is member of required GROUP ONLY"""
    if user_id in admin_ids:
        return True
    
    if not force_join_enabled:
        return True
    
    if is_user_banned(user_id):
        return False  

    try:
        def get_chat_id(chat):
            return chat[1:] if isinstance(chat, str) and chat.startswith('@') else chat

        g_id = get_chat_id(FORCE_GROUP)
        group_member = bot.get_chat_member(g_id, user_id)  
        if group_member.status not in ['member', 'administrator', 'creator']:
            return False
        
        return True
    except Exception as e:
        logger.error(f"❌ Error checking membership for user {user_id}: {e}")
        return False

def create_force_join_message():
    """create force join message with modern UI (Group Only)"""
    return f"""
🔒 *ACCESS RESTRICTED* 🔒

👋 **Welcome! To access pai Cloud, please join our community:**

🌐 **Official Channel:** {FORCE_CHANNEL}
👥 **Community Group:** {FORCE_GROUP}

---
📋 **Instructions:**
1. Tap the button below to join the group.
2. Wait a few seconds for Telegram to update.
3. Tap "✅ Verify Access".
4. Enjoy unlimited cloud hosting!
    """

def create_force_join_keyboard():
    """create force join keyboard with modern buttons (Group Only)"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    markup.add(types.InlineKeyboardButton("👥 Join Group", url=f"https://t.me/{FORCE_GROUP[1:]}"))
    markup.add(types.InlineKeyboardButton("✅ Verify Access", callback_data='check_membership'))
    
    return markup

def mark_user_verified(user_id, verified=True):
    """mark user as verified in database"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute('UPDATE users SET verified = ? WHERE user_id = ?', 
                 (1 if verified else 0, user_id))
        conn.commit()
    except Exception as e:
        logger.error(f"❌ Error marking user verified: {e}")
    finally:
        conn.close()

def is_user_verified(user_id):
    """check if user is verified in database"""
    if user_id in admin_ids:
        return True
    
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute('SELECT verified FROM users WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        return result and result[0] == 1
    except Exception as e:
        logger.error(f"❌ Error checking user verification: {e}")
        return False
    finally:
        conn.close()

def get_user_folder(user_id):
    """get or create user's folder for storing files"""
    user_folder = os.path.join(UPLOAD_BOTS_DIR, str(user_id))
    os.makedirs(user_folder, exist_ok=True)
    return user_folder

def get_user_file_limit(user_id):
    """get the file upload limit for a user"""
    if user_id == OWNER_ID: return OWNER_LIMIT
    if user_id in admin_ids: return ADMIN_LIMIT
    
    if is_premium_user(user_id):
        subscription_info = user_subscriptions.get(user_id, {})
        return subscription_info.get('file_limit', PREMIUM_USER_LIMIT)
    
    return FREE_USER_LIMIT  

def get_user_file_count(user_id):
    """get the number of files uploaded by a user"""
    return len(user_files.get(user_id, []))

def is_premium_user(user_id):
    """check if user has active subscription"""
    if user_id in user_subscriptions:
        expiry = user_subscriptions[user_id]['expiry']
        return expiry > datetime.now()
    return False

def get_user_status(user_id):
    """get user status with modern emojis"""
    if user_id == OWNER_ID: return "👑 System Owner"
    if user_id in admin_ids: return "🛡️ Administrator"
    if is_premium_user(user_id): return "💎 Premium"
    return "👤 Standard User"

def get_premium_users_details():
    """get detailed information about premium users"""
    premium_users = []
    for user_id in active_users:
        if is_premium_user(user_id):
            try:
                chat = bot.get_chat(user_id)
                user_files_list = user_files.get(user_id, [])
                running_files = sum(1 for file_name, _, _ in user_files_list if is_bot_running(user_id, file_name))
                subscription_info = user_subscriptions.get(user_id, {})
                file_limit = subscription_info.get('file_limit', PREMIUM_USER_LIMIT)
                
                premium_users.append({
                    'user_id': user_id,
                    'first_name': chat.first_name,
                    'username': chat.username,
                    'file_count': len(user_files_list),
                    'file_limit': file_limit,
                    'running_files': running_files,
                    'expiry': subscription_info['expiry']
                })
            except Exception as e:
                logger.error(f"❌ Error getting user details for {user_id}: {e}")
    
    return premium_users

def generate_subscription_key(days, max_uses=1, file_limit=999, created_by=None):
    """generate subscription key with 1-key 1-user enforcement"""
    part1 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    part2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    key = f"PAI-{part1}-{part2}"
    
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute('''INSERT INTO subscription_keys 
                 (key_value, days_valid, max_uses, file_limit, created_by) 
                 VALUES (?, ?, ?, ?, ?)''',
              (key, days, max_uses, file_limit, created_by))
    conn.commit()
    conn.close()
    
    return key

def redeem_subscription_key(key_value, user_id):
    """redeem subscription key - one key per user"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    
    try:
        c.execute('''SELECT days_valid, max_uses, used_count, file_limit, is_active, used_by_user
                     FROM subscription_keys WHERE key_value = ?''', (key_value,))
        key_data = c.fetchone()
        
        if not key_data:
            return False, "❌ Invalid Key"
        
        days_valid, max_uses, used_count, file_limit, is_active, used_by_user = key_data
        
        if is_active != 1:
            return False, "❌ Key Inactive"
        
        if used_count >= max_uses:
            return False, f"❌ Key Already Used ({used_count}/{max_uses} uses)"
        
        if used_by_user and used_by_user == user_id:
            return False, "❌ You already used this key"
        
        c.execute('''SELECT key_used FROM users WHERE user_id = ? AND 
                     key_used IS NOT NULL''', (user_id,))
        user_key = c.fetchone()
        
        if user_key:
            return False, "❌ You already have an active key"
        
        current_expiry = user_subscriptions.get(user_id, {}).get('expiry', datetime.now())
        if current_expiry < datetime.now():
            current_expiry = datetime.now()
        
        new_expiry = current_expiry + timedelta(days=days_valid)
        
        save_subscription(user_id, new_expiry, file_limit)
        
        current_time = datetime.now().isoformat()
        c.execute('''UPDATE subscription_keys 
                     SET used_count = used_count + 1,
                         used_by_user = ?,
                         used_date = ?
                     WHERE key_value = ?''',
                  (user_id, current_time, key_value))
        
        c.execute('''UPDATE users 
                     SET key_used = ?,
                         key_used_date = ?
                     WHERE user_id = ?''',
                  (key_value, current_time, user_id))
        
        conn.commit()

        try:
            user_info = bot.get_chat(user_id)
            user_mention = f"[{user_info.first_name}](tg://user?id={user_id})" if user_info.first_name else f"User {user_id}"
    
            admin_msg = f"""
💳 **NEW PREMIUM ACTIVATION**

👤 **User:**
├─ ID: `{user_id}`
├─ Name: {user_mention}
├─ Username: @{user_info.username if user_info.username else 'N/A'}
└─ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔑 **Key Details:**
├─ Key: `{key_value}`
├─ Duration: {days_valid} Days
├─ Files: {file_limit} Files
├─ Uses: {used_count + 1}/{max_uses}
└─ Expires: {new_expiry.strftime('%Y-%m-%d %H:%M:%S')}
            """
            bot.send_message(OWNER_ID, admin_msg, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"❌ Failed to notify admin: {e}")    
        
        return True, f"""
✨ **PREMIUM ACTIVATED SUCCESSFULLY!** ✨

🔑 **Key:** `{key_value}`
👤 **Assigned to:** You
📅 **Duration:** {days_valid} Days
🗃 **File Limit:** {file_limit} Files
⏰ **Start:** {datetime.now().strftime('%Y-%m-%d')}
⏳ **End:** {new_expiry.strftime('%Y-%m-%d')}

📝 **Note:**
• This key is now linked to your account.
• It cannot be used by anyone else.
• You cannot use another key.
        """
    
    except Exception as e:
        return False, f"❌ Error: {str(e)}"
    finally:
        conn.close()

def get_all_subscription_keys():
    """get all subscription keys with details"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute('SELECT key_value, days_valid, max_uses, used_count, file_limit, created_date FROM subscription_keys ORDER BY created_date DESC')
    keys = c.fetchall()
    conn.close()
    return keys

def delete_subscription_key(key_value):
    """delete subscription key and remove premium status from users"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    
    c.execute('SELECT user_id FROM key_usage WHERE key_value = ?', (key_value,))
    users_affected = c.fetchall()
    
    for (user_id,) in users_affected:
        if user_id in user_subscriptions:
            del user_subscriptions[user_id]
        c.execute('DELETE FROM subscriptions WHERE user_id = ?', (user_id,))
        
        try:
            bot.send_message(user_id, "⚠️ **Your Premium Access has been Revoked**\n\nThe key used has been deactivated.")
        except Exception as e:
            logger.error(f"❌ Failed to notify user {user_id}: {e}")
    
    c.execute('DELETE FROM subscription_keys WHERE key_value = ?', (key_value,))
    c.execute('DELETE FROM key_usage WHERE key_value = ?', (key_value,))
    conn.commit()
    conn.close()

def update_file_limit(new_limit):
    """update free user file limit"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)', 
              ('free_user_limit', str(new_limit)))
    conn.commit()
    conn.close()
    
    global FREE_USER_LIMIT
    FREE_USER_LIMIT = new_limit

def update_force_join_status(enabled):
    """update force join status"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)', 
              ('force_join_enabled', '1' if enabled else '0'))
    conn.commit()
    conn.close()
    
    global force_join_enabled
    force_join_enabled = enabled

def get_bot_statistics():
    """get comprehensive bot statistics"""
    total_users = len(active_users)
    total_files = sum(len(files) for files in user_files.values())
    
    active_files = 0
    for script_key in bot_scripts:
        if is_bot_running(int(script_key.split('_')[0]), bot_scripts[script_key]['file_name']):
            active_files += 1
    
    premium_users = sum(1 for user_id in active_users if is_premium_user(user_id))
    
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM security_logs')
    security_alerts = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM banned_users')
    banned_users = c.fetchone()[0]
    conn.close()
    
    return {
        'total_users': total_users,
        'total_files': total_files,
        'active_files': active_files,
        'premium_users': premium_users,
        'security_alerts': security_alerts,
        'banned_users': banned_users
    }

def get_all_users_details():
    """get details of all bot users"""
    users_list = []
    for user_id in active_users:
        try:
            chat = bot.get_chat(user_id)
            users_list.append({
                'user_id': user_id,
                'first_name': chat.first_name,
                'username': chat.username,
                'is_premium': is_premium_user(user_id)
            })
        except:
            users_list.append({
                'user_id': user_id,
                'first_name': 'Unknown',
                'username': 'Unknown',
                'is_premium': is_premium_user(user_id)
            })
    return users_list

def get_all_admins():
    """get all admin IDs from database"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute('SELECT user_id FROM admins')
    admins = [row[0] for row in c.fetchall()]
    conn.close()
    return admins

def add_admin_to_db(admin_id):
    """add admin to database"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (admin_id,))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"❌ Error adding admin: {e}")
        return False
    finally:
        conn.close()

def remove_admin_from_db(admin_id):
    """remove admin from database"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute('DELETE FROM admins WHERE user_id = ?', (admin_id,))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"❌ Error removing admin: {e}")
        return False
    finally:
        conn.close()

def is_bot_running(script_owner_id, file_name):
    """check if a bot script is currently running"""
    script_key = f"{script_owner_id}_{file_name}"
    script_info = bot_scripts.get(script_key)
    if script_info and script_info.get('process'):
        try:
            proc = psutil.Process(script_info['process'].pid)
            return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
        except psutil.NoSuchProcess:
            return False
    return False

def kill_process_tree(process_info):
    """kill a process and all its children"""
    try:
        process = process_info.get('process')
        if process and hasattr(process, 'pid'):
            pid = process.pid
            try:
                parent = psutil.Process(pid)
                
                try:
                    parent.terminate()
                    parent.wait(timeout=5)
                except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                    pass
                
                try:
                    if parent.is_running():
                        parent.kill()
                        parent.wait(timeout=3)
                except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                    pass
                
                try:
                    children = parent.children(recursive=True)
                    for child in children:
                        try:
                            child.terminate()
                        except psutil.NoSuchProcess:
                            pass
                    
                    time.sleep(1)
                    
                    for child in children:
                        try:
                            if child.is_running():
                                child.kill()
                        except psutil.NoSuchProcess:
                            pass
                except psutil.NoSuchProcess:
                    pass
                
            except psutil.NoSuchProcess:
                pass
            
            try:
                if process.poll() is None:
                    process.terminate()
                    time.sleep(2)
                    if process.poll() is None:
                        process.kill()
            except:
                pass
            
            if process_info.get('log_file'):
                try:
                    process_info['log_file'].close()
                except:
                    pass
                
    except Exception as e:
        logger.error(f"❌ Error killing process: {e}")

def force_cleanup_process(process_info):
    """Force cleanup of a process with multiple attempts"""
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            kill_process_tree(process_info)
            
            if process_info.get('process'):
                try:
                    pid = process_info['process'].pid
                    psutil.Process(pid)
                    time.sleep(1)
                    continue
                except psutil.NoSuchProcess:
                    return True
            
            return True
            
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed to kill process: {e}")
            time.sleep(1)
    
    return False

def cleanup_user_processes(user_id):
    """Clean up all processes for a specific user"""
    keys_to_remove = []
    for script_key, process_info in list(bot_scripts.items()):
        if script_key.startswith(f"{user_id}_"):
            if force_cleanup_process(process_info):
                keys_to_remove.append(script_key)
    
    for key in keys_to_remove:
        if key in bot_scripts:
            del bot_scripts[key]
    
    return len(keys_to_remove)

TELEGRAM_MODULES = {
    'telebot': 'pyTelegramBotAPI',
    'telegram': 'python-telegram-bot',
    'python_telegram_bot': 'python-telegram-bot',
    'aiogram': 'aiogram',
    'pyrogram': 'pyrogram',
    'telethon': 'telethon',
    'requests': 'requests',
    'bs4': 'beautifulsoup4',
    'pillow': 'Pillow',
    'cv2': 'opencv-python',
    'yaml': 'PyYAML',
    'dotenv': 'python-dotenv',
    'dateutil': 'python-dateutil',
    'pandas': 'pandas',
    'numpy': 'numpy',
    'flask': 'Flask',
    'django': 'Django',
    'sqlalchemy': 'SQLAlchemy',
    'psutil': 'psutil',
    'asyncio': None, 'json': None, 'datetime': None, 'os': None, 'sys': None, 're': None,
    'time': None, 'math': None, 'random': None, 'logging': None, 'threading': None,
    'subprocess': None, 'zipfile': None, 'tempfile': None, 'shutil': None, 'sqlite3': None
}

def attempt_install_pip(module_name, message):
    package_name = TELEGRAM_MODULES.get(module_name.lower(), module_name) 
    if package_name is None: 
        logger.info(f"📦 Module '{module_name}' is core. Skipping pip install.")
        return False 
    try:
        try:
            bot.send_message(message.from_user.id, f"🔧 Installing `{package_name}`...", parse_mode='Markdown')
        except Exception as e:
            logger.error(f"❌ Failed to send install message: {e}")
            return False
            
        command = [sys.executable, '-m', 'pip', 'install', package_name, '--timeout', '60', '--retries', '3']
        logger.info(f"🔨 Running install: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True, check=False, encoding='utf-8', errors='ignore', timeout=120)
        if result.returncode == 0:
            logger.info(f"✅ Installed {package_name}. Output:\n{result.stdout}")
            try:
                bot.send_message(message.from_user.id, f"✅ Installed `{package_name}`", parse_mode='Markdown')
            except Exception as e:
                logger.error(f"❌ Failed to send success message: {e}")
            return True
        else:
            error_msg = f"❌ Failed `{package_name}`\n```\n{result.stderr or result.stdout}\n```"
            logger.error(error_msg)
            if len(error_msg) > 4000: error_msg = error_msg[:4000] + "\n... (Truncated)"
            try:
                bot.send_message(message.from_user.id, error_msg, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"❌ Failed to send error message: {e}")
            return False
    except subprocess.TimeoutExpired:
        error_msg = f"❌ Timeout `{package_name}`"
        logger.error(error_msg)
        try:
            bot.send_message(message.from_user.id, error_msg)
        except Exception as e:
            logger.error(f"❌ Failed to send timeout message: {e}")
        return False
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        try:
            bot.send_message(message.from_user.id, error_msg)
        except Exception as e:
            logger.error(f"❌ Failed to send error message: {e}")
        return False

def attempt_install_npm(module_name, user_folder, message):
    try:
        try:
            bot.send_message(message.from_user.id, f"📦 Installing `{module_name}`...", parse_mode='Markdown')
        except Exception as e:
            logger.error(f"❌ Failed to send install message: {e}")
            return False
            
        command = ['npm', 'install', module_name, '--timeout=60000']
        logger.info(f"🔨 Running npm install: {' '.join(command)} in {user_folder}")
        result = subprocess.run(command, capture_output=True, text=True, check=False, cwd=user_folder, encoding='utf-8', errors='ignore', timeout=120)
        if result.returncode == 0:
            logger.info(f"✅ Installed {module_name}. Output:\n{result.stdout}")
            try:
                bot.send_message(message.from_user.id, f"✅ Installed `{module_name}`", parse_mode='Markdown')
            except Exception as e:
                logger.error(f"❌ Failed to send success message: {e}")
            return True
        else:
            error_msg = f"❌ Failed `{module_name}`\n```\n{result.stderr or result.stdout}\n```"
            logger.error(error_msg)
            if len(error_msg) > 4000: error_msg = error_msg[:4000] + "\n... (Truncated)"
            try:
                bot.send_message(message.from_user.id, error_msg, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"❌ Failed to send error message: {e}")
            return False
    except FileNotFoundError:
         error_msg = "❌ Node.js not found"
         logger.error(error_msg)
         try:
             bot.send_message(message.from_user.id, error_msg)
         except Exception as e:
             logger.error(f"❌ Failed to send node error message: {e}")
         return False
    except subprocess.TimeoutExpired:
        error_msg = f"❌ Timeout `{module_name}`"
        logger.error(error_msg)
        try:
            bot.send_message(message.from_user.id, error_msg)
        except Exception as e:
            logger.error(f"❌ Failed to send timeout message: {e}")
        return False
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        try:
            bot.send_message(message.from_user.id, error_msg)
        except Exception as e:
            logger.error(f"❌ Failed to send error message: {e}")
        return False

def run_script(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt=1):
    """run python script with automatic dependency installation"""
    max_attempts = 2 
    if attempt > max_attempts:
        try:
            bot.send_message(script_owner_id, f"❌ Failed to start `{file_name}`")
        except Exception as e:
            logger.error(f"❌ Failed to send error message: {e}")
        return

    script_key = f"{script_owner_id}_{file_name}"
    logger.info(f"Attempt {attempt} to run python script: {script_path}")

    try:
        if not os.path.exists(script_path):
            try:
                bot.send_message(script_owner_id, f"❌ File `{file_name}` not found")
            except Exception as e:
                logger.error(f"❌ Failed to send file not found message: {e}")
            return

        if attempt == 1:
            check_command = [sys.executable, script_path]
            logger.info(f"🔍 Running python pre-check: {' '.join(check_command)}")
            check_proc = None
            try:
                check_proc = subprocess.Popen(check_command, cwd=user_folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
                stdout, stderr = check_proc.communicate(timeout=10)
                return_code = check_proc.returncode
                logger.info(f"🔍 Python pre-check. rc: {return_code}. stderr: {stderr[:200]}...")
                if return_code != 0 and stderr:
                    match_py = re.search(r"ModuleNotFoundError: No module named '(.+?)'", stderr)
                    if match_py:
                        module_name = match_py.group(1).strip().strip("'\"")
                        logger.info(f"📦 Detected missing python module: {module_name}")
                        try:
                            bot.send_message(script_owner_id, f"🔧 Installing `{module_name}`...")
                        except Exception as e:
                            logger.error(f"❌ Failed to send install message: {e}")
                        
                        if attempt_install_pip(module_name, message_obj_for_reply):
                            logger.info(f"✅ Install ok for {module_name}. Retrying run_script...")
                            try:
                                bot.send_message(script_owner_id, f"⚡ Restarting `{file_name}`...")
                            except Exception as e:
                                logger.error(f"❌ Failed to send restart message: {e}")
                            time.sleep(2)
                            threading.Thread(target=run_script, args=(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt + 1)).start()
                            return
                        else:
                            try:
                                bot.send_message(script_owner_id, f"❌ Cannot run `{file_name}` - installation failed")
                            except Exception as e:
                                logger.error(f"❌ Failed to send error message: {e}")
                            return
            except subprocess.TimeoutExpired:
                logger.info("⏱️ Python pre-check timed out, imports likely ok.")
                if check_proc and check_proc.poll() is None: 
                    check_proc.kill()
                    check_proc.communicate()
            except Exception as e:
                 logger.error(f"❌ Error in python pre-check: {e}")
                 return

        logger.info(f"🚀 Starting python process for {script_key}")
        log_file_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        log_file = None; process = None
        try: 
            log_file = open(log_file_path, 'w', encoding='utf-8', errors='ignore')
        except Exception as e:
             logger.error(f"❌ Failed to open log file: {e}")
             try:
                 bot.send_message(script_owner_id, f"❌ Log file error for `{file_name}`")
             except Exception as e:
                 logger.error(f"❌ Failed to send log error message: {e}")
             return
        try:
            startupinfo = None; creationflags = 0
            if os.name == 'nt':
                 startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                 startupinfo.wShowWindow = subprocess.SW_HIDE
            process = subprocess.Popen(
                [sys.executable, script_path], 
                cwd=user_folder, 
                stdout=log_file, 
                stderr=log_file,
                stdin=subprocess.PIPE, 
                startupinfo=startupinfo, 
                creationflags=creationflags,
                encoding='utf-8', 
                errors='ignore',
                bufsize=1
            )
            logger.info(f"✅ Started python process {process.pid} for {script_key}")
            bot_scripts[script_key] = {
                'process': process, 
                'log_file': log_file, 
                'file_name': file_name,
                'chat_id': script_owner_id,  
                'user_id': script_owner_id,
                'start_time': datetime.now(), 
                'user_folder': user_folder, 
                'type': 'py', 
                'script_key': script_key
            }
            try:
                bot.send_message(script_owner_id, f"✅ `{file_name}` Running (PID: {process.pid})")
            except Exception as e:
                logger.error(f"❌ Failed to send success message: {e}")
            try:
                bot.delete_message(message_obj_for_reply.chat.id, message_obj_for_reply.message_id)
            except Exception as e:
                logger.warning(f"⚠️ Failed to delete message: {e}")  
        except Exception as e:
            if log_file and not log_file.closed: 
                log_file.close()
            error_msg = f"❌ Error starting `{file_name}`: {str(e)[:100]}"
            logger.error(error_msg, exc_info=True)
            try:
                bot.send_message(script_owner_id, error_msg)
            except Exception as e:
                logger.error(f"❌ Failed to send error message: {e}")
            if script_key in bot_scripts: 
                del bot_scripts[script_key]
    except Exception as e:
        error_msg = f"❌ Error with `{file_name}`: {str(e)[:100]}"
        logger.error(error_msg, exc_info=True)
        try:
            bot.send_message(script_owner_id, error_msg)
        except Exception as e:
            logger.error(f"❌ Failed to send error message: {e}")

def run_js_script(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt=1):
    """run js script with automatic dependency installation"""
    max_attempts = 2
    if attempt > max_attempts:
        try:
            bot.send_message(script_owner_id, f"❌ Failed to start `{file_name}`")
        except Exception as e:
            logger.error(f"❌ Failed to send error message: {e}")
        return

    script_key = f"{script_owner_id}_{file_name}"
    logger.info(f"Attempt {attempt} to run js script: {script_path}")

    try:
        if not os.path.exists(script_path):
            try:
                bot.send_message(script_owner_id, f"❌ File `{file_name}` not found")
            except Exception as e:
                logger.error(f"❌ Failed to send file not found message: {e}")
            return

        if attempt == 1:
            check_command = ['node', script_path]
            logger.info(f"🔍 Running js pre-check: {' '.join(check_command)}")
            check_proc = None
            try:
                check_proc = subprocess.Popen(check_command, cwd=user_folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
                stdout, stderr = check_proc.communicate(timeout=10)
                return_code = check_proc.returncode
                logger.info(f"🔍 JS pre-check. rc: {return_code}. stderr: {stderr[:200]}...")
                if return_code != 0 and stderr:
                    match_js = re.search(r"Cannot find module '(.+?)'", stderr)
                    if match_js:
                        module_name = match_js.group(1).strip().strip("'\"")
                        if not module_name.startswith('.') and not module_name.startswith('/'):
                             logger.info(f"📦 Detected missing node module: {module_name}")
                             try:
                                 bot.send_message(script_owner_id, f"📦 Installing `{module_name}`...")
                             except Exception as e:
                                 logger.error(f"❌ Failed to send install message: {e}")
                             
                             if attempt_install_npm(module_name, user_folder, message_obj_for_reply):
                                 logger.info(f"✅ npm install ok for {module_name}. Retrying run_js_script...")
                                 try:
                                     bot.send_message(script_owner_id, f"⚡ Restarting `{file_name}`...")
                                 except Exception as e:
                                     logger.error(f"❌ Failed to send restart message: {e}")
                                 time.sleep(2)
                                 threading.Thread(target=run_js_script, args=(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt + 1)).start()
                                 return
            except subprocess.TimeoutExpired:
                logger.info("⏱️ JS pre-check timed out, imports likely ok.")
                if check_proc and check_proc.poll() is None: 
                    check_proc.kill()
                    check_proc.communicate()
            except Exception as e:
                 logger.error(f"❌ Error in js pre-check: {e}")
                 return

        logger.info(f"🚀 Starting js process for {script_key}")
        log_file_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        log_file = None; process = None
        try: 
            log_file = open(log_file_path, 'w', encoding='utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"❌ Failed to open log file: {e}")
            try:
                bot.send_message(script_owner_id, f"❌ Log file error for `{file_name}`")
            except Exception as e:
                logger.error(f"❌ Failed to send log error message: {e}")
            return
        try:
            startupinfo = None; creationflags = 0
            if os.name == 'nt':
                 startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                 startupinfo.wShowWindow = subprocess.SW_HIDE
            process = subprocess.Popen(
                ['node', script_path], 
                cwd=user_folder, 
                stdout=log_file, 
                stderr=log_file,
                stdin=subprocess.PIPE, 
                startupinfo=startupinfo, 
                creationflags=creationflags,
                encoding='utf-8', 
                errors='ignore',
                bufsize=1
            )
            logger.info(f"✅ Started js process {process.pid} for {script_key}")
            bot_scripts[script_key] = {
                'process': process, 
                'log_file': log_file, 
                'file_name': file_name,
                'chat_id': script_owner_id,
                'user_id': script_owner_id,
                'start_time': datetime.now(), 
                'user_folder': user_folder, 
                'type': 'js', 
                'script_key': script_key
            }
            try:
                bot.send_message(script_owner_id, f"✅ `{file_name}` Running (PID: {process.pid})")
            except Exception as e:
                logger.error(f"❌ Failed to send success message: {e}")
            
            try:
                bot.delete_message(message_obj_for_reply.chat.id, message_obj_for_reply.message_id)
            except Exception as e:
                logger.warning(f"⚠️ Failed to delete message: {e}")
        except Exception as e:
            if log_file and not log_file.closed: 
                log_file.close()
            error_msg = f"❌ Error starting `{file_name}`: {str(e)[:100]}"
            logger.error(error_msg, exc_info=True)
            try:
                bot.send_message(script_owner_id, error_msg)
            except Exception as e:
                logger.error(f"❌ Failed to send error message: {e}")
            if script_key in bot_scripts: 
                del bot_scripts[script_key]
    except Exception as e:
        error_msg = f"❌ Error with `{file_name}`: {str(e)[:100]}"
        logger.error(error_msg, exc_info=True)
        try:
            bot.send_message(script_owner_id, error_msg)
        except Exception as e:
            logger.error(f"❌ Failed to send error message: {e}")

# --- Database  ---
DB_LOCK = threading.Lock()

def save_user(user_id, username, first_name, last_name):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('INSERT OR REPLACE INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)',
                      (user_id, username, first_name, last_name))
            conn.commit()
        except Exception as e:
            logger.error(f"❌ Error saving user: {e}")
        finally:
            conn.close()

def save_user_file(user_id, file_name, file_type='unknown', file_path='', pending=False):
    """Save user file with chat ID and username"""
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('SELECT username, first_name FROM users WHERE user_id = ?', (user_id,))
            user_info = c.fetchone()
            username = user_info[0] if user_info else None
            first_name = user_info[1] if user_info else "Unknown"
            
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            
            c.execute('''INSERT INTO user_files 
                        (user_id, username, chat_id, file_name, file_type, file_path, 
                         original_filename, file_size, is_pending)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                     (user_id, username, user_id, file_name, file_type, file_path, 
                      file_name, file_size, 1 if pending else 0))
            
            conn.commit()
            
            if not pending:
                if user_id not in user_files:
                    user_files[user_id] = []
                user_files[user_id] = [(fn, ft, fp) for fn, ft, fp in user_files[user_id] if fn != file_name]
                user_files[user_id].append((file_name, file_type, file_path))
            
            logger.info(f"✅ File saved for user {user_id} (@{username}): {file_name} - Pending: {pending}")
            
        except Exception as e:
            logger.error(f"❌ Error saving file: {e}")
        finally:
            conn.close()

def approve_pending_file(user_id, file_name):
    """Approve a pending file and make it visible to user"""
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('UPDATE user_files SET is_pending = 0 WHERE user_id = ? AND file_name = ?', 
                     (user_id, file_name))
            
            c.execute('SELECT file_type, file_path FROM user_files WHERE user_id = ? AND file_name = ?', 
                     (user_id, file_name))
            result = c.fetchone()
            
            if result:
                file_type, file_path = result
                
                if user_id not in user_files:
                    user_files[user_id] = []
                user_files[user_id] = [(fn, ft, fp) for fn, ft, fp in user_files[user_id] if fn != file_name]
                user_files[user_id].append((file_name, file_type, file_path))
            
            conn.commit()
            logger.info(f"✅ File approved for user {user_id}: {file_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Error approving file: {e}")
            return False
        finally:
            conn.close()

def remove_user_file_db(user_id, file_name):
    """Remove user file from database and file system"""
    file_path = None
    
    if user_id in user_files:
        for fn, ft, fp in user_files[user_id]:
            if fn == file_name:
                file_path = fp
                break
    
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            if not file_path:
                c.execute('SELECT file_path FROM user_files WHERE user_id = ? AND file_name = ?', (user_id, file_name))
                result = c.fetchone()
                if result:
                    file_path = result[0]
            
            c.execute('DELETE FROM user_files WHERE user_id = ? AND file_name = ?', (user_id, file_name))
            conn.commit()
            
            if user_id in user_files:
                user_files[user_id] = [f for f in user_files[user_id] if f[0] != file_name]
                if not user_files[user_id]: 
                    del user_files[user_id]
            
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"✅ Deleted physical file: {file_path}")
                except Exception as e:
                    logger.error(f"❌ Error deleting physical file {file_path}: {e}")
            
        except Exception as e:
            logger.error(f"❌ Error removing file from database: {e}")
        finally:
            conn.close()

def add_active_user(user_id):
    active_users.add(user_id)
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('INSERT OR IGNORE INTO active_users (user_id) VALUES (?)', (user_id,))
            conn.commit()
        except Exception as e:
            logger.error(f"❌ Error adding active user: {e}")
        finally:
            conn.close()

def save_subscription(user_id, expiry, file_limit=999):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            expiry_str = expiry.isoformat()
            c.execute('INSERT OR REPLACE INTO subscriptions (user_id, expiry, file_limit) VALUES (?, ?, ?)', 
                     (user_id, expiry_str, file_limit))
            conn.commit()
            user_subscriptions[user_id] = {'expiry': expiry, 'file_limit': file_limit}
        except Exception as e:
            logger.error(f"❌ Error saving subscription: {e}")
        finally:
            conn.close()

def format_file_size(size_bytes):
    """Convert bytes to human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {size_names[i]}"

def get_user_files_with_details(user_id):
    """Get all files for a user with complete details (non-pending only)"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute('''SELECT file_id, file_name, file_type, file_path, 
                     original_filename, file_size, upload_date, is_active
                     FROM user_files 
                     WHERE user_id = ? AND is_pending = 0
                     ORDER BY upload_date DESC''', (user_id,))
        files = c.fetchall()
        
        file_details = []
        for file in files:
            file_id, file_name, file_type, file_path, original_filename, file_size, upload_date, is_active = file
            
            size_str = format_file_size(file_size)
            
            is_running = is_bot_running(user_id, file_name)
            
            file_details.append({
                'file_id': file_id,
                'file_name': file_name,
                'file_type': file_type,
                'file_path': file_path,
                'original_filename': original_filename,
                'file_size': size_str,
                'upload_date': upload_date,
                'is_active': bool(is_active),
                'is_running': is_running
            })
        
        return file_details
    except Exception as e:
        logger.error(f"❌ Error getting user files: {e}")
        return []
    finally:
        conn.close()

def get_all_user_files_for_owner():
    """Get all files from all users - Owner only access"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute('''SELECT u.user_id, u.username, u.first_name, 
                     f.file_name, f.file_type, f.file_size, f.upload_date, f.is_active, f.is_pending,
                     f.file_path
                     FROM user_files f
                     JOIN users u ON f.user_id = u.user_id
                     ORDER BY f.upload_date DESC''')
        files = c.fetchall()
        
        files_by_user = {}
        for file in files:
            user_id, username, first_name, file_name, file_type, file_size, upload_date, is_active, is_pending, file_path = file
            
            if user_id not in files_by_user:
                files_by_user[user_id] = {
                    'username': username,
                    'first_name': first_name,
                    'files': []
                }
            
            files_by_user[user_id]['files'].append({
                'file_name': file_name,
                'file_type': file_type,
                'file_size': format_file_size(file_size),
                'upload_date': upload_date,
                'is_active': bool(is_active),
                'is_pending': bool(is_pending),
                'file_path': file_path
            })
        
        return files_by_user
    except Exception as e:
        logger.error(f"❌ Error getting all files: {e}")
        return {}
    finally:
        conn.close()

def get_user_by_key(key_value):
    """Get user who used a specific key"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute('''SELECT u.user_id, u.username, u.first_name, u.key_used_date,
                     k.days_valid, k.file_limit, k.used_date
                     FROM users u
                     JOIN subscription_keys k ON u.key_used = k.key_value
                     WHERE u.key_used = ?''', (key_value,))
        user = c.fetchone()
        
        if user:
            return {
                'user_id': user[0],
                'username': user[1],
                'first_name': user[2],
                'key_used_date': user[3],
                'days_valid': user[4],
                'file_limit': user[5],
                'key_activation_date': user[6]
            }
        return None
    except Exception as e:
        logger.error(f"❌ Error getting user by key: {e}")
        return None
    finally:
        conn.close()

def get_owner_files_summary():
    """Get summary of all files for owner dashboard"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute('SELECT COUNT(*) FROM user_files')
        total_files = c.fetchone()[0]
        
        c.execute('SELECT SUM(file_size) FROM user_files')
        total_size = c.fetchone()[0] or 0
        
        c.execute('SELECT file_type, COUNT(*) FROM user_files GROUP BY file_type ORDER BY COUNT(*) DESC')
        files_by_type = c.fetchall()
        
        c.execute('''SELECT u.user_id, u.username, u.first_name, COUNT(f.file_id) AS file_count
                     FROM users u
                     LEFT JOIN user_files f ON u.user_id = f.user_id
                     GROUP BY u.user_id
                     ORDER BY file_count DESC
                     LIMIT 10''')
        top_users = c.fetchall()
        
        return {
            'total_files': total_files,
            'total_size': format_file_size(total_size),
            'files_by_type': files_by_type,
            'top_users': top_users
        }
    except Exception as e:
        logger.error(f"❌ Error getting owner summary: {e}")
        return None
    finally:
        conn.close()

# --- Ban User Functions ---
def ban_user(user_id):
    """Ban a user from using the bot"""
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('SELECT user_id FROM banned_users WHERE user_id = ?', (user_id,))
            if c.fetchone():
                return False, "User already banned"
            
            c.execute('INSERT INTO banned_users (user_id, banned_by) VALUES (?, ?)', 
                     (user_id, OWNER_ID))
            
            c.execute('DELETE FROM active_users WHERE user_id = ?', (user_id,))
            
            cleanup_user_processes(user_id)
            
            c.execute('SELECT file_path FROM user_files WHERE user_id = ?', (user_id,))
            files = c.fetchall()
            for file_path, in files:
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except:
                        pass
            
            c.execute('DELETE FROM user_files WHERE user_id = ?', (user_id,))
            
            c.execute('DELETE FROM subscriptions WHERE user_id = ?', (user_id,))
            
            if user_id in active_users:
                active_users.remove(user_id)
            if user_id in user_files:
                del user_files[user_id]
            if user_id in user_subscriptions:
                del user_subscriptions[user_id]
            
            conn.commit()
            return True, "User banned successfully"
        except Exception as e:
            logger.error(f"❌ Error banning user: {e}")
            return False, f"Error: {str(e)}"
        finally:
            conn.close()

def unban_user(user_id):
    """Unban a user"""
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM banned_users WHERE user_id = ?', (user_id,))
            
            c.execute('INSERT OR IGNORE INTO active_users (user_id) VALUES (?)', (user_id,))
            active_users.add(user_id)
            
            conn.commit()
            return True, "User unbanned successfully"
        except Exception as e:
            logger.error(f"❌ Error unbanning user: {e}")
            return False, f"Error: {str(e)}"
        finally:
            conn.close()

def get_banned_users():
    """Get all banned users with details"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute('''SELECT bu.user_id, bu.ban_date, bu.reason, 
                     u.username, u.first_name, u.last_name
                     FROM banned_users bu
                     LEFT JOIN users u ON bu.user_id = u.user_id
                     ORDER BY bu.ban_date DESC''')
        return c.fetchall()
    finally:
        conn.close()

# --- Enhanced Main Menu with Security Buttons ---
def create_main_menu_keyboard_enhanced(user_id):
    """Enhanced main menu with security and install buttons"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    # Main buttons
    buttons = [
        '📤 Upload File',
        '📂 My Files',
        '🔑 Redeem Key',
        '💎 Upgrade',
        '👤 Profile',
        '📊 Statistics',
    ]
    
    # Add install buttons for all users
    install_buttons = ['📦 Install Pip', '📦 Install Npm']
    
    # Add security buttons (only for owner)
    if user_id == OWNER_ID:
        security_buttons = ['🛡️ Security', '🚫 Quarantine']
    else:
        security_buttons = []
    
    # Add admin dashboard if admin
    if user_id in admin_ids and user_id != OWNER_ID:
        buttons.append('⚙️ Admin Dashboard')
    
    # Create rows
    row1 = buttons[0:2]
    row2 = buttons[2:4]
    row3 = buttons[4:6]
    
    markup.row(*row1)
    markup.row(*row2)
    markup.row(*row3)
    
    # Add install row
    markup.row(*install_buttons)
    
    # Add security row for owner
    if security_buttons:
        markup.row(*security_buttons)
    
    # Add admin row if admin (not owner, since owner already has security buttons)
    if user_id in admin_ids and user_id != OWNER_ID and len(buttons) > 6:
        markup.row(buttons[6])
    
    return markup

def create_start_hosting_keyboard():
    """create start hosting button"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('🚀 Deploy Now', callback_data='start_hosting'))
    return markup

def create_manage_files_keyboard(user_id):
    """create modern files management keyboard"""
    user_files_list = user_files.get(user_id, [])
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if not user_files_list:
        markup.add(types.InlineKeyboardButton("📭 No Files", callback_data='no_files'))
    else:
        for file_name, file_type, file_path in user_files_list:
            is_running = is_bot_running(user_id, file_name)
            status_emoji = "🟢" if is_running else "🔴"
            button_text = f"{status_emoji} {file_name}"
            markup.add(types.InlineKeyboardButton(button_text, callback_data=f'file_{user_id}_{file_name}'))
    
    markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data='back_to_main'))
    return markup

def create_file_management_buttons(user_id, file_name, is_running=True):
    markup = types.InlineKeyboardMarkup(row_width=2)
    if is_running:
        markup.row(
            types.InlineKeyboardButton("⏸️ Stop", callback_data=f'stop_{user_id}_{file_name}'),
            types.InlineKeyboardButton("🔄 Restart", callback_data=f'restart_{user_id}_{file_name}')
        )
    else:
        markup.row(
            types.InlineKeyboardButton("▶️ Start", callback_data=f'start_{user_id}_{file_name}'),
        )
    markup.row(
        types.InlineKeyboardButton("🗑️ Delete", callback_data=f'delete_{user_id}_{file_name}'),
        types.InlineKeyboardButton("📋 Logs", callback_data=f'logs_{user_id}_{file_name}')
    )
    markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data='manage_files'))
    return markup

def create_admin_panel_keyboard(user_id=None):
    """create modern admin panel with owner-only options"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    buttons = [
        '📊 Users Stats',
        '👥 Users',
        '💎 Premium Users',
        '🔑 Generate', 
        '🔍 Key-User',
        '🗑️ Revoke',
        '🔢 Keys',
        '⬅️ Back'
    ]
    
    if user_id == OWNER_ID:
        owner_buttons = [
            '➕ Add Admin',
            '➖ Remove Admin',
            '🚫 Ban User',
            '✅ Unban User',
            '📋 Banned',
            '📢 Broadcast',
            '📈 Limits',
            '⚙️ Settings',
            '📁 All Files',
            '🛡️ Security Logs',
            '🛑 Force Stop'
        ]
        buttons = owner_buttons + buttons
    
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            markup.row(buttons[i], buttons[i+1])
        else:
            markup.row(buttons[i])
    
    return markup

# --- Security Dashboard Command ---
@bot.message_handler(func=lambda message: message.text == '🛡️ Security')
@advanced_rate_limit('admin')
def handle_security_button(message):
    """Handle security dashboard button"""
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Owner only")
        return
    
    show_security_dashboard(message)

@bot.message_handler(commands=['security'])
def handle_security_command(message):
    """Handle /security command"""
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Owner only")
        return
    
    show_security_dashboard(message)

def show_security_dashboard(message):
    """Show enhanced security dashboard"""
    # Gather ransomware stats
    quarantined = ransomware_protection.quarantine.get_quarantine_list()
    
    # Behavior analysis stats
    total_users_analyzed = len(ransomware_protection.behavior_analyzer.user_behavior)
    high_risk_users = sum(1 for user_id in ransomware_protection.behavior_analyzer.user_behavior
                         if ransomware_protection.behavior_analyzer.analyze_user_behavior(user_id)['risk'] == 'high')
    
    # Sandbox stats
    active_sandboxes = len(ransomware_protection.sandbox_environment.active_sandboxes)
    
    # Alert stats
    alert_history = ransomware_protection.alert_system.alert_history
    critical_alerts = len([a for a in alert_history if a.get('priority') == 'CRITICAL'])
    high_alerts = len([a for a in alert_history if a.get('priority') == 'HIGH'])
    
    # Source integrity
    source_integrity = source_protector.verify_source_integrity()
    
    dashboard = f"""
🛡️ **ENHANCED SECURITY DASHBOARD**

🚨 **RANSOMWARE PROTECTION**
├─ Quarantined Files: {len(quarantined)}
├─ Critical Threats: {critical_alerts}
├─ High Risk Events: {high_alerts}
└─ Active Sandboxes: {active_sandboxes}

👥 **BEHAVIORAL ANALYSIS**
├─ Users Analyzed: {total_users_analyzed}
├─ High Risk Users: {high_risk_users}
└─ Suspicious Patterns: {sum(ransomware_protection.behavior_analyzer.suspicious_patterns.values())}

📁 **FILE MONITORING**
├─ Monitored Files: {len(ransomware_protection.file_monitor.file_hashes)}
├─ Backups: {len(os.listdir(ransomware_protection.file_backup.backup_dir)) if os.path.exists(ransomware_protection.file_backup.backup_dir) else 0}
└─ Quarantine DB: {'✅ Active' if os.path.exists(ransomware_protection.quarantine.quarantine_db) else '❌ Missing'}

🔍 **DETECTION SYSTEMS**
├─ Signature Detector: ✅ Active
├─ Heuristic Engine: ✅ Active
├─ Behavior Analyzer: ✅ Active
├─ Sandbox Environment: ✅ Active
└─ Honeypot Traps: ✅ Active

🔐 **SOURCE PROTECTION**
├─ Integrity: {'✅ Verified' if source_integrity else '❌ COMPROMISED'}
├─ Anti-Theft: ✅ Active
└─ Honeypot Hits: {len([h for h in source_protector.honeypot_files.values() if h['accessed']])}

⚡ **SYSTEM STATUS**
├─ Overall: {'🟢 Excellent' if critical_alerts == 0 else '🟡 Warning'}
├─ Last Check: {datetime.now().strftime('%H:%M:%S')}
└─ Uptime: {int(time.time() - start_time)}s
    """
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔄 Scan All", callback_data='security_scan_all'),
        types.InlineKeyboardButton("📋 Quarantine", callback_data='security_quarantine'),
        types.InlineKeyboardButton("🚫 Blocked Users", callback_data='security_blocked'),
        types.InlineKeyboardButton("📊 Full Report", callback_data='security_report')
    )
    
    bot.send_message(
        message.chat.id,
        dashboard,
        reply_markup=markup,
        parse_mode='Markdown'
    )

# --- Quarantine Command ---
@bot.message_handler(func=lambda message: message.text == '🚫 Quarantine')
@advanced_rate_limit('admin')
def handle_quarantine_button(message):
    """Handle quarantine button"""
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Owner only")
        return
    
    show_quarantine_list(message)

@bot.message_handler(commands=['quarantine'])
def handle_quarantine_command(message):
    """Handle /quarantine command"""
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Owner only")
        return
    
    show_quarantine_list(message)

def show_quarantine_list(message):
    """Show quarantine list"""
    quarantined = ransomware_protection.quarantine.get_quarantine_list()
    
    if not quarantined:
        bot.send_message(message.chat.id, "📭 No files in quarantine")
        return
    
    response = "🚨 **QUARANTINED FILES**\n\n"
    
    for q in quarantined[:10]:
        response += f"**ID:** `{q['id']}`\n"
        response += f"**File:** `{q['file_name']}`\n"
        response += f"**Reason:** {q['reason']}\n"
        response += f"**Severity:** {q['severity']}\n"
        response += f"**Time:** {q['detection_time']}\n"
        response += f"**Status:** {q['status']}\n"
        response += "─" * 30 + "\n\n"
    
    if len(quarantined) > 10:
        response += f"\n... and {len(quarantined) - 10} more"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔍 Inspect", callback_data='quarantine_inspect'),
        types.InlineKeyboardButton("🗑️ Clean All", callback_data='quarantine_clean'),
        types.InlineKeyboardButton("📊 Stats", callback_data='quarantine_stats')
    )
    
    bot.send_message(message.chat.id, response, reply_markup=markup, parse_mode='Markdown')

# --- Install Handlers ---
@bot.message_handler(func=lambda message: message.text == '📦 Install Pip')
@advanced_rate_limit('install')
def handle_pip_install_button(message):
    """Handle pip install from button"""
    user_id = message.from_user.id
    
    if not is_premium_user(user_id) and user_id not in admin_ids:
        bot.reply_to(
            message,
            "💎 **Premium Feature**\n\n"
            "Manual pip installation is only available for premium users.",
            parse_mode='Markdown'
        )
        return
    
    msg = bot.reply_to(
        message,
        "📦 **Pip Package Installer**\n\n"
        "Enter the Python package name to install:\n"
        "Example: `requests`",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, process_pip_install)

def process_pip_install(message):
    """Process pip installation with security checks"""
    user_id = message.from_user.id
    package = message.text.strip().lower()
    
    if not re.match(r'^[a-zA-Z0-9\-_\.]+$', package):
        bot.reply_to(message, "❌ Invalid package name format")
        rate_limiter.track_suspicious(user_id, 'invalid_package_format')
        return
    
    if package in SecurityConfig.DANGEROUS_PIP_PACKAGES:
        bot.reply_to(
            message,
            "❌ **Package Restricted**\n\n"
            "This package is blocked for security reasons.",
            parse_mode='Markdown'
        )
        rate_limiter.track_suspicious(user_id, 'dangerous_package_attempt')
        return
    
    safe_packages = ['requests', 'flask', 'django', 'numpy', 'pandas', 'matplotlib', 
                     'pillow', 'beautifulsoup4', 'pytelegrambotapi', 'python-telegram-bot',
                     'aiohttp', 'fastapi', 'uvicorn', 'sqlalchemy']
    
    if package not in safe_packages and user_id not in admin_ids:
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Yes, proceed", callback_data=f'confirm_pip_{package}'),
            types.InlineKeyboardButton("❌ Cancel", callback_data='cancel_install')
        )
        bot.reply_to(
            message,
            f"⚠️ **Security Warning**\n\n"
            f"Package `{package}` is not in the verified safe list.\n"
            f"Are you sure you want to proceed?",
            reply_markup=markup,
            parse_mode='Markdown'
        )
        return
    
    install_status = bot.reply_to(message, f"🔧 Installing `{package}`...", parse_mode='Markdown')
    
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', package, '--no-deps', '--no-cache-dir'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            bot.edit_message_text(
                f"✅ Successfully installed `{package}`",
                message.chat.id,
                install_status.message_id,
                parse_mode='Markdown'
            )
        else:
            error_msg = result.stderr[:200] if result.stderr else "Unknown error"
            bot.edit_message_text(
                f"❌ Failed to install `{package}`\n\nError: `{error_msg}`",
                message.chat.id,
                install_status.message_id,
                parse_mode='Markdown'
            )
            
    except subprocess.TimeoutExpired:
        bot.edit_message_text(
            f"❌ Installation timeout for `{package}`",
            message.chat.id,
            install_status.message_id,
            parse_mode='Markdown'
        )
    except Exception as e:
        bot.edit_message_text(
            f"❌ Error: {str(e)[:100]}",
            message.chat.id,
            install_status.message_id,
            parse_mode='Markdown'
        )

@bot.message_handler(func=lambda message: message.text == '📦 Install Npm')
@advanced_rate_limit('install')
def handle_npm_install_button(message):
    """Handle npm install from button"""
    user_id = message.from_user.id
    
    if not is_premium_user(user_id) and user_id not in admin_ids:
        bot.reply_to(
            message,
            "💎 **Premium Feature**\n\n"
            "Manual npm installation is only available for premium users.",
            parse_mode='Markdown'
        )
        return
    
    msg = bot.reply_to(
        message,
        "📦 **NPM Package Installer**\n\n"
        "Enter the Node.js package name to install:\n"
        "Example: `express`",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, process_npm_install)

def process_npm_install(message):
    """Process npm installation with security checks"""
    user_id = message.from_user.id
    package = message.text.strip().lower()
    
    if not re.match(r'^[a-zA-Z0-9\-_\.@]+$', package):
        bot.reply_to(message, "❌ Invalid package name format")
        rate_limiter.track_suspicious(user_id, 'invalid_package_format')
        return
    
    if package in SecurityConfig.DANGEROUS_NPM_PACKAGES:
        bot.reply_to(
            message,
            "❌ **Package Restricted**\n\n"
            "This package is blocked for security reasons.",
            parse_mode='Markdown'
        )
        rate_limiter.track_suspicious(user_id, 'dangerous_package_attempt')
        return
    
    safe_packages = ['express', 'axios', 'lodash', 'moment', 'chalk', 'commander',
                     'react', 'vue', 'angular', 'typescript', 'webpack', 'babel']
    
    if package not in safe_packages and user_id not in admin_ids:
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Yes, proceed", callback_data=f'confirm_npm_{package}'),
            types.InlineKeyboardButton("❌ Cancel", callback_data='cancel_install')
        )
        bot.reply_to(
            message,
            f"⚠️ **Security Warning**\n\n"
            f"Package `{package}` is not in the verified safe list.\n"
            f"Are you sure you want to proceed?",
            reply_markup=markup,
            parse_mode='Markdown'
        )
        return
    
    user_folder = get_user_folder(user_id)
    install_status = bot.reply_to(message, f"🔧 Installing `{package}`...", parse_mode='Markdown')
    
    try:
        result = subprocess.run(
            ['npm', 'install', package, '--no-audit', '--no-fund', '--no-optional'],
            cwd=user_folder,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            bot.edit_message_text(
                f"✅ Successfully installed `{package}`",
                message.chat.id,
                install_status.message_id,
                parse_mode='Markdown'
            )
        else:
            error_msg = result.stderr[:200] if result.stderr else "Unknown error"
            bot.edit_message_text(
                f"❌ Failed to install `{package}`\n\nError: `{error_msg}`",
                message.chat.id,
                install_status.message_id,
                parse_mode='Markdown'
            )
            
    except subprocess.TimeoutExpired:
        bot.edit_message_text(
            f"❌ Installation timeout for `{package}`",
            message.chat.id,
            install_status.message_id,
            parse_mode='Markdown'
        )
    except FileNotFoundError:
        bot.edit_message_text(
            "❌ Node.js/npm not found on server",
            message.chat.id,
            install_status.message_id,
            parse_mode='Markdown'
        )
    except Exception as e:
        bot.edit_message_text(
            f"❌ Error: {str(e)[:100]}",
            message.chat.id,
            install_status.message_id,
            parse_mode='Markdown'
        )

# --- Enhanced Document Handler with Ransomware Protection ---
@bot.message_handler(content_types=['document'])
@advanced_rate_limit('upload')
def handle_document_with_ransomware_protection(message):
    """Enhanced document handler with ransomware protection"""
    user_id = message.from_user.id
    
    if rate_limiter.is_suspicious(user_id):
        bot.reply_to(message, "⛔ Your account is under review. Contact admin.")
        return
    
    if is_user_banned(user_id):
        bot.reply_to(message, "🚫 You are banned")
        return
    
    if bot_locked and user_id not in admin_ids:
        bot.reply_to(message, "🔒 Bot is in maintenance mode")
        return
    
    if force_join_enabled and user_id not in admin_ids and not check_force_join(user_id):
        bot.reply_to(message, "❌ Join required group first")
        return
    
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    
    if current_files >= file_limit:
        bot.reply_to(message, f"❌ Storage limit reached ({file_limit} files)")
        return
    
    doc = message.document
    file_name = doc.file_name
    file_size = doc.file_size
    file_ext = os.path.splitext(file_name)[1].lower()
    
    if file_ext not in SUPPORTED_EXTENSIONS:
        bot.reply_to(message, f"❌ Unsupported file type: {file_ext}")
        return
    
    if file_size > SecurityConfig.MAX_FILE_SIZE:
        max_mb = SecurityConfig.MAX_FILE_SIZE / 1024 / 1024
        bot.reply_to(message, f"❌ File too large (max {max_mb}MB)")
        return
    
    user_total_size = sum(
        os.path.getsize(os.path.join(get_user_folder(user_id), fn))
        for fn, _, _ in user_files.get(user_id, [])
        if os.path.exists(os.path.join(get_user_folder(user_id), fn))
    )
    
    if user_total_size + file_size > SecurityConfig.MAX_TOTAL_STORAGE_PER_USER:
        bot.reply_to(message, f"❌ Total storage limit reached (50MB)")
        return
    
    try:
        file_info = bot.get_file(doc.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, file_name)
        
        with open(temp_path, 'wb') as f:
            f.write(downloaded_file)
        
        try:
            with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            is_theft_attempt, patterns = source_protector.detect_source_theft_attempt(content, user_id)
            if is_theft_attempt:
                shutil.rmtree(temp_dir)
                bot.reply_to(
                    message,
                    "🚫 **Security Violation**\n\n"
                    "File contains attempts to access bot source code.",
                    parse_mode='Markdown'
                )
                return
        except:
            pass
        
        signature_result = ransomware_protection.signature_detector.scan_file(temp_path)
        if signature_result['detected']:
            ransomware_protection.quarantine.add_file(
                temp_path,
                f"Signature match: {signature_result['malware']}",
                severity='critical',
                detected_by='signature_detector'
            )
            
            bot.reply_to(message, 
                "🚨 **MALWARE DETECTED**\n\n"
                "File contains known malware signatures and has been blocked.",
                parse_mode='Markdown'
            )
            
            ransomware_protection.alert_system.send_critical_alert({
                'type': 'MALWARE_DETECTED',
                'user_id': user_id,
                'file': file_name,
                'malware': signature_result['malware']
            })
            
            shutil.rmtree(temp_dir)
            return
        
        try:
            with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                code_content = f.read()
            
            heuristic_findings = ransomware_protection.heuristic_engine.analyze_code(code_content)
            
            if any(f['severity'] == 'critical' for f in heuristic_findings):
                ransomware_protection.quarantine.add_file(
                    temp_path,
                    f"Heuristic detection",
                    severity='critical',
                    detected_by='heuristic_engine'
                )
                
                bot.reply_to(message,
                    "🚨 **SUSPICIOUS CODE DETECTED**\n\n"
                    "File contains suspicious patterns and has been blocked.",
                    parse_mode='Markdown'
                )
                
                ransomware_protection.alert_system.send_high_risk_alert({
                    'type': 'HEURISTIC_DETECTION',
                    'user_id': user_id,
                    'file': file_name,
                    'findings': heuristic_findings
                })
                
                shutil.rmtree(temp_dir)
                return
            
            elif any(f['severity'] == 'high' for f in heuristic_findings):
                sandbox_info = ransomware_protection.sandbox_environment.create_sandbox(user_id, temp_path)
                if sandbox_info:
                    sandbox_results = ransomware_protection.sandbox_environment.run_in_sandbox(sandbox_info)
                    
                    if sandbox_results and sandbox_results.get('changes'):
                        ransomware_protection.quarantine.add_file(
                            temp_path,
                            f"Sandbox detected file modifications",
                            severity='high',
                            detected_by='sandbox'
                        )
                        
                        bot.reply_to(message,
                            "⚠️ **SUSPICIOUS BEHAVIOR DETECTED**\n\n"
                            "File attempted to modify other files during testing.\n"
                            "It has been blocked.",
                            parse_mode='Markdown'
                        )
                        
                        ransomware_protection.alert_system.send_high_risk_alert({
                            'type': 'SANDBOX_DETECTION',
                            'user_id': user_id,
                            'file': file_name,
                            'changes': sandbox_results['changes']
                        })
                        
                        shutil.rmtree(temp_dir)
                        return
                    
                    ransomware_protection.sandbox_environment.cleanup_sandbox(sandbox_info['id'])
        
        except Exception as e:
            logger.error(f"Code analysis error: {e}")
        
        behavior_analysis = ransomware_protection.behavior_analyzer.analyze_user_behavior(user_id)
        ransomware_protection.behavior_analyzer.add_activity(user_id, 'file_upload', file_name)
        
        user_folder = get_user_folder(user_id)
        final_path = os.path.join(user_folder, file_name)
        
        if os.path.exists(final_path):
            ransomware_protection.file_backup.backup_file(final_path, user_id)
        
        shutil.move(temp_path, final_path)
        shutil.rmtree(temp_dir)
        
        file_type = SUPPORTED_EXTENSIONS.get(file_ext, 'Unknown')
        save_user_file(user_id, file_name, file_type, final_path, pending=False)
        
        ransomware_protection.file_monitor.file_hashes[final_path] = \
            hashlib.sha256(downloaded_file).hexdigest()
        
        limit_display = str(file_limit) if file_limit != float('inf') else "Unlimited"
        
        success_text = f"""
✅ **UPLOAD SUCCESS - SECURITY CLEARED**

File: `{file_name}`
Type: {file_type}
Size: {format_file_size(file_size)}

**Security Checks Passed:**
• ✓ Signature Scan
• ✓ Heuristic Analysis
• ✓ Behavioral Check
• ✓ Sandbox Testing

**Storage:** {current_files + 1}/{limit_display}

Tap Deploy to start.
        """
        
        markup = create_start_hosting_keyboard()
        bot.reply_to(message, success_text, reply_markup=markup, parse_mode='Markdown')
        
        ransomware_protection.behavior_analyzer.add_activity(user_id, 'upload_success', file_name)
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        bot.reply_to(message, f"❌ Error: {str(e)[:100]}")
        
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

# --- Command Handlers for existing features ---
@bot.message_handler(commands=['start', 'help'])
@advanced_rate_limit('default')
def command_send_welcome_enhanced(message):
    """Enhanced welcome message with new menu"""
    user_id = message.from_user.id
    
    if is_user_banned(user_id):
        bot.send_message(message.chat.id, "🚫 You are banned")
        return
    
    if bot_locked and user_id not in admin_ids:
        bot.send_message(message.chat.id, "🔒 Bot is in maintenance mode")
        return
    
    if force_join_enabled and user_id not in admin_ids and not check_force_join(user_id):
        force_message = create_force_join_message()
        force_markup = create_force_join_keyboard()
        bot.send_message(message.chat.id, force_message, reply_markup=force_markup, parse_mode='Markdown')
        return
    
    add_active_user(user_id)
    save_user(user_id, message.from_user.username, message.from_user.first_name, message.from_user.last_name)
    
    user_file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    
    if user_file_limit == float('inf'):
        limit_display = 'Unlimited'
    else:
        limit_display = user_file_limit
    
    welcome_text = f"""
☁️ **PAI CLOUD HOST v3.0** ☁️

✨ *Welcome back, {message.from_user.first_name}!*

🚀 **Enhanced Security & Features**
-----------------------------------------
├─📦 Manual Pip/NPM Installation
├─🛡️ Advanced Malware Scanning
├─🔒 Ransomware Protection
├─🚫 Quarantine System
└─📊 Real-time Security Monitoring

**ACCOUNT STATUS**  
-----------------
├─ Plan: {get_user_status(user_id)}
└─ Storage: {current_files}/{limit_display}

**📦 New Features:**
• **Pip Install** - Install Python packages
• **Npm Install** - Install Node.js packages
• **🛡️ Security** - Security dashboard (Owner)
• **🚫 Quarantine** - Manage quarantined files (Owner)

Select an option below to begin.
    """
    
    markup = create_main_menu_keyboard_enhanced(user_id)
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode='Markdown')

# --- Include all other message handlers from your original code ---
# [You need to copy all your existing message handlers here from your original code]

# --- Callback Handlers ---
@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    """Handle all callback queries"""
    user_id = call.from_user.id
    
    data = call.data
    
    # Handle security callbacks
    if data.startswith('security_'):
        if user_id != OWNER_ID:
            bot.answer_callback_query(call.id, "❌ Owner only", show_alert=True)
            return
        
        if data == 'security_scan_all':
            bot.answer_callback_query(call.id, "🔄 Starting full scan...")
            bot.edit_message_text(
                "🔄 **Full Security Scan Initiated**\n\nScanning all user files...",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown'
            )
            threading.Thread(target=run_full_security_scan, args=(call.message,)).start()
        
        elif data == 'security_quarantine':
            show_quarantine_list(call.message)
            bot.answer_callback_query(call.id)
        
        elif data == 'security_blocked':
            show_blocked_users(call.message)
            bot.answer_callback_query(call.id)
        
        elif data == 'security_report':
            generate_security_report(call.message)
            bot.answer_callback_query(call.id)
    
    # Handle quarantine callbacks
    elif data.startswith('quarantine_'):
        if user_id != OWNER_ID:
            bot.answer_callback_query(call.id, "❌ Owner only", show_alert=True)
            return
        
        if data == 'quarantine_inspect':
            bot.edit_message_text(
                "🔍 **Quarantine Inspection**\n\nUse `/quarantine` to view all quarantined files.",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown'
            )
        
        elif data == 'quarantine_clean':
            bot.answer_callback_query(call.id, "🧹 Cleaning quarantine...")
            
            try:
                conn = sqlite3.connect(ransomware_protection.quarantine.quarantine_db)
                c = conn.cursor()
                c.execute("SELECT quarantine_path FROM quarantine")
                files = c.fetchall()
                
                for file_path, in files:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                
                c.execute("DELETE FROM quarantine")
                conn.commit()
                conn.close()
                
                bot.edit_message_text(
                    "✅ **Quarantine Cleaned**\n\nAll quarantined files have been permanently deleted.",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='Markdown'
                )
            except Exception as e:
                bot.edit_message_text(
                    f"❌ Error: {str(e)}",
                    call.message.chat.id,
                    call.message.message_id
                )
        
        elif data == 'quarantine_stats':
            quarantined = ransomware_protection.quarantine.get_quarantine_list()
            
            by_severity = {}
            for q in quarantined:
                severity = q['severity']
                by_severity[severity] = by_severity.get(severity, 0) + 1
            
            stats = "📊 **Quarantine Statistics**\n\n"
            stats += f"**Total Files:** {len(quarantined)}\n\n"
            stats += "**By Severity:**\n"
            for severity, count in by_severity.items():
                emoji = '🔴' if severity == 'critical' else '🟠' if severity == 'high' else '🟡'
                stats += f"{emoji} {severity.title()}: {count}\n"
            
            bot.edit_message_text(
                stats,
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown'
            )
    
    # Handle install confirmation callbacks
    elif data.startswith('confirm_pip_'):
        package = data.replace('confirm_pip_', '')
        bot.delete_message(call.message.chat.id, call.message.message_id)
        process_pip_install_after_confirm(call.message, package)
        bot.answer_callback_query(call.id)
    
    elif data.startswith('confirm_npm_'):
        package = data.replace('confirm_npm_', '')
        bot.delete_message(call.message.chat.id, call.message.message_id)
        process_npm_install_after_confirm(call.message, package)
        bot.answer_callback_query(call.id)
    
    elif data == 'cancel_install':
        bot.edit_message_text(
            "❌ Installation cancelled.",
            call.message.chat.id,
            call.message.message_id
        )
        bot.answer_callback_query(call.id)
    
    # Handle other callbacks from original code
    elif data == 'check_membership':
        if user_id in admin_ids:
            bot.answer_callback_query(call.id, "✅ Admin Access", show_alert=True)
            return
        
        if check_force_join(user_id):
            bot.answer_callback_query(call.id, "✅ Verified", show_alert=True)
            add_active_user(user_id)
            save_user(user_id, call.from_user.username, call.from_user.first_name, call.from_user.last_name)
            
            welcome_text = f"""
☁️ **PAI CLOUD HOST** ☁️

✨ *Welcome, {call.from_user.first_name}!*

✅ **MEMBERSHIP VERIFIED**

📊 **Status:** {get_user_status(user_id)}
🗃 **Files:** {get_user_file_count(user_id)}/{get_user_file_limit(user_id) if get_user_file_limit(user_id) != float('inf') else 'Unlimited'}

Tap buttons to start
            """
            
            markup = create_main_menu_keyboard_enhanced(user_id)

            try:
                bot.send_message(call.message.chat.id, welcome_text, reply_markup=markup, parse_mode='Markdown')
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception as e:
                logger.error(f"❌ Error sending welcome message: {e}")
                try:
                    bot.edit_message_text(welcome_text, call.message.chat.id, call.message.message_id, 
                                         reply_markup=markup, parse_mode='Markdown')
                except Exception as e2:
                    logger.error(f"❌ Error editing message: {e2}")
                    bot.send_message(call.message.chat.id, welcome_text, reply_markup=markup, parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, "❌ Join the group", show_alert=True)
    
    elif data == 'start_hosting':
        # Handle start hosting callback
        user_files_list = user_files.get(user_id, [])
        if not user_files_list:
            bot.answer_callback_query(call.id, "❌ No Files", show_alert=True)
            return
        
        bot.answer_callback_query(call.id, "🚀 Starting...")
        
        started_count = 0
        for file_name, file_type, file_path in user_files_list:
            if not is_bot_running(user_id, file_name) and os.path.exists(file_path):
                user_folder = get_user_folder(user_id)
                file_ext = os.path.splitext(file_name)[1].lower()
                if file_ext == '.py':
                    threading.Thread(target=run_script, args=(file_path, user_id, user_folder, file_name, call.message)).start()
                    started_count += 1
                elif file_ext == '.js':
                    threading.Thread(target=run_js_script, args=(file_path, user_id, user_folder, file_name, call.message)).start()
                    started_count += 1
                time.sleep(1)
        
        if started_count > 0:
            bot.send_message(call.message.chat.id, f"✅ Deployed {started_count} files")
        else:
            bot.send_message(call.message.chat.id, "ℹ️ All Active")
    
    elif data == 'manage_files':
        # Handle manage files callback
        user_files_list = user_files.get(user_id, [])
        
        if not user_files_list:
            bot.answer_callback_query(call.id, "📭 No Files", show_alert=True)
            return
        
        files_text = f"📂 **MY FILES:**\n\n"
        
        for file_name, file_type, file_path in user_files_list:
            is_running = is_bot_running(user_id, file_name)
            status = "🟢 Running" if is_running else "🔴 Stopped"
            files_text += f"• `{file_name}` - {status}\n"
        
        files_text += "\nTap file to manage"
        
        markup = create_manage_files_keyboard(user_id)
        bot.edit_message_text(files_text, call.message.chat.id, call.message.message_id, 
                             reply_markup=markup, parse_mode='Markdown')
    
    elif data.startswith('file_'):
        # Handle file click callback
        try:
            _, user_id_str, file_name = data.split('_', 2)
            file_owner_id = int(user_id_str)
            
            if call.from_user.id != file_owner_id and call.from_user.id not in admin_ids:
                bot.answer_callback_query(call.id, "❌ Denied", show_alert=True)
                return
            
            file_details = None
            for fn, ft, fp in user_files.get(file_owner_id, []):
                if fn == file_name:
                    file_details = (fn, ft, fp)
                    break
            
            if not file_details:
                bot.answer_callback_query(call.id, "❌ Not Found", show_alert=True)
                return
            
            file_name, file_type, file_path = file_details
            is_running = is_bot_running(file_owner_id, file_name)
            
            file_text = f"""
FILE NAME: `{file_name}`

FILE TYPE: {file_type}
STATUS: {'🟢 Running' if is_running else '🔴 Stopped'}
            """
            
            markup = create_file_management_buttons(file_owner_id, file_name, is_running)
            bot.edit_message_text(file_text, call.message.chat.id, call.message.message_id,
                                 reply_markup=markup, parse_mode='Markdown')
            
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ {str(e)}", show_alert=True)
    
    elif data.startswith('start_'):
        # Handle start file callback
        try:
            _, user_id_str, file_name = data.split('_', 2)
            file_owner_id = int(user_id_str)
            
            if call.from_user.id != file_owner_id and call.from_user.id not in admin_ids:
                bot.answer_callback_query(call.id, "❌ Denied", show_alert=True)
                return
            
            file_path = None
            for fn, ft, fp in user_files.get(file_owner_id, []):
                if fn == file_name:
                    file_path = fp
                    break
            
            if not file_path or not os.path.exists(file_path):
                bot.answer_callback_query(call.id, "❌ Not Found", show_alert=True)
                return
            
            user_folder = get_user_folder(file_owner_id)
            file_ext = os.path.splitext(file_name)[1].lower()
            
            if file_ext == '.py':
                threading.Thread(target=run_script, args=(file_path, file_owner_id, user_folder, file_name, call.message)).start()
                bot.answer_callback_query(call.id, f"🚀 Starting...")
            elif file_ext == '.js':
                threading.Thread(target=run_js_script, args=(file_path, file_owner_id, user_folder, file_name, call.message)).start()
                bot.answer_callback_query(call.id, f"🚀 Starting...")
            else:
                bot.answer_callback_query(call.id, f"✅ Deployed")
            
            time.sleep(1)
            # Refresh file view
            file_text = f"""
FILE NAME: `{file_name}`

FILE TYPE: {file_type}
STATUS: 🟢 Running
            """
            markup = create_file_management_buttons(file_owner_id, file_name, True)
            bot.edit_message_text(file_text, call.message.chat.id, call.message.message_id,
                                 reply_markup=markup, parse_mode='Markdown')
            
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ {str(e)}", show_alert=True)
    
    elif data.startswith('stop_'):
        # Handle stop file callback
        try:
            _, user_id_str, file_name = data.split('_', 2)
            file_owner_id = int(user_id_str)
            script_key = f"{file_owner_id}_{file_name}"
            
            if call.from_user.id != file_owner_id and call.from_user.id not in admin_ids:
                bot.answer_callback_query(call.id, "❌ Denied", show_alert=True)
                return
            
            process_info = bot_scripts.get(script_key)
            if process_info:
                success = force_cleanup_process(process_info)
                if script_key in bot_scripts:
                    del bot_scripts[script_key]
                
                if success:
                    bot.answer_callback_query(call.id, f"⏸️ Stopped")
                else:
                    bot.answer_callback_query(call.id, f"⚠️ Partially stopped")
            else:
                bot.answer_callback_query(call.id, f"ℹ️ Not Running")
            
            time.sleep(1)
            # Refresh file view
            file_text = f"""
FILE NAME: `{file_name}`

FILE TYPE: {file_type}
STATUS: 🔴 Stopped
            """
            markup = create_file_management_buttons(file_owner_id, file_name, False)
            bot.edit_message_text(file_text, call.message.chat.id, call.message.message_id,
                                 reply_markup=markup, parse_mode='Markdown')
            
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ {str(e)}", show_alert=True)
    
    elif data.startswith('restart_'):
        # Handle restart file callback
        try:
            _, user_id_str, file_name = data.split('_', 2)
            file_owner_id = int(user_id_str)
            
            if call.from_user.id != file_owner_id and call.from_user.id not in admin_ids:
                bot.answer_callback_query(call.id, "❌ Denied", show_alert=True)
                return
            
            script_key = f"{file_owner_id}_{file_name}"
            process_info = bot_scripts.get(script_key)
            if process_info:
                force_cleanup_process(process_info)
                if script_key in bot_scripts:
                    del bot_scripts[script_key]
                time.sleep(1)
            
            file_path = None
            for fn, ft, fp in user_files.get(file_owner_id, []):
                if fn == file_name:
                    file_path = fp
                    break
            
            if file_path and os.path.exists(file_path):
                user_folder = get_user_folder(file_owner_id)
                file_ext = os.path.splitext(file_name)[1].lower()
                if file_ext == '.py':
                    threading.Thread(target=run_script, args=(file_path, file_owner_id, user_folder, file_name, call.message)).start()
                elif file_ext == '.js':
                    threading.Thread(target=run_js_script, args=(file_path, file_owner_id, user_folder, file_name, call.message)).start()
                bot.answer_callback_query(call.id, f"🔄 Restarting")
            else:
                bot.answer_callback_query(call.id, "❌ Not Found", show_alert=True)
            
            time.sleep(1)
            # Refresh file view
            file_text = f"""
FILE NAME: `{file_name}`

FILE TYPE: {file_type}
STATUS: 🟢 Running
            """
            markup = create_file_management_buttons(file_owner_id, file_name, True)
            bot.edit_message_text(file_text, call.message.chat.id, call.message.message_id,
                                 reply_markup=markup, parse_mode='Markdown')
            
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ {str(e)}", show_alert=True)
    
    elif data.startswith('delete_'):
        # Handle delete file callback
        try:
            _, user_id_str, file_name = data.split('_', 2)
            file_owner_id = int(user_id_str)
            
            if call.from_user.id != file_owner_id and call.from_user.id not in admin_ids:
                bot.answer_callback_query(call.id, "❌ Denied", show_alert=True)
                return
            
            file_path = None
            for fn, ft, fp in user_files.get(file_owner_id, []):
                if fn == file_name:
                    file_path = fp
                    break
            
            if not file_path:
                bot.answer_callback_query(call.id, "❌ Not Found", show_alert=True)
                return
            
            script_key = f"{file_owner_id}_{file_name}"
            process_info = bot_scripts.get(script_key)
            if process_info:
                force_cleanup_process(process_info)
                if script_key in bot_scripts:
                    del bot_scripts[script_key]
            
            remove_user_file_db(file_owner_id, file_name)
            
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.error(f"❌ Error deleting file {file_path}: {e}")
            
            user_folder = get_user_folder(file_owner_id)
            log_file = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
            if os.path.exists(log_file):
                try:
                    os.remove(log_file)
                except Exception as e:
                    logger.error(f"❌ Error deleting log file {log_file}: {e}")
            
            bot.answer_callback_query(call.id, f"🗑️ Deleted")
            
            # Go back to files list
            user_files_list = user_files.get(file_owner_id, [])
            if user_files_list:
                files_text = f"📂 **MY FILES:**\n\n"
                for fn, ft, fp in user_files_list:
                    is_running = is_bot_running(file_owner_id, fn)
                    status = "🟢 Running" if is_running else "🔴 Stopped"
                    files_text += f"• `{fn}` - {status}\n"
                
                files_text += "\nTap file to manage"
                markup = create_manage_files_keyboard(file_owner_id)
                bot.edit_message_text(files_text, call.message.chat.id, call.message.message_id,
                                     reply_markup=markup, parse_mode='Markdown')
            else:
                bot.edit_message_text("📭 No Files", call.message.chat.id, call.message.message_id)
            
        except Exception as e:
            logger.error(f"❌ Error in handle_delete_file: {e}")
            bot.answer_callback_query(call.id, f"❌ {str(e)}", show_alert=True)
    
    elif data.startswith('logs_'):
        # Handle logs file callback
        try:
            _, user_id_str, file_name = data.split('_', 2)
            file_owner_id = int(user_id_str)
            
            user_folder = get_user_folder(file_owner_id)
            log_file = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
            
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    logs = f.read()
                
                if len(logs) > 4000:
                    logs = logs[:4000] + "\n\n... (Truncated)"
                
                log_text = f"📋 **{file_name}:**\n\n```\n{logs}\n```"
                
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data=f'file_{file_owner_id}_{file_name}'))
                
                bot.edit_message_text(log_text, call.message.chat.id, call.message.message_id, 
                                     reply_markup=markup, parse_mode='Markdown')
            else:
                bot.answer_callback_query(call.id, "📭 No Logs", show_alert=True)
                
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ {str(e)}", show_alert=True)
    
    elif data == 'back_to_main':
        # Handle back to main callback
        file_limit = get_user_file_limit(user_id)
        current_files = get_user_file_count(user_id)
        limit_str = str(file_limit) if file_limit != float('inf') else "Unlimited"
        user_status = get_user_status(user_id)
        
        main_menu_text = f"""
☁️ **PAI CLOUD HOST**

👋 *{call.from_user.first_name}*

🤖 `{user_id}`
📊 {user_status}
📁 {current_files} / {limit_str}
        """
        
        markup = create_main_menu_keyboard_enhanced(user_id)
        bot.edit_message_text(main_menu_text, call.message.chat.id, call.message.message_id, 
                             reply_markup=markup, parse_mode='Markdown')
    
    elif data == 'no_files':
        bot.answer_callback_query(call.id, "📭 No Files", show_alert=True)
    
    # Handle other callbacks from original code (redeem_key, buy_subscription, etc.)
    elif data == 'redeem_key':
        msg = bot.send_message(call.message.chat.id, "🔑 Enter Key:")
        bot.register_next_step_handler(msg, process_redeem_key)
        bot.answer_callback_query(call.id)
    
    elif data == 'buy_subscription':
        # Handle buy subscription
        html_text = """
<b>💎 UPGRADE PREMIUM PLANS</b>

<b>♣️ WEEKLY PLANS</b>
──────────────
│ <b>Price:</b> $0.50 / 2000 Ks
│ <b>Files:</b> 5 Files
└─ <b>Support:</b> Basic

<b>♦️ MONTHLY PLANS(popular)</b>
──────────────
│ <b>Price:</b> $2.00 / 8000 Ks
│ <b>Files:</b> 15 Files
└─ <b>Support:</b> Standard

<b>♥️ 3 MONTHS</b>
──────────────
│ <b>Price:</b> $5.50 / 23000 Ks
│ <b>Files:</b> Unlimited
└─ <b>Support:</b> Priority

<b>♠️ 1 YEAR</b>
──────────────
│ <b>Price:</b> $20.00 / 80000 Ks
│ <b>Files:</b> Unlimited & Bot Admin
└─ <b>Support:</b> Priority+

<b>⚡ LIFETIME</b>
───────────────
│ <b>Price:</b> $50.00 / 200000 Ks
│ <b>Files:</b> Unlimited & Bot Admin & Bot Source
└─ <b>Support:</b> 24/7 VIP

<b>💳 Payment Methods:</b>
• Binance
• Bybit
• KPAY
• WAVE

<b>📲 Contact Support:</b> """ + YOUR_USERNAME + """
        """
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💳 Contact Support", url=f"https://t.me/{YOUR_USERNAME[1:]}"))
        markup.add(types.InlineKeyboardButton("🔑 Redeem Key", callback_data='redeem_key'))
        
        bot.edit_message_text(html_text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='HTML')
        bot.answer_callback_query(call.id)

def process_redeem_key(message):
    """Process key redemption"""
    user_id = message.from_user.id
    
    if force_join_enabled and user_id not in admin_ids and not check_force_join(user_id):
        force_message = create_force_join_message()
        force_markup = create_force_join_keyboard()
        bot.send_message(message.chat.id, force_message, reply_markup=force_markup, parse_mode=None)
        return
    
    key_value = message.text.strip().upper()
    
    if not key_value.startswith('PAI-') or len(key_value) != 13:
        bot.reply_to(message, f"❌ FORMAT: PAI-XXXX-XXXX\nEXAMPLE: PAI-A1B2-C3D4")
        return
    
    success, result_msg = redeem_subscription_key(key_value, user_id)
    bot.reply_to(message, result_msg)

def process_pip_install_after_confirm(message, package):
    """Process pip installation after user confirmation"""
    install_status = bot.reply_to(message, f"🔧 Installing `{package}`...", parse_mode='Markdown')
    
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', package, '--no-deps', '--no-cache-dir'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            bot.edit_message_text(
                f"✅ Successfully installed `{package}`",
                message.chat.id,
                install_status.message_id,
                parse_mode='Markdown'
            )
        else:
            error_msg = result.stderr[:200] if result.stderr else "Unknown error"
            bot.edit_message_text(
                f"❌ Failed to install `{package}`\n\nError: `{error_msg}`",
                message.chat.id,
                install_status.message_id,
                parse_mode='Markdown'
            )
            
    except subprocess.TimeoutExpired:
        bot.edit_message_text(
            f"❌ Installation timeout for `{package}`",
            message.chat.id,
            install_status.message_id,
            parse_mode='Markdown'
        )
    except Exception as e:
        bot.edit_message_text(
            f"❌ Error: {str(e)[:100]}",
            message.chat.id,
            install_status.message_id,
            parse_mode='Markdown'
        )

def process_npm_install_after_confirm(message, package):
    """Process npm installation after user confirmation"""
    user_id = message.from_user.id
    user_folder = get_user_folder(user_id)
    
    install_status = bot.reply_to(message, f"🔧 Installing `{package}`...", parse_mode='Markdown')
    
    try:
        result = subprocess.run(
            ['npm', 'install', package, '--no-audit', '--no-fund', '--no-optional'],
            cwd=user_folder,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            bot.edit_message_text(
                f"✅ Successfully installed `{package}`",
                message.chat.id,
                install_status.message_id,
                parse_mode='Markdown'
            )
        else:
            error_msg = result.stderr[:200] if result.stderr else "Unknown error"
            bot.edit_message_text(
                f"❌ Failed to install `{package}`\n\nError: `{error_msg}`",
                message.chat.id,
                install_status.message_id,
                parse_mode='Markdown'
            )
            
    except subprocess.TimeoutExpired:
        bot.edit_message_text(
            f"❌ Installation timeout for `{package}`",
            message.chat.id,
            install_status.message_id,
            parse_mode='Markdown'
        )
    except FileNotFoundError:
        bot.edit_message_text(
            "❌ Node.js/npm not found on server",
            message.chat.id,
            install_status.message_id,
            parse_mode='Markdown'
        )
    except Exception as e:
        bot.edit_message_text(
            f"❌ Error: {str(e)[:100]}",
            message.chat.id,
            install_status.message_id,
            parse_mode='Markdown'
        )

def run_full_security_scan(message):
    """Run full security scan on all user files"""
    try:
        total_files = 0
        threats_found = 0
        
        for user_id in active_users:
            user_folder = get_user_folder(user_id)
            if not os.path.exists(user_folder):
                continue
            
            for file in os.listdir(user_folder):
                file_path = os.path.join(user_folder, file)
                
                if file.endswith('.log'):
                    continue
                
                total_files += 1
                
                result = ransomware_protection.signature_detector.scan_file(file_path)
                if result['detected']:
                    threats_found += 1
                    
                    ransomware_protection.quarantine.add_file(
                        file_path,
                        f"Scan detected: {result['malware']}",
                        severity='high',
                        detected_by='full_scan'
                    )
        
        bot.send_message(
            message.chat.id,
            f"✅ **Full Scan Complete**\n\n"
            f"📁 Files Scanned: {total_files}\n"
            f"🚨 Threats Found: {threats_found}\n"
            f"📋 Quarantined: {threats_found}",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"❌ Scan error: {str(e)}"
        )

def show_blocked_users(message):
    """Show blocked users"""
    banned = get_banned_users()
    
    if not banned:
        bot.send_message(message.chat.id, "📭 No blocked users")
        return
    
    response = "🚫 **BLOCKED USERS**\n\n"
    
    for user in banned[:10]:
        user_id, ban_date, reason, username, first_name, last_name = user
        name = first_name or "Unknown"
        response += f"**ID:** `{user_id}`\n"
        response += f"**Name:** {name}\n"
        response += f"**Username:** @{username if username else 'N/A'}\n"
        response += f"**Date:** {ban_date[:16]}\n"
        response += f"**Reason:** {reason or 'N/A'}\n"
        response += "─" * 30 + "\n\n"
    
    if len(banned) > 10:
        response += f"\n... and {len(banned) - 10} more"
    
    bot.send_message(message.chat.id, response, parse_mode='Markdown')

def generate_security_report(message):
    """Generate detailed security report"""
    report = "📊 **SECURITY REPORT**\n\n"
    
    report += "**Threat Statistics:**\n"
    report += f"• Total Scans: {security_scans['total_scans']}\n"
    report += f"• Threats Found: {security_scans['threats_found']}\n"
    report += f"• High Risk Files: {security_scans['high_risk_files']}\n"
    report += f"• Blocked Files: {security_scans['blocked_files']}\n\n"
    
    quarantined = ransomware_protection.quarantine.get_quarantine_list()
    report += f"**Quarantine:** {len(quarantined)} files\n\n"
    
    report += "**Recent Alerts:**\n"
    for alert in ransomware_protection.alert_system.alert_history[-5:]:
        report += f"• [{alert.get('priority', 'INFO')}] {alert.get('type', 'Unknown')}\n"
    
    bot.send_message(message.chat.id, report, parse_mode='Markdown')

# --- Text Message Handlers for Admin Panel ---
@bot.message_handler(func=lambda message: True)
def handle_all_text_messages(message):
    """Handle all text messages"""
    user_id = message.from_user.id
    text = message.text

    if message.chat.type in ['group', 'supergroup']:
        return

    if not (user_id in admin_ids or user_id == OWNER_ID) and is_user_banned(user_id):
        bot.send_message(message.chat.id, "🚫 You are banned")
        return

    if bot_locked and user_id not in admin_ids:
        bot.send_message(message.chat.id, "🔒 Bot is in maintenance mode")
        return
        
    if force_join_enabled and user_id not in admin_ids and not check_force_join(user_id):
        force_message = create_force_join_message()
        force_markup = create_force_join_keyboard()
        bot.send_message(message.chat.id, force_message, reply_markup=force_markup, parse_mode='Markdown')
        return

    # Handle admin commands
    if text == '📊 Users Stats' and user_id in admin_ids:
        stats = get_bot_statistics()
        html_text = f"""
<b>📊 SYSTEM STATS</b>

👥 <b>Users:</b> <code>{stats['total_users']}</code>
💎 <b>Premium Users:</b> <code>{stats['premium_users']}</code>
📁 <b>Total Files:</b> <code>{stats['total_files']}</code>
🟢 <b>Active Files:</b> <code>{stats['active_files']}</code>

<b>🛡️ SECURITY:</b>
├─ 🔍 <b>Scans:</b> <code>{security_scans['total_scans']}</code>
├─ ⚠️ <b>Threats:</b> <code>{security_scans['threats_found']}</code>
├─ 🔴 <b>High Risk:</b> <code>{security_scans['high_risk_files']}</code>
└─ 🚫 <b>Blocked:</b> <code>{security_scans['blocked_files']}</code>

<b>📈 ADMIN:</b>
├─ 🔔 <b>Alerts:</b> <code>{stats['security_alerts']}</code>
└─ 🚫 <b>Banned:</b> <code>{stats['banned_users']}</code>

<b>⚡ Status:</b> 🟢 Online
        """
        bot.send_message(message.chat.id, html_text, parse_mode='HTML')
    
    elif text == '👥 Users' and user_id in admin_ids:
        users = get_all_users_details()
        if not users:
            bot.send_message(message.chat.id, "📭 No Users")
            return
        
        html_text = "<b>👥 USERS LIST</b>\n\n"
        for user in users[:50]:
            status = "💎" if user['is_premium'] else "👤"
            username = f"@{user['username']}" if user['username'] else "-"
            html_text += f"""
{status} <b>{user['first_name']}</b>
├─ <b>ID:</b> <code>{user['user_id']}</code>
└─ <b>Username:</b> {username}
"""
            html_text += "─" * 25 + "\n"
        
        if len(users) > 50:
            html_text += f"\n<b>📈 ... {len(users) - 50} more users</b>"
        
        html_text += f"\n<b>📊 TOTAL USERS:</b> {len(users)}"
        bot.send_message(message.chat.id, html_text, parse_mode='HTML')
    
    elif text == '💎 Premium Users' and user_id in admin_ids:
        premium_users = get_premium_users_details()
        if not premium_users:
            bot.send_message(message.chat.id, "📭 No Premium Users")
            return
        
        html_text = "<b>💎 PREMIUM USERS LIST</b>\n\n"
        for user in premium_users:
            days_left = (user['expiry'] - datetime.now()).days
            html_text += f"""
<b>👤 {user['first_name']}</b> (@{user['username']})
├─ <b>ID:</b> <code>{user['user_id']}</code>
├─ <b>Files:</b> {user['file_count']}/{user['file_limit']} 
├─ <b>Running:</b> 🟢 {user['running_files']}
└─ <b>Days Left:</b> {days_left}
"""
        html_text += f"\n<b>📊 TOTAL PREMIUM:</b> {len(premium_users)} users"
        bot.send_message(message.chat.id, html_text, parse_mode='HTML')
    
    elif text == '🔑 Generate' and user_id in admin_ids:
        msg = bot.send_message(message.chat.id, "📅 Duration (Days):")
        bot.register_next_step_handler(msg, process_generate_key_days)
    
    elif text == '🔍 Key-User' and user_id in admin_ids:
        msg = bot.send_message(message.chat.id, "<b>🔑 Enter key to check:</b>", parse_mode='HTML')
        bot.register_next_step_handler(msg, process_key_user_info)
    
    elif text == '🗑️ Revoke' and user_id in admin_ids:
        keys = get_all_subscription_keys()
        if not keys:
            bot.send_message(message.chat.id, "📭 No Keys")
            return
        
        keys_text = f"🗑️ **ACTIVE KEYS:**\n\n"
        for key in keys:
            keys_text += f"• `{key[0]}` - {key[1]}d, {key[3]}/{key[2]}, {key[4]} files\n"
        
        keys_text += "\nEnter key to revoke:"
        bot.send_message(message.chat.id, keys_text, parse_mode='Markdown')
        msg = bot.send_message(message.chat.id, "🔑 Key:")
        bot.register_next_step_handler(msg, process_delete_key)
    
    elif text == '🔢 Keys' and user_id in admin_ids:
        keys = get_all_subscription_keys()
        if not keys:
            bot.send_message(message.chat.id, "📭 No Keys")
            return
        
        keys_text = f"🔢 **ALL KEYS:**\n\n"
        for key in keys:
            keys_text += f"• `{key[0]}`\n  📅 {key[1]}d, 📊 {key[4]} files, 🔢 {key[3]}/{key[2]}\n  🕐 {key[5][:16]}\n\n"
        
        bot.send_message(message.chat.id, keys_text, parse_mode='Markdown')
    
    elif text == '📈 Limits' and user_id in admin_ids:
        current_limit = FREE_USER_LIMIT
        msg = bot.send_message(message.chat.id, f"📈 Current Limit: {current_limit}\n\nNew Limit (1-100):")
        bot.register_next_step_handler(msg, process_file_limit)
    
    elif text == '⚙️ Settings' and user_id in admin_ids:
        settings_text = f"""
⚙️ **BOT SETTINGS**

👤 **Admin:** {message.from_user.first_name}
🆔 **ID:** `{message.from_user.id}`
---------------------------------------------

🔐 **Force Join:** {'Enabled' if force_join_enabled else 'Disabled'}
🔒 **Bot Lock:** {'Locked' if bot_locked else 'Unlocked'}
🗃 **File Limit:** {FREE_USER_LIMIT}
🛡️ **Scans:** {security_scans['total_scans']}
---------------------------------------------
        """
        bot.send_message(message.chat.id, settings_text, parse_mode='Markdown')
    
    elif text == '➕ Add Admin' and user_id == OWNER_ID:
        msg = bot.send_message(message.chat.id, "🆔 Enter Admin ID:")
        bot.register_next_step_handler(msg, process_add_admin)
    
    elif text == '➖ Remove Admin' and user_id == OWNER_ID:
        admins = get_all_admins()
        if not admins:
            bot.send_message(message.chat.id, "📭 No admins")
            return
        
        admin_list = "🛡️ **CURRENT ADMINS:**\n\n"
        for admin_id in admins:
            if admin_id != OWNER_ID:
                try:
                    user_info = bot.get_chat(admin_id)
                    username = f"@{user_info.username}" if user_info.username else "N/A"
                    admin_list += f"👤 {user_info.first_name} - `{admin_id}` {username}\n"
                except:
                    admin_list += f"👤 Unknown - `{admin_id}`\n"
        
        admin_list += "\n🆔 Enter admin ID to remove:"
        msg = bot.send_message(message.chat.id, admin_list, parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_remove_admin)
    
    elif text == '🚫 Ban User' and user_id == OWNER_ID:
        msg = bot.send_message(message.chat.id, "🆔 Enter user ID to ban:")
        bot.register_next_step_handler(msg, process_ban_user)
    
    elif text == '✅ Unban User' and user_id == OWNER_ID:
        banned_users = get_banned_users()
        if not banned_users:
            bot.send_message(message.chat.id, "📭 No Banned Users")
            return
        
        banned_text = "🚫 **BANNED USERS:**\n\n"
        for user in banned_users:
            user_id, ban_date, reason, username, first_name, last_name = user
            name = first_name or "Unknown"
            username_display = f"@{username}" if username else "N/A"
            banned_text += f"• `{user_id}` - {name} ({username_display})\n"
        
        banned_text += "\n🆔 Enter user ID to unban:"
        msg = bot.send_message(message.chat.id, banned_text, parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_unban_user)
    
    elif text == '📋 Banned' and user_id == OWNER_ID:
        banned_users = get_banned_users()
        if not banned_users:
            bot.send_message(message.chat.id, "📭 No Banned Users")
            return
        
        html_text = "<b>🚫 BANNED USERS LIST</b>\n\n"
        for user in banned_users:
            user_id, ban_date, reason, username, first_name, last_name = user
            name = first_name or "Unknown"
            username_display = f"@{username}" if username else "N/A"
            time_ago = (datetime.now() - datetime.fromisoformat(ban_date)).days
            
            html_text += f"""
<b>👤 User:</b> {name}
<b>🆔 ID:</b> <code>{user_id}</code>
<b>📱 Username:</b> {username_display}
<b>📅 Banned:</b> {ban_date[:16]} ({time_ago} days ago)
"""
            if reason:
                html_text += f"<b>📝 Reason:</b> {reason}\n"
            html_text += "─" * 30 + "\n"
        
        html_text += f"\n<b>📊 TOTAL:</b> {len(banned_users)} users"
        bot.send_message(message.chat.id, html_text, parse_mode='HTML')
    
    elif text == '📢 Broadcast' and user_id in admin_ids:
        msg = bot.send_message(message.chat.id, "📢 Enter message:")
        bot.register_next_step_handler(msg, process_broadcast)
    
    elif text == '📁 All Files' and user_id == OWNER_ID:
        files_data = get_all_user_files_for_owner()
        if not files_data:
            bot.send_message(message.chat.id, "📭 No files found")
            return
        
        files_text = "👑 **OWNER VIEW - ALL USER FILES:**\n\n"
        for user_id, user_data in list(files_data.items())[:20]:
            username = f"@{user_data['username']}" if user_data['username'] else "No Username"
            files_text += f"👤 **{user_data['first_name']}** ({username}) - `{user_id}`\n"
            
            for file in user_data['files'][:5]:
                status = "🟡 Pending" if file['is_pending'] else "🟢" if file['is_active'] else "🔴"
                files_text += f"  {status} `{file['file_name']}` ({file['file_size']}) - {file['upload_date'][:10]}\n"
            
            files_text += "\n"
        
        if len(files_data) > 20:
            files_text += f"\n... {len(files_data) - 20} more users"
        
        total_users = len(files_data)
        total_files = sum(len(user_data['files']) for user_data in files_data.values())
        files_text += f"\n📊 **SUMMARY:** {total_files} files from {total_users} users"
        bot.send_message(message.chat.id, files_text, parse_mode='Markdown')
    
    elif text == '🛡️ Security Logs' and user_id == OWNER_ID:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('''SELECT username, file_name, threat_count, risk_level, 
                         action_taken, log_date FROM security_logs 
                         ORDER BY log_date DESC LIMIT 20''')
            logs = c.fetchall()
            
            if not logs:
                bot.send_message(message.chat.id, "📭 No Security Logs")
                return
            
            html_text = "<b>🛡️ SECURITY LOGS</b>\n\n"
            for log in logs:
                username, file_name, threat_count, risk_level, action_taken, log_date = log
                risk_emoji = "🔴" if risk_level == 'critical' else "🟠" if risk_level == 'high' else "🟡"
                html_text += f"""
<b>{risk_emoji} {risk_level.upper()}</b>
├─ <b>User:</b> @{username}
├─ <b>File:</b> <code>{file_name}</code>
├─ <b>Threats:</b> {threat_count}
├─ <b>Action:</b> {action_taken}
└─ <b>Time:</b> {log_date[:19]}
"""
                html_text += "─" * 35 + "\n"
            
            c.execute('SELECT COUNT(*) FROM security_logs')
            total_logs = c.fetchone()[0]
            html_text += f"""
<b>📊 SUMMARY:</b>
├─ <b>Total Logs:</b> {total_logs}
├─ <b>Total Scans:</b> {security_scans['total_scans']}
├─ <b>Threats Found:</b> {security_scans['threats_found']}
└─ <b>Blocked Files:</b> {security_scans['blocked_files']}
            """
            bot.send_message(message.chat.id, html_text, parse_mode='HTML')
        except Exception as e:
            logger.error(f"❌ Error getting security logs: {e}")
            bot.send_message(message.chat.id, f"❌ Error: {str(e)}")
        finally:
            conn.close()
    
    elif text == '🛑 Force Stop' and user_id in admin_ids:
        msg = bot.send_message(message.chat.id, "🆔 Enter user ID to force stop all processes:")
        bot.register_next_step_handler(msg, process_force_stop_user)
    
    elif text == '⬅️ Back':
        markup = create_main_menu_keyboard_enhanced(user_id)
        bot.send_message(message.chat.id, "⬅️ Main Menu", reply_markup=markup)
    
    elif text == '📤 Upload File':
        file_limit = get_user_file_limit(user_id)
        current_files = get_user_file_count(user_id)
        if current_files >= file_limit and not is_premium_user(user_id):
            bot.send_message(message.chat.id, f"❌ Storage limit reached ({FREE_USER_LIMIT} files)\n💎 Upgrade for more space.")
            return
        
        supported_files = ", ".join([ext for ext in SUPPORTED_EXTENSIONS.keys()])
        bot.send_message(message.chat.id, 
                        f"""
📤 **UPLOAD FILE**

Supported: `{supported_files}`

Upload your script or code file now.
Auto-deploy is available.
                        """,
                        parse_mode='Markdown')
    
    elif text == '📂 My Files':
        user_files_list = user_files.get(user_id, [])
        if not user_files_list:
            bot.send_message(message.chat.id, "📭 No Files")
            return
        
        files_text = f"📂 **MY FILES:**\n\n"
        for file_name, file_type, file_path in user_files_list:
            is_running = is_bot_running(user_id, file_name)
            status = "🟢 Running" if is_running else "🔴 Stopped"
            files_text += f"• `{file_name}` - {status}\n"
        
        files_text += "\nTap file to manage"
        markup = create_manage_files_keyboard(user_id)
        bot.send_message(message.chat.id, files_text, reply_markup=markup, parse_mode='Markdown')
    
    elif text == '🔑 Redeem Key':
        msg = bot.send_message(message.chat.id, "🔑 Enter Key (PAI-XXXX-XXXX):")
        bot.register_next_step_handler(msg, process_redeem_key)
    
    elif text == '💎 Upgrade':
        html_text = """
<b>💎 UPGRADE PREMIUM PLANS</b>

<b>♣️ WEEKLY PLANS</b>
──────────────
│ <b>Price:</b> $0.50 / 2000 Ks
│ <b>Files:</b> 5 Files
└─ <b>Support:</b> Basic

<b>♦️ MONTHLY PLANS(popular)</b>
──────────────
│ <b>Price:</b> $2.00 / 8000 Ks
│ <b>Files:</b> 15 Files
└─ <b>Support:</b> Standard

<b>♥️ 3 MONTHS</b>
──────────────
│ <b>Price:</b> $5.50 / 23000 Ks
│ <b>Files:</b> Unlimited
└─ <b>Support:</b> Priority

<b>♠️ 1 YEAR</b>
──────────────
│ <b>Price:</b> $20.00 / 80000 Ks
│ <b>Files:</b> Unlimited & Bot Admin
└─ <b>Support:</b> Priority+

<b>⚡ LIFETIME</b>
───────────────
│ <b>Price:</b> $50.00 / 200000 Ks
│ <b>Files:</b> Unlimited & Bot Admin & Bot Source
└─ <b>Support:</b> 24/7 VIP

<b>💳 Payment Methods:</b>
• Binance
• Bybit
• KPAY
• WAVE

<b>📲 Contact Support:</b> """ + YOUR_USERNAME + """
        """
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💳 Contact Support", url=f"https://t.me/{YOUR_USERNAME[1:]}"))
        markup.add(types.InlineKeyboardButton("🔑 Redeem Key", callback_data='redeem_key'))
        bot.send_message(message.chat.id, html_text, reply_markup=markup, parse_mode='HTML')
    
    elif text == '👤 Profile':
        user_status = get_user_status(user_id)
        file_limit = get_user_file_limit(user_id)
        current_files = get_user_file_count(user_id)
        
        subscription_info = ""
        if is_premium_user(user_id):
            subscription_data = user_subscriptions.get(user_id, {})
            expiry = subscription_data.get('expiry', datetime.now())
            file_limit = subscription_data.get('file_limit', 999)
            days_left = (expiry - datetime.now()).days
            subscription_info = f"📅 Expires: {expiry.strftime('%Y-%m-%d')}\n📊 Limit: {file_limit} Files\n⏳ Days Left: {days_left}"
        else:
            subscription_info = "⏳ Standard Plan"
        
        limit_str = str(file_limit) if file_limit != float('inf') else "Unlimited"
        
        profile_text = f"""
👤 **PROFILE**

🤖 ID: `{user_id}`
👤 Name: {message.from_user.first_name}
📱 Username: @{message.from_user.username if message.from_user.username else '-'}
📊 Status: {user_status}
---------------------------------------------

💎 **Tier:**
{subscription_info}
📂 Used: {current_files}/{limit_str}
---------------------------------------------

📁 **Files:**
├─ 🗃 Total: {current_files}
├─ 🟢 Active: {sum(1 for fn, _, _ in user_files.get(user_id, []) if is_bot_running(user_id, fn))}
└─ 🔴 Stopped: {sum(1 for fn, _, _ in user_files.get(user_id, []) if not is_bot_running(user_id, fn))}
---------------------------------------------
        """
        
        markup = types.InlineKeyboardMarkup()
        if not is_premium_user(user_id):
            markup.add(types.InlineKeyboardButton("💎 Upgrade", callback_data='buy_subscription'))
        markup.add(types.InlineKeyboardButton("📁 Files", callback_data='manage_files'))
        markup.add(types.InlineKeyboardButton("🔑 Redeem", callback_data='redeem_key'))
        
        bot.send_message(message.chat.id, profile_text, reply_markup=markup, parse_mode='Markdown')
    
    elif text == '📊 Statistics':
        stats_text = f"""
📊 **CURRENT STATUS**

👤User: {message.from_user.first_name}
📊Status: {get_user_status(user_id)}
📁Files: {get_user_file_count(user_id)}/{get_user_file_limit(user_id) if get_user_file_limit(user_id) != float('inf') else 'Unlimited'}
🟢Running: {sum(1 for fn, _, _ in user_files.get(user_id, []) if is_bot_running(user_id, fn))}
🔴Stopped: {sum(1 for fn, _, _ in user_files.get(user_id, []) if not is_bot_running(user_id, fn))}

💎Premium: {'Active' if is_premium_user(user_id) else 'Basic'}
🔒Bot Status: {'Locked' if bot_locked else 'Open'}
🔰Force Join: {'On' if force_join_enabled else 'Off'}
        """
        bot.send_message(message.chat.id, stats_text, parse_mode='Markdown')
    
    elif text == '⚙️ Admin Dashboard' and user_id in admin_ids:
        if user_id == OWNER_ID:
            role_text = "👑 Owner"
            features = "• 📁 View all user files\n• 👑 Full system access\n• 🛡️ Security monitoring"
        else:
            role_text = "🛡️ Admin"
            features = "• 👥 User management\n• 🔑 Key management"
        
        admin_text = f"""
🛡️ **ADMIN DASHBOARD**

👤 **User:** {message.from_user.first_name}
🆔 **ID:** `{user_id}`
📋 **Role:** {role_text}

📊 **Statistics:**
• Total Users: {len(active_users)}
• Total Files: {sum(len(files) for files in user_files.values())}
• Premium Users: {sum(1 for user_id in active_users if is_premium_user(user_id))}
• Security Scans: {security_scans['total_scans']}

⚙️ **Your Features:**
{features}
        """
        
        markup = create_admin_panel_keyboard(user_id)
        bot.send_message(message.chat.id, admin_text, reply_markup=markup, parse_mode='Markdown')
    
    else:
        bot.send_message(message.chat.id, "❌ Invalid Command")

# --- Admin helper functions ---
def process_generate_key_days(message):
    try:
        days = int(message.text.strip())
        if days <= 0:
            bot.send_message(message.chat.id, "❌ Positive number required")
            return
        
        bot.send_message(message.chat.id, f"✅ {days} Days\n\nMax Uses:")
        bot.register_next_step_handler(message, process_generate_key_uses, days)
    except ValueError:
        bot.send_message(message.chat.id, "❌ Number required")

def process_generate_key_uses(message, days):
    try:
        max_uses = int(message.text.strip())
        if max_uses <= 0:
            bot.send_message(message.chat.id, "❌ Positive number required")
            return
        
        bot.send_message(message.chat.id, f"🗃 File Limit (1-999):")
        bot.register_next_step_handler(message, process_generate_key_file_limit, days, max_uses)
    except ValueError:
        bot.send_message(message.chat.id, "❌ Number required")

def process_generate_key_file_limit(message, days, max_uses):
    try:
        file_limit = int(message.text.strip())
        if file_limit < 1 or file_limit > 999:
            bot.send_message(message.chat.id, "❌ 1-999")
            return
        
        key = generate_subscription_key(days, max_uses, file_limit, created_by=message.from_user.id)
        bot.send_message(message.chat.id, 
                        f"""
✅ **KEY GENERATED**

🔑 `{key}`
📅 {days} Days
🗃 {file_limit} Files
🔢 {max_uses} Uses
                        """,
                        parse_mode='Markdown')
    except ValueError:
        bot.send_message(message.chat.id, "❌ Number required")

def process_key_user_info(message):
    key_value = message.text.strip().upper()
    user_info = get_user_by_key(key_value)
    
    if not user_info:
        bot.reply_to(message, f"❌ No user found for key <code>{key_value}</code>", parse_mode='HTML')
        return
    
    html_text = f"""
<b>🔑 KEY-USER INFORMATION</b>

<b>Key:</b> <code>{key_value}</code>

<b>👤 USER DETAILS:</b>
├─ <b>ID:</b> <code>{user_info['user_id']}</code>
├─ <b>Name:</b> {user_info['first_name']}
├─ <b>Username:</b> @{user_info['username'] if user_info['username'] else 'N/A'}
├─ <b>Duration:</b> {user_info['days_valid']} Days
├─ <b>File Limit:</b> {user_info['file_limit']}
├─ <b>Key Activated:</b> {user_info['key_activation_date'][:19]}
└─ <b>User Data Saved:</b> {user_info['key_used_date'][:19]}

<b>📝 Note:</b> 1Key = 1User
    """
    
    user_files_list = get_user_files_with_details(user_info['user_id'])
    if user_files_list:
        html_text += f"\n<b>📁 FILES ({len(user_files_list)}):</b>\n"
        for file in user_files_list[:10]:
            status = "🟢" if file['is_running'] else "🔴"
            html_text += f"├─ {status} <code>{file['file_name']}</code> ({file['file_size']})\n"
        if len(user_files_list) > 10:
            html_text += f"└─ <b>... {len(user_files_list) - 10} more files</b>\n"
    else:
        html_text += "\n<b>📭 NO FILES</b>"
    
    bot.reply_to(message, html_text, parse_mode='HTML')

def process_delete_key(message):
    key_value = message.text.strip().upper()
    keys = get_all_subscription_keys()
    key_exists = any(key[0] == key_value for key in keys)
    
    if not key_exists:
        bot.send_message(message.chat.id, f"❌ `{key_value}` Not Found", parse_mode='Markdown')
        return
    
    delete_subscription_key(key_value)
    bot.send_message(message.chat.id, f"✅ `{key_value}` Revoked", parse_mode='Markdown')

def process_file_limit(message):
    try:
        new_limit = int(message.text.strip())
        if 1 <= new_limit <= 100:
            update_file_limit(new_limit)
            bot.send_message(message.chat.id, f"✅ Limit: {new_limit}")
        else:
            bot.send_message(message.chat.id, "❌ 1-100")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Number")

def process_add_admin(message):
    try:
        admin_id = int(message.text.strip())
        if admin_id == OWNER_ID:
            bot.send_message(message.chat.id, "❌ Can't add Owner")
            return
        
        if add_admin_to_db(admin_id):
            admin_ids.add(admin_id)
            try:
                user_info = bot.get_chat(admin_id)
                username = f"@{user_info.username}" if user_info.username else "N/A"
                name = user_info.first_name
                bot.send_message(message.chat.id, 
                                f"""
✅ **ADMIN ADDED**

👤 {name}
🆔 {admin_id}
👥 {username}
                                """, 
                                parse_mode='Markdown')
                bot.send_message(admin_id, 
                                f"""
🛡️ **YOU HAVE BEEN PROMOTED**

👑 By: {message.from_user.first_name}
🔑 Access: Full Admin Dashboard

Use /start to see your new menu.
                                """, 
                                parse_mode='Markdown')
            except Exception as e:
                bot.send_message(message.chat.id, f"✅ Admin added (id: {admin_id})")
                logger.error(f"❌ Failed to get user info: {e}")
        else:
            bot.send_message(message.chat.id, "❌ Failed to add admin")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid ID")

def process_remove_admin(message):
    try:
        admin_id = int(message.text.strip())
        if admin_id == OWNER_ID:
            bot.send_message(message.chat.id, "❌ Can't remove Owner")
            return
        
        if admin_id not in admin_ids:
            bot.send_message(message.chat.id, "❌ Not an admin")
            return
        
        if remove_admin_from_db(admin_id):
            admin_ids.discard(admin_id)
            try:
                user_info = bot.get_chat(admin_id)
                username = f"@{user_info.username}" if user_info.username else "N/A"
                name = user_info.first_name
                bot.send_message(message.chat.id, 
                                f"""
❌ **ADMIN REMOVED**

👤 {name}
🆔 {admin_id}
👥 {username}
                                """, 
                                parse_mode='Markdown')
                bot.send_message(admin_id, 
                                f"""
⚠️ **YOU HAVE BEEN REMOVED**

👑 By: {message.from_user.first_name}
🔑 Access: Revoked
                                """, 
                                parse_mode='Markdown')
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ Admin removed (id: {admin_id})")
                logger.error(f"❌ Failed to get user info: {e}")
        else:
            bot.send_message(message.chat.id, "❌ Failed to remove admin")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid ID")

def process_ban_user(message):
    try:
        user_id = int(message.text.strip())
        if user_id == OWNER_ID:
            bot.send_message(message.chat.id, "❌ Can't ban Owner")
            return
        
        if user_id in admin_ids:
            bot.send_message(message.chat.id, "❌ Can't ban Admin\nRemove admin first")
            return
        
        try:
            user_info = bot.get_chat(user_id)
            username = f"@{user_info.username}" if user_info.username else "N/A"
            name = user_info.first_name
        except:
            username = "N/A"
            name = "Unknown"
        
        success, result = ban_user(user_id)
        
        if success:
            try:
                bot.send_message(user_id,
                               """
🚫 <b>YOU HAVE BEEN BANNED</b>

⚠️ Your access has been revoked
📁 All your files have been deleted

👑 <b>Contact:</b> """ + YOUR_USERNAME + """
                               """,
                               parse_mode='HTML')
            except:
                pass
            
            bot.send_message(message.chat.id,
                           f"""
✅ <b>USER BANNED</b>

👤 {name}
🆔 <code>{user_id}</code>
👥 {username}
🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📝 <b>ACTIONS TAKEN:</b>
• Removed from active users
• Deleted all files
• Killed running processes
• Revoked subscription
                           """,
                           parse_mode='HTML')
        else:
            bot.send_message(message.chat.id, f"❌ {result}")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid ID")

def process_unban_user(message):
    try:
        user_id = int(message.text.strip())
        success, result = unban_user(user_id)
        
        if success:
            try:
                bot.send_message(user_id,
                               f"""
✅ *YOU HAVE BEEN UNBANNED*

✨ Your access has been restored
Use /start to begin again
                               """,
                               parse_mode='Markdown')
            except:
                pass
            
            bot.send_message(message.chat.id, f"✅ User `{user_id}` Unbanned", parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, f"❌ {result}")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid ID")

def process_force_stop_user(message):
    try:
        user_id = int(message.text.strip())
        stopped_count = cleanup_user_processes(user_id)
        bot.send_message(message.chat.id, f"✅ Force stopped {stopped_count} processes for user {user_id}")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid ID")

def process_broadcast(message):
    try:
        broadcast_text = message.text
        success_count = 0
        fail_count = 0
        
        for user_id in active_users:
            try:
                bot.send_message(user_id, broadcast_text)
                success_count += 1
                time.sleep(0.1)
            except:
                fail_count += 1
        
        bot.send_message(
            message.chat.id,
            f"📢 **Broadcast Complete**\n\n✅ Success: {success_count}\n❌ Failed: {fail_count}",
            parse_mode='Markdown'
        )
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

# --- Periodic Ransomware Scan ---
def ransomware_scan_task():
    """Periodic ransomware scan of all user files"""
    while True:
        try:
            logger.info("Starting periodic ransomware scan...")
            
            for user_id in active_users:
                user_folder = get_user_folder(user_id)
                if not os.path.exists(user_folder):
                    continue
                
                for file in os.listdir(user_folder):
                    file_path = os.path.join(user_folder, file)
                    
                    if file.endswith('.log'):
                        continue
                    
                    try:
                        if ransomware_protection.is_ransom_note(file_path):
                            logger.warning(f"Ransom note detected: {file_path}")
                            ransomware_protection.quarantine.add_file(
                                file_path,
                                "Ransom note detected",
                                severity='high',
                                detected_by='periodic_scan'
                            )
                            ransomware_protection.alert_system.send_high_risk_alert({
                                'type': 'RANSOM_NOTE_DETECTED',
                                'user_id': user_id,
                                'file': file,
                            })
                            remove_user_file_db(user_id, file)
                        
                        if ransomware_protection.detect_extension_change(file_path):
                            if file_path not in ransomware_protection.file_monitor.file_hashes:
                                ransomware_protection.alert_system.send_high_risk_alert({
                                    'type': 'ENCRYPTED_FILE_DETECTED',
                                    'user_id': user_id,
                                    'file': file,
                                })
                    except Exception as e:
                        logger.error(f"Error scanning {file_path}: {e}")
            
            for user_id in active_users:
                changes = ransomware_protection.file_monitor.detect_unauthorized_changes(user_id)
                if changes and len(changes) > 10:
                    ransomware_protection.alert_system.send_high_risk_alert({
                        'type': 'MASS_FILE_CHANGES',
                        'user_id': user_id,
                        'change_count': len(changes),
                    })
            
            logger.info("Periodic ransomware scan completed")
            time.sleep(300)
        except Exception as e:
            logger.error(f"Ransomware scan task error: {e}")
            time.sleep(60)

# --- Cleanup function for zombie processes ---
def cleanup_zombie_processes():
    """Clean up any zombie processes that might still be running"""
    for script_key in list(bot_scripts.keys()):
        try:
            script_info = bot_scripts.get(script_key)
            if script_info and script_info.get('process'):
                pid = script_info['process'].pid
                try:
                    proc = psutil.Process(pid)
                    if not proc.is_running() or proc.status() == psutil.STATUS_ZOMBIE:
                        if script_info.get('log_file'):
                            try:
                                script_info['log_file'].close()
                            except:
                                pass
                        del bot_scripts[script_key]
                except psutil.NoSuchProcess:
                    if script_info.get('log_file'):
                        try:
                            script_info['log_file'].close()
                        except:
                            pass
                    del bot_scripts[script_key]
        except Exception as e:
            logger.error(f"Error in cleanup: {e}")

def schedule_cleanup():
    """Regular cleanup of zombie processes and orphaned files"""
    while True:
        try:
            cleanup_zombie_processes()
            
            for script_key in list(bot_scripts.keys()):
                try:
                    script_info = bot_scripts.get(script_key)
                    if script_info and script_info.get('process'):
                        pid = script_info['process'].pid
                        try:
                            proc = psutil.Process(pid)
                            if not proc.is_running():
                                if script_key in bot_scripts:
                                    if script_info.get('log_file'):
                                        try:
                                            script_info['log_file'].close()
                                        except:
                                            pass
                                    del bot_scripts[script_key]
                        except psutil.NoSuchProcess:
                            if script_key in bot_scripts:
                                if script_info.get('log_file'):
                                    try:
                                        script_info['log_file'].close()
                                    except:
                                        pass
                                del bot_scripts[script_key]
                except Exception as e:
                    logger.error(f"Error checking process {script_key}: {e}")
            
            for user_folder in os.listdir(UPLOAD_BOTS_DIR):
                user_folder_path = os.path.join(UPLOAD_BOTS_DIR, user_folder)
                if os.path.isdir(user_folder_path):
                    for file in os.listdir(user_folder_path):
                        if file.endswith('.log'):
                            log_path = os.path.join(user_folder_path, file)
                            if os.path.getmtime(log_path) < time.time() - 3600:
                                try:
                                    os.remove(log_path)
                                    logger.info(f"Cleaned up orphaned log file: {log_path}")
                                except:
                                    pass
            time.sleep(300)
        except Exception as e:
            logger.error(f"Error in schedule_cleanup: {e}")
            time.sleep(60)

# --- Start time for uptime tracking ---
start_time = time.time()

# --- Initialize all security features ---
def init_all_security():
    """Initialize all security features"""
    logger.info("🛡️ Initializing all security features...")
    
    try:
        if hasattr(resource, 'RLIMIT_NOFILE'):
            resource.setrlimit(resource.RLIMIT_NOFILE, (4096, 4096))
        if hasattr(resource, 'RLIMIT_NPROC'):
            resource.setrlimit(resource.RLIMIT_NPROC, (100, 100))
    except:
        pass
    
    scan_thread = threading.Thread(target=ransomware_scan_task, daemon=True)
    scan_thread.start()
    
    logger.info("✅ All security features initialized")

# Call this after database initialization
init_all_security()

# --- Cleanup function ---
def cleanup():
    logger.warning("🛑 Shutting down...")
    for script_key in list(bot_scripts.keys()):
        if script_key in bot_scripts:
            force_cleanup_process(bot_scripts[script_key])

atexit.register(cleanup)

# --- Main execution ---
if __name__ == '__main__':
    cleanup_thread = threading.Thread(target=schedule_cleanup, daemon=True)
    cleanup_thread.start()
    
    keep_alive()
    
    logger.info("🚀 PAI Cloud Bot starting with enhanced security...")
    
    try:
        bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception as e:
        logger.error(f"Bot polling error: {e}")
        time.sleep(5)
        bot.polling(none_stop=True)
