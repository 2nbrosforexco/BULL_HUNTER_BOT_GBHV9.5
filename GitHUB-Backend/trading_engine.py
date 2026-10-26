"""
==============================================================================
📜 BULL HUNTER MULTI ASSET QUANT ENGINE - RENDER PRODUCTION MASTER MODULE
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

        # Clean Asset Configuration (Removed ANSI color codes for Cloud/Render compatibility)
        self.assets_config = {
            'B-XAU_USDT': 'Gold Futures (XAU)',
            'B-XAG_USDT': 'Silver Futures (XAG)',
            'B-CL_USDT': 'WTI Crude Oil',
            'BTC/USDT': 'Bitcoin (BTC)',
            'ETH/USDT': 'Ethereum (ETH)',
            'SOL/USDT': 'Solana (SOL)',
            'BNB/USDT': 'Binance Coin (BNB)',
            'XRP/USDT': 'XRP (XRP)'
        }
        self.symbols = list(self.assets_config.keys())
        
        self.asset_priorities = {
            'B-XAU_USDT': 1, 'B-XAG_USDT': 2, 'B-CL_USDT': 3,
            'BTC/USDT': 4, 'ETH/USDT': 5,
            'SOL/USDT': 6, 'BNB/USDT': 7, 'XRP/USDT': 8
        }

        # Capital & Risk Parameters
        self.balance = 200.0
        self.peak_balance = 200.0
        self.daily_start_balance = 200.0
        self.max_daily_loss_pct = 0.03        # 3% Daily Circuit Breaker
        self.max_peak_drawdown_pct = 0.08     # 8% Peak Drawdown Freeze
        self.is_circuit_broken = False
        self.is_hard_frozen = False
        self.current_day = datetime.datetime.now().day
        self.bot_running = True
        
        self.state_lock = threading.Lock()
        self.candle_cache = {}
        self.candle_cache_lock = threading.Lock()
        
        self.audio_queue = queue.Queue()
        self.macro_news_risk = False
        self.last_news_check_time = 0

        # State Matrix Initialization per Asset
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

        # Initial Wallet Sync & Background Workers
        self.fetch_exchange_balance()
        self.daily_start_balance = self.balance  
        self.peak_balance = self.balance

        threading.Thread(target=self.audio_worker, daemon=True).start()
        self.sync_exchange_positions()
        
        self.send_telegram_alert(
            f"BULL HUNTER QUANT ENGINE STARTED (MASTER LEVEL 9.5)\n"
            f"User: {self.user_email}\n"
            f"Balance: ${self.balance:,.2f} USDT"
        )

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
            except Exception:
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
                        bal = float(item.get("balance", 0.0))
                        locked = float(item.get("locked_balance", 0.0))
                        total = bal + locked
                        if total > 0:
                            with self.state_lock:
                                self.balance = total
                        break
            with self.state_lock:
                if self.balance > self.peak_balance:
                    self.peak_balance = self.balance
        except Exception:
            pass

    def evaluate_global_risk(self):
        try:
            self.fetch_exchange_balance()
            today = datetime.datetime.now().day
            with self.state_lock:
                if today != self.current_day:
                    self.current_day = today
                    self.daily_start_balance = self.balance
                    self.is_circuit_broken = False
                
                if self.balance > self.peak_balance:
                    self.peak_balance = self.balance
                
                peak_dd = (self.peak_balance - self.balance) / self.peak_balance if self.peak_balance > 0 else 0.0
                if peak_dd >= self.max_peak_drawdown_pct and not self.is_hard_frozen:
                    self.is_hard_frozen = True
                    self.send_telegram_alert(f"Hard Drawdown Triggered ({peak_dd*100:.1f}%) for {self.user_email}")

                daily_l = (self.daily_start_balance - self.balance) / self.daily_start_balance if self.daily_start_balance > 0 else 0.0
                if daily_l >= self.max_daily_loss_pct and not self.is_circuit_broken:
                    self.is_circuit_broken = True
                    self.send_telegram_alert(f"Daily Circuit Breaker Triggered ({daily_l*100:.1f}%) for {self.user_email}")
        except Exception:
            pass

    def check_macro_news_risk(self):
        current_time = time.time()
        if current_time - self.last_news_check_time < 900:
            return
        self.last_news_check_time = current_time
        try:
            url = "https://cryptopanic.com/api/v1/posts/?auth_token=free&filter=important"
            res = requests.get(url, timeout=4)
            if res.status_code == 200:
                data = res.json()
                for item in data.get('results', [])[:5]:
                    title = item.get('title', '').lower()
                    if any(w in title for w in ['cpi', 'fomc', 'fed rate', 'war', 'sec crackdown']):
                        self.macro_news_risk = True
                        self.send_telegram_alert("High Volatility Macro Event Detected")
                        return
            self.macro_news_risk = False
        except Exception:
            self.macro_news_risk = False

    def fetch_ticker_price(self, symbol: str) -> float:
        try:
            price_url = "https://public.coindcx.com/market_data/v3/current_prices/futures/rt"
            pres = self.session.get(price_url, timeout=5)
            if pres.status_code == 200:
                prices = pres.json().get("prices", {})
                clean_sym = symbol.replace('/', '_').replace(':USDT', '')
                if 'OIL' in symbol or 'CL' in symbol:
                    clean_sym = "B-CL_USDT"
                elif not clean_sym.startswith("B-"):
                    clean_sym = f"B-{clean_sym}"
                    
                for key in [symbol, clean_sym, clean_sym.replace('B-', '')]:
                    if key in prices:
                        val = float(prices[key].get("mp", 0) or prices[key].get("ls", 0) or 0)
                        if val > 0:
                            return val
        except Exception:
            pass
        return 0.0

    def fetch_market_candles(self, symbol, interval="15m", limit=120):
        if interval == "4h":
            interval = "1d"
        expiry_map = {"15m": 30, "1h": 120, "1d": 600}
        expiry = expiry_map.get(interval, 30)
        current_time = time.time()

        with self.candle_cache_lock:
            if symbol in self.candle_cache and interval in self.candle_cache[symbol]:
                ts, cached_df = self.candle_cache[symbol][interval]
                if current_time - ts < expiry and cached_df is not None and not cached_df.empty:
                    return cached_df

        clean_sym = symbol.replace('/', '_').replace(':USDT', '')
        candidate_pairs = []
        if 'XAU' in symbol or 'GOLD' in symbol:
            candidate_pairs = ["B-XAU_USDT", "B-PAXG_USDT", "XAU_USDT", "PAXG_USDT"]
        elif 'XAG' in symbol or 'SILVER' in symbol:
            candidate_pairs = ["B-XAG_USDT", "XAG_USDT"]
        elif 'OIL' in symbol or 'CRUDE' in symbol or 'CL' in symbol:
            candidate_pairs = ["B-CL_USDT", "CL_USDT"]
        else:
            candidate_pairs = [f"B-{clean_sym}" if not clean_sym.startswith("B-") else clean_sym, clean_sym]

        for pair in candidate_pairs:
            url = f"https://public.coindcx.com/market_data/candles?pair={pair}&interval={interval}&limit={limit}"
            try:
                res = self.session.get(url, timeout=4)
                if res.status_code == 200:
                    data = res.json()
                    if isinstance(data, list) and len(data) >= 10:
                        df = pd.DataFrame(data)
                        required_cols = ["open", "high", "low", "close", "volume", "time"]
                        if not all(col in df.columns for col in required_cols):
                            continue
                        for col in required_cols:
                            df[col] = df[col].astype(float) if col != "time" else df[col]
                        df = df.sort_values(by="time", ascending=True).reset_index(drop=True)
                        with self.candle_cache_lock:
                            if symbol not in self.candle_cache:
                                self.candle_cache[symbol] = {}
                            self.candle_cache[symbol][interval] = (current_time, df)
                        return df
            except Exception:
                pass
        return None

    def check_strong_engulfing_pattern(self, df_15m):
        if df_15m is None or len(df_15m) < 3:
            return False, "NEUTRAL"
        prev_open, prev_close = df_15m['open'].iloc[-2], df_15m['close'].iloc[-2]
        curr_open, curr_close = df_15m['open'].iloc[-1], df_15m['close'].iloc[-1]
        
        if prev_close < prev_open and (curr_close > curr_open) and (curr_close >= prev_open):
            return True, "BUY"
        if prev_close > prev_open and (curr_close < curr_open) and (curr_close <= prev_open):
            return True, "SELL"
        return False, "NEUTRAL"

    def detect_liquidity_target(self, df_15m, side):
        if df_15m is None or len(df_15m) < 50:
            return None
        try:
            highs = df_15m['high'].iloc[-96:-2].values
            lows = df_15m['low'].iloc[-96:-2].values
            if side == 'BUY':
                return float(np.max(highs))
            elif side == 'SELL':
                return float(np.min(lows))
        except Exception:
            pass
        return None

    def calculate_custom_asset_score(self, symbol, df_15m, htf_1h_trend, htf_1d_trend, spread_safe):
        is_gold = ('XAU' in symbol or 'PAXG' in symbol)
        max_score = 12.0 if is_gold else 10.0
        
        if htf_1d_trend == 'NEUTRAL' or htf_1d_trend != htf_1h_trend:
            return 0.0, max_score, False

        detected_side = 'BUY' if htf_1d_trend == 'BULLISH' else 'SELL'
        target_px = self.detect_liquidity_target(df_15m, detected_side)
        if target_px is None:
            return 0.0, max_score, False

        raw_score = 3.0
        if spread_safe:
            raw_score += 1.0

        is_low_volatility = False
        if df_15m is not None and not df_15m.empty and len(df_15m) >= 25:
            recent_vol = df_15m['volume'].iloc[-1]
            avg_vol = df_15m['volume'].iloc[-20:-1].mean()
            if avg_vol > 0 and recent_vol < (0.8 * avg_vol):
                is_low_volatility = True
            elif avg_vol > 0 and recent_vol >= (1.3 * avg_vol):
                raw_score += 1.0

            engulf_triggered, engulf_side = self.check_strong_engulfing_pattern(df_15m)
            if engulf_triggered and engulf_side == detected_side:
                raw_score += 2.0

        final_score = max(0.0, min(max_score, raw_score))
        if detected_side == 'SELL':
            final_score = -final_score

        return final_score, max_score, is_low_volatility

    def fetch_market_analytics(self, symbol):
        try:
            live_price = self.fetch_ticker_price(symbol)
            if live_price <= 0:
                return None

            spread_safe = True
            try:
                clean_sym = symbol.replace('/', '_').replace(':USDT', '')
                if 'OIL' in symbol or 'CL' in symbol:
                    clean_sym = "B-CL_USDT"
                book_url = f"https://public.coindcx.com/market_data/orderbook?pair=B-{clean_sym}"
                b_res = self.session.get(book_url, timeout=3)
                if b_res.status_code == 200:
                    bids, asks = b_res.json().get('bids', {}), b_res.json().get('asks', {})
                    if bids and asks:
                        best_bid = float(list(bids.keys())[0] if isinstance(bids, dict) else bids[0][0])
                        best_ask = float(list(asks.keys())[0] if isinstance(asks, dict) else asks[0][0])
                        if ((best_ask - best_bid) / best_bid) * 100 > 0.35:
                            spread_safe = False
            except Exception:
                pass

            df_1d = self.fetch_market_candles(symbol, interval='4h', limit=50)
            htf_1d_trend = 'BULLISH' if df_1d is not None and not df_1d.empty and df_1d['close'].iloc[-1] > df_1d['close'].ewm(span=20).mean().iloc[-1] else 'BEARISH'

            df_1h = self.fetch_market_candles(symbol, interval='1h', limit=100)
            htf_1h_trend = 'BULLISH' if df_1h is not None and not df_1h.empty and df_1h['close'].iloc[-1] > df_1h['close'].ewm(span=20).mean().iloc[-1] else 'BEARISH'

            df_15m = self.fetch_market_candles(symbol, interval='15m', limit=120)
            atr_val = live_price * 0.005
            if df_15m is not None and not df_15m.empty:
                tr = pd.concat([df_15m['high'] - df_15m['low'], np.abs(df_15m['high'] - df_15m['close'].shift()), np.abs(df_15m['low'] - df_15m['close'].shift())], axis=1).max(axis=1)
                atr_val = tr.rolling(14).mean().iloc[-1] if not np.isnan(tr.rolling(14).mean().iloc[-1]) else atr_val

            score, max_score, is_low_vol = self.calculate_custom_asset_score(symbol, df_15m, htf_1h_trend, htf_1d_trend, spread_safe)
            side_map = 'BUY' if score > 0 else ('SELL' if score < 0 else 'NEUTRAL')
            target_price = self.detect_liquidity_target(df_15m, side_map)

            return {
                'spread_unsafe': not spread_safe,
                'price': live_price,
                'atr': atr_val,
                'htf_1d_trend': htf_1d_trend,
                'htf_1h_trend': htf_1h_trend,
                'live_score': score,
                'max_score': max_score,
                'liquidity_target': target_price,
                'is_low_volatility': is_low_vol
            }
        except Exception:
            return None

    def place_futures_isolated_order(self, symbol, side, quantity, leverage=1):
        try:
            self.fetch_exchange_balance()
            with self.state_lock:
                if self.balance < 5.0:
                    return False, {"error": "Insufficient Margin"}

            timestamp = int(round(time.time() * 1000))
            clean_sym = symbol.replace('/', '_').replace(':USDT', '')
            if 'OIL' in symbol or 'CL' in symbol:
                clean_sym = "B-CL_USDT"
            pair_formatted = f"B-{clean_sym}" if not clean_sym.startswith("B-") else clean_sym
            
            qty_float = float(quantity)
            formatted_qty = max(0.001, round(qty_float, 3)) if 'BTC' in symbol else max(0.01, round(qty_float, 2))

            order_payload = {
                "side": side.lower(), 
                "pair": pair_formatted, 
                "order_type": "market_order", 
                "total_quantity": formatted_qty, 
                "leverage": leverage, 
                "notification": "email_notification", 
                "margin_currency_short_name": "USDT"
            }
            status, resp = self.send_signed_request("/exchange/v1/derivatives/futures/orders/create", {"timestamp": timestamp, "order": order_payload})
            self.fetch_exchange_balance()
            return (status == 200 and resp), resp
        except Exception as e:
            return False, str(e)

    def manage_position(self, symbol, current_price, atr):
        try:
            with self.state_lock:
                st = self.states[symbol]
                if st['position'] is None:
                    return
                pos, entry_px, pos_size, tsl = st['position'], st['entry_price'], st['position_size'], st['trailing_stop_loss']
                hps, lps, live_score = st['highest_price_seen'], st['lowest_price_seen'], st['live_score']

            safe_atr = atr if (atr is not None and atr > 0 and not np.isnan(atr)) else (current_price * 0.005)
            abs_score = abs(live_score)
            atr_multiplier = 2.5 if abs_score >= 8.5 else (2.0 if abs_score >= 6.5 else 1.5)

            if pos == 'BUY':
                if tsl <= 0.0 or hps <= 0.0:
                    hps = max(entry_px, current_price)
                    tsl = entry_px - (atr_multiplier * safe_atr)
                if current_price > hps:
                    hps = current_price

                price_gain = current_price - entry_px
                if price_gain >= (1.5 * safe_atr):
                    tsl = max(tsl, hps - (atr_multiplier * safe_atr))

                with self.state_lock:
                    self.states[symbol]['highest_price_seen'] = hps
                    self.states[symbol]['trailing_stop_loss'] = tsl

                if current_price <= tsl:
                    if self.place_futures_isolated_order(symbol, "sell", pos_size, leverage=1)[0]:
                        pnl = (current_price - entry_px) * pos_size
                        with self.state_lock:
                            self.balance += pnl
                        self.log_trade_to_supabase(symbol, "BUY", pos_size, entry_px, current_price, pnl)
                        self.send_telegram_alert(f"[SL EXIT] {symbol} Closed @ {current_price:,.4f} | PnL: ${pnl:,.2f}")
                        with self.state_lock:
                            self.states[symbol]['position'] = None
                        self.sync_exchange_positions()

            elif pos == 'SELL':
                if tsl <= 0.0 or lps == float('inf') or lps <= 0.0:
                    lps = min(entry_px, current_price)
                    tsl = entry_px + (atr_multiplier * safe_atr)
                if current_price < lps:
                    lps = current_price

                price_drop = entry_px - current_price
                if price_drop >= (1.5 * safe_atr):
                    tsl = min(tsl, lps + (atr_multiplier * safe_atr))

                with self.state_lock:
                    self.states[symbol]['lowest_price_seen'] = lps
                    self.states[symbol]['trailing_stop_loss'] = tsl

                if current_price >= tsl:
                    if self.place_futures_isolated_order(symbol, "buy", pos_size, leverage=1)[0]:
                        pnl = (entry_px - current_price) * pos_size
                        with self.state_lock:
                            self.balance += pnl
                        self.log_trade_to_supabase(symbol, "SELL", pos_size, entry_px, current_price, pnl)
                        self.send_telegram_alert(f"[SL EXIT] {symbol} Short Closed @ {current_price:,.4f} | PnL: ${pnl:,.2f}")
                        with self.state_lock:
                            self.states[symbol]['position'] = None
                        self.sync_exchange_positions()
        except Exception:
            pass

    def execute_entry(self, symbol, mkt):
        try:
            with self.state_lock:
                st = dict(self.states[symbol])
                total_balance = self.balance

            if time.time() < st['cooldown_until'] or self.macro_news_risk or mkt['spread_unsafe']:
                return

            price, atr = mkt['price'], mkt['atr']
            if price <= 0 or atr <= 0:
                return

            asset_budget = total_balance * (0.20 if 'BTC' in symbol else 0.15)
            max_trade_budget = asset_budget * 0.50
            if max_trade_budget < 5.0 or total_balance < max_trade_budget:
                return

            is_gold = ('XAU' in symbol or 'PAXG' in symbol)
            required_threshold = (8.5 if is_gold else 7.0) + (0.5 if mkt['is_low_volatility'] else 0.0)
            abs_score = abs(st['live_score'])
            
            buy_confirmed = (st['live_score'] >= required_threshold and mkt['liquidity_target'] is not None)
            sell_confirmed = (st['live_score'] <= -required_threshold and mkt['liquidity_target'] is not None)

            if buy_confirmed or sell_confirmed:
                atr_multiplier = 2.5 if abs_score >= 8.5 else (2.0 if abs_score >= 6.5 else 1.5)
                
                initial_risk = atr_multiplier * atr
                potential_reward = (mkt['liquidity_target'] - price) if buy_confirmed else (price - mkt['liquidity_target'])

                if initial_risk <= 0 or potential_reward <= 0:
                    return

                risk_reward_ratio = potential_reward / initial_risk
                if risk_reward_ratio < 1.5:
                    return  # Reject trade if Mandatory 1:1.5 R:R Gate fails

                sizing_multiplier = 1.2 if abs_score >= (10.0 if is_gold else 8.5) else 1.0
                position_size = (max_trade_budget * sizing_multiplier) / price
                side_type = "buy" if buy_confirmed else "sell"

                if self.place_futures_isolated_order(symbol, side_type, position_size, leverage=1)[0]:
                    self.send_telegram_alert(
                        f"ENTRY CONFIRMED ({side_type.upper()})\n"
                        f"User: {self.user_email}\n"
                        f"Asset: {symbol}\n"
                        f"Score: {st['live_score']:+.1f}/{st['max_score']}\n"
                        f"R:R Ratio: 1:{risk_reward_ratio:.2f}\n"
                        f"Target: ${mkt['liquidity_target']:,.4f}\n"
                        f"Entry: ${price:,.4f} | Qty: {position_size}"
                    )
                    self.sync_exchange_positions()
        except Exception:
            pass

    def sync_exchange_positions(self):
        try:
            timestamp = int(round(time.time() * 1000))
            body = {"timestamp": timestamp, "page": "1", "size": "10", "margin_currency_short_name": ["USDT"]}
            status, response = self.send_signed_request("/exchange/v1/derivatives/futures/positions", body)
            
            exchange_active_symbols = set()

            if status == 200:
                positions_list = response if isinstance(response, list) else response.get("data", response.get("positions", []))
                if not isinstance(positions_list, list):
                    positions_list = [positions_list] if positions_list else []

                with self.state_lock:
                    for pos in positions_list:
                        if not isinstance(pos, dict): continue
                        
                        sym = str(pos.get('pair', '') or pos.get('symbol', '')).upper()
                        contracts = float(pos.get('active_pos', 0.0) or pos.get('contracts', 0.0) or pos.get('size', 0.0))
                        
                        if contracts != 0:
                            side = str(pos.get('side', '')).lower()
                            if not side:
                                side = 'buy' if contracts > 0 else 'sell'
                            
                            entry_px = float(pos.get('avg_price', 0.0) or pos.get('entryPrice', 0.0) or pos.get('price', 0.0))
                            
                            for configured_sym in self.symbols:
                                normalized_cfg = configured_sym.replace('/', '_').replace(':USDT', '').upper()
                                if normalized_cfg in sym or sym in normalized_cfg:
                                    exchange_active_symbols.add(configured_sym)
                                    mapped_pos = 'BUY' if side in ['buy', 'long'] else 'SELL'
                                    st = self.states[configured_sym]
                                    
                                    was_active_already = (st['position'] == mapped_pos and st['entry_price'] == entry_px)
                                    
                                    st['position'] = mapped_pos
                                    st['entry_price'] = entry_px
                                    st['position_size'] = abs(contracts)
                                    st['margin_status'] = 'NORMAL'
                                    
                                    current_px = self.fetch_ticker_price(configured_sym) or entry_px
                                    fallback_atr = entry_px * 0.008 if entry_px > 0 else 1.0
                                    
                                    if not was_active_already or st['trailing_stop_loss'] <= 0.0:
                                        if mapped_pos == 'BUY':
                                            st['highest_price_seen'] = max(entry_px, current_px)
                                            st['trailing_stop_loss'] = entry_px - (1.5 * fallback_atr)
                                        else:
                                            st['lowest_price_seen'] = min(entry_px, current_px)
                                            st['trailing_stop_loss'] = entry_px + (1.5 * fallback_atr)

                    for configured_sym in self.symbols:
                        if configured_sym not in exchange_active_symbols:
                            st = self.states[configured_sym]
                            if st['position'] is not None:
                                st['position'] = None
                                st['position_size'] = 0.0
                                st['entry_price'] = 0.0
                                st['trailing_stop_loss'] = 0.0
        except Exception:
            pass

    def send_telegram_alert(self, message: str):
        if self.telegram_token and self.telegram_chat_id:
            try:
                url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
                requests.post(url, json={"chat_id": self.telegram_chat_id, "text": message}, timeout=5)
            except Exception:
                pass

    def audio_worker(self):
        while self.bot_running:
            try:
                text, lang = self.audio_queue.get(timeout=1)
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

    def get_live_wallet_summary(self) -> dict:
        total_unrealized = 0.0
        with self.state_lock:
            for sym in self.symbols:
                st = self.states[sym]
                if st['position'] is not None and st['last_price'] > 0:
                    if st['position'] == 'BUY':
                        total_unrealized += (st['last_price'] - st['entry_price']) * st['position_size']
                    else:
                        total_unrealized += (st['entry_price'] - st['last_price']) * st['position_size']
            
            return {
                "total_margin": self.balance,
                "unrealized_pnl": round(total_unrealized, 2)
            }

    def run_loop(self):
        while self.bot_running:
            try:
                self.evaluate_global_risk()
                self.check_macro_news_risk()
                self.sync_exchange_positions()

                with self.state_lock:
                    is_broken, is_frozen = self.is_circuit_broken, self.is_hard_frozen

                if not is_broken and not is_frozen:
                    valid_signals = []
                    for symbol in self.symbols:
                        mkt = self.fetch_market_analytics(symbol)
                        if mkt:
                            with self.state_lock:
                                st = self.states[symbol]
                                st.update({
                                    'last_price': mkt['price'],
                                    'live_score': mkt['live_score'],
                                    'liquidity_target': mkt['liquidity_target'],
                                    'is_low_volatility': mkt['is_low_volatility'],
                                    'is_fetched': True
                                })
                            if st['position'] is not None:
                                self.manage_position(symbol, mkt['price'], mkt['atr'])
                            else:
                                valid_signals.append((self.asset_priorities.get(symbol, 99), symbol, mkt))

                    for _, symbol, mkt in sorted(valid_signals, key=lambda x: x[0]):
                        self.execute_entry(symbol, mkt)

                time.sleep(3)
            except Exception:
                time.sleep(3)

    def stop(self):
        self.bot_running = False
        self.send_telegram_alert(f"Quant Engine Stopped from App Dashboard for {self.user_email}.")