"""
==============================================================================
📜 BULL HUNTER MULTI ASSET QUANT ENGINE - FASTAPI INTEGRATED MODULE
==============================================================================
"""

import pandas as pd
import numpy as np
import time
import datetime
import requests
import os
import sys
import threading
import queue
import tempfile
import hmac
import hashlib
import json
import traceback
from gtts import gTTS

class DynamicBullHunterEngine:
    def __init__(self, user_email: str, api_key: str, api_secret: str, telegram_token: str = "", telegram_chat_id: str = "", supabase_client=None):
        self.user_email = user_email
        self.api_key = api_key.strip()
        self.api_secret = api_secret.strip()
        self.telegram_token = telegram_token.strip()
        self.telegram_chat_id = telegram_chat_id.strip()
        self.supabase = supabase_client
        
        self.bot_start_time = time.time()
        self.base_url = "https://api.coindcx.com"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

        self.assets_config = {
            'B-XAU_USDT': ('Gold Futures (XAU)', '\033[1;38;5;208m'),
            'B-XAG_USDT': ('Silver Futures (XAG)', '\033[1;38;5;159m'),
            'B-CL_USDT': ('WTI Crude Oil', '\033[1;38;5;214m'),
            'BTC/USDT': ('Bitcoin (BTC)', '\033[1;33m'),
            'ETH/USDT': ('Ethereum (ETH)', '\033[1;35m'),
            'SOL/USDT': ('Solana (SOL)', '\033[1;38;5;39m'),
            'BNB/USDT': ('Binance Coin (BNB)', '\033[1;38;5;220m'),
            'XRP/USDT': ('XRP (XRP)', '\033[1;36m')
        }
        self.symbols = list(self.assets_config.keys())
        
        self.balance = 200.0
        self.peak_balance = 200.0
        self.daily_start_balance = 200.0
        self.max_daily_loss_pct = 0.03
        self.max_peak_drawdown_pct = 0.08
        self.is_circuit_broken = False
        self.is_hard_frozen = False
        self.bot_running = True
        
        self.state_lock = threading.Lock()
        self.candle_cache = {}
        self.candle_cache_lock = threading.Lock()
        
        self.audio_queue = queue.Queue()
        self.states = {}
        for sym in self.symbols:
            is_gold = ('XAU' in sym or 'PAXG' in sym)
            self.states[sym] = {
                'position': None,
                'entry_price': 0.0,
                'position_size': 0.0,
                'trailing_stop_loss': 0.0,
                'highest_price_seen': 0.0,
                'lowest_price_seen': float('inf'),
                'live_score': 0.0,
                'max_score': 12.0 if is_gold else 10.0,
                'liquidity_target': None,
                'is_low_volatility': False,
                'is_fetched': False,
                'cooldown_until': 0,
                'margin_status': 'NORMAL',
                'last_price': 0.0
            }

        self.fetch_exchange_balance()
        self.daily_start_balance = self.balance  
        self.peak_balance = self.balance
        self.macro_news_risk = False
        self.last_news_check_time = 0

        # Start background workers
        threading.Thread(target=self.audio_worker, daemon=True).start()
        self.sync_exchange_positions()
        self.send_telegram_alert(f"🚀 *BULL HUNTER QUANT ENGINE STARTED*\nUser: `{self.user_email}`\nBalance: `${self.balance:,.2f} USDT`")

    def get_signature(self, json_payload: str) -> str:
        secret_bytes = bytes(self.api_secret, encoding="utf-8")
        return hmac.new(secret_bytes, json_payload.encode("utf-8"), hashlib.sha256).hexdigest()

    def send_signed_request(self, endpoint: str, body: dict, method: str = "POST") -> tuple:
        url = f"{self.base_url}{endpoint}"
        json_body = json.dumps(body, separators=(",", ":"))
        signature = self.get_signature(json_body)
        headers = {
            "Content-Type": "application/json",
            "X-AUTH-APIKEY": self.api_key,
            "X-AUTH-SIGNATURE": signature,
        }
        for attempt in range(1, 4):
            try:
                if method.upper() == "GET":
                    response = self.session.get(url, data=json_body, headers=headers, timeout=10)
                else:
                    response = self.session.post(url, data=json_body, headers=headers, timeout=10)
                if response.status_code == 429:
                    time.sleep(attempt * 2)
                    continue
                response.raise_for_status()
                return response.status_code, response.json() if response.text else {}
            except Exception as e:
                time.sleep(attempt * 2)
        return 503, {}

    def fetch_exchange_balance(self):
        try:
            timestamp = int(round(time.time() * 1000))
            body = {"timestamp": timestamp}
            status, resp = self.send_signed_request("/exchange/v1/derivatives/futures/wallets", body, method="GET")
            if status == 200:
                data_list = resp if isinstance(resp, list) else resp.get("data", [resp] if isinstance(resp, dict) else [])
                for item in data_list:
                    if isinstance(item, dict) and str(item.get("currency_short_name", "")).upper() == "USDT":
                        balance = float(item.get("balance", 0.0)) + float(item.get("locked_balance", 0.0))
                        if balance > 0:
                            with self.state_lock:
                                self.balance = balance
                        break
        except Exception:
            pass

    def send_telegram_alert(self, message: str):
        if self.telegram_token and self.telegram_chat_id:
            try:
                url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
                requests.post(url, json={"chat_id": self.telegram_chat_id, "text": message, "parse_mode": "Markdown"}, timeout=5)
            except Exception:
                pass

    def audio_worker(self):
        while self.bot_running:
            try:
                text, lang = self.audio_queue.get(timeout=1)
                # Headless server: Audio generation without GUI playback dependency
                filename = os.path.join(tempfile.gettempdir(), f"alert_{int(time.time()*1000)}.mp3")
                tts = gTTS(text=text, lang=lang, slow=False)
                tts.save(filename)
                if os.path.exists(filename):
                    os.remove(filename)
                self.audio_queue.task_done()
            except queue.Empty:
                continue
            except Exception:
                pass

    def log_trade_to_supabase(self, symbol, side, qty, entry_price, exit_price, pnl):
        if self.supabase:
            try:
                self.supabase.table("trade_logs").insert({
                    "email": self.user_email,
                    "symbol": symbol,
                    "side": side,
                    "quantity": qty,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "pnl": pnl,
                    "executed_at": datetime.datetime.utcnow().isoformat()
                }).execute()
            except Exception:
                pass

    def sync_exchange_positions(self):
        try:
            timestamp = int(round(time.time() * 1000))
            body = {"timestamp": timestamp, "page": "1", "size": "10", "margin_currency_short_name": ["USDT"]}
            status, response = self.send_signed_request("/exchange/v1/derivatives/futures/positions", body)
            if status == 200:
                positions_list = response if isinstance(response, list) else response.get("data", response.get("positions", []))
                active_syms = set()
                with self.state_lock:
                    for pos in positions_list:
                        if not isinstance(pos, dict): continue
                        sym = str(pos.get('pair', '') or pos.get('symbol', '')).upper()
                        contracts = float(pos.get('active_pos', 0.0) or pos.get('contracts', 0.0) or pos.get('size', 0.0))
                        if contracts != 0:
                            for cfg_sym in self.symbols:
                                if cfg_sym.replace('/', '_').replace(':USDT', '').upper() in sym:
                                    active_syms.add(cfg_sym)
                                    self.states[cfg_sym]['position'] = 'BUY' if contracts > 0 else 'SELL'
                                    self.states[cfg_sym]['entry_price'] = float(pos.get('avg_price', 0.0) or pos.get('entryPrice', 0.0))
                                    self.states[cfg_sym]['position_size'] = abs(contracts)
                    for cfg_sym in self.symbols:
                        if cfg_sym not in active_syms and self.states[cfg_sym]['position'] is not None:
                            self.states[cfg_sym]['position'] = None
        except Exception:
            pass

    def fetch_ticker_price(self, symbol: str) -> float:
        try:
            res = self.session.get("https://public.coindcx.com/market_data/v3/current_prices/futures/rt", timeout=5)
            if res.status_code == 200:
                prices = res.json().get("prices", {})
                clean_sym = f"B-{symbol.replace('/', '_').replace(':USDT', '')}"
                if clean_sym in prices:
                    return float(prices[clean_sym].get("mp", 0) or prices[clean_sym].get("ls", 0) or 0)
        except Exception:
            pass
        return 0.0

    def run_loop(self):
        while self.bot_running:
            try:
                self.fetch_exchange_balance()
                self.sync_exchange_positions()
                for sym in self.symbols:
                    px = self.fetch_ticker_price(sym)
                    if px > 0:
                        with self.state_lock:
                            self.states[sym]['last_price'] = px
                            self.states[sym]['is_fetched'] = True
                time.sleep(3)
            except Exception:
                time.sleep(3)

    def stop(self):
        self.bot_running = False
        self.send_telegram_alert("🛑 *[SHUTDOWN]* Engine Stopped from App Dashboard.")