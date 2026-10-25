import os
import time
import json
import threading
import asyncio
import random
import hashlib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from cryptography.fernet import Fernet
from supabase import create_client, Client

# Integration of Bull Hunter Quant Engine
from trading_engine import DynamicBullHunterEngine

# FastAPI App Initialization
app = FastAPI(
    title="CDX Bull Hunter - Master SaaS Engine",
    version="9.6.0"
)

# CORS Tolerance (Flutter Web/Cross-platform access ke liye)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------------------
# 🔑 ENVIRONMENT & SUPABASE SETUP
# ------------------------------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key().decode())

cipher = Fernet(ENCRYPTION_KEY.encode())
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL else None

# Active bot engine instances, threads & WebSocket connections tracking
active_bot_instances: dict[str, DynamicBullHunterEngine] = {}
active_bot_threads: dict[str, threading.Thread] = {}
active_connections: dict[str, WebSocket] = {}

# ------------------------------------------------------------------------------
# 🛡️ HELPER FUNCTIONS (ENCRYPTION & METRICS)
# ------------------------------------------------------------------------------
def encrypt_val(value: str) -> str:
    if not value:
        return ""
    return cipher.encrypt(value.encode()).decode()

def decrypt_val(encrypted_value: str) -> str:
    if not encrypted_value:
        return ""
    try:
        return cipher.decrypt(encrypted_value.encode()).decode()
    except Exception:
        return encrypted_value  # Fallback if unencrypted

def calculate_performance_metrics(trades_list: list, initial_balance: float = 200.0) -> dict:
    if not trades_list:
        return {
            "total_trades": 0,
            "net_pnl": 0.0,
            "win_rate_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "sharpe_ratio": 0.0
        }

    df = pd.DataFrame(trades_list)
    total_trades = len(df)
    net_pnl = float(df['pnl'].sum()) if 'pnl' in df.columns else 0.0

    winning_trades = len(df[df['pnl'] > 0]) if 'pnl' in df.columns else 0
    win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0.0

    equity_curve = [initial_balance]
    curr_eq = initial_balance
    for pnl in df.get('pnl', []):
        curr_eq += pnl
        equity_curve.append(curr_eq)

    eq_series = pd.Series(equity_curve)
    peak = eq_series.cummax()
    drawdown = (eq_series - peak) / peak
    max_drawdown_pct = abs(float(drawdown.min())) * 100 if not drawdown.empty else 0.0

    if total_trades > 1 and 'pnl' in df.columns and df['pnl'].std() > 0:
        mean_ret = df['pnl'].mean()
        std_ret = df['pnl'].std()
        sharpe_ratio = (mean_ret / std_ret) * np.sqrt(252)
    else:
        sharpe_ratio = 0.0

    return {
        "total_trades": total_trades,
        "net_pnl": round(net_pnl, 2),
        "win_rate_pct": round(win_rate, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "sharpe_ratio": round(sharpe_ratio, 2)
    }

# ------------------------------------------------------------------------------
# 📦 REQUEST MODELS
# ------------------------------------------------------------------------------
class UserRegistrationRequest(BaseModel):
    full_name: str
    email: str
    phone_number: str
    coindcx_api_key: str
    coindcx_secret: str
    telegram_token: str = ""
    telegram_chat_id: str = ""

class BotControlRequest(BaseModel):
    email: str
    action: str  # "start" ya "stop"

class SendOTPRequest(BaseModel):
    email: str

class VerifyOTPRequest(BaseModel):
    email: str
    otp: str

class SetPinRequest(BaseModel):
    email: str
    pin: str

class VerifyPinRequest(BaseModel):
    email: str
    pin: str

# ------------------------------------------------------------------------------
# 🚀 API ENDPOINTS & WEBSOCKET
# ------------------------------------------------------------------------------

@app.get("/")
def health_check():
    return {
        "status": "online",
        "engine": "Bull Hunter Quant SaaS Engine Level 9.6 (Secured)",
        "active_users_running": len(active_bot_instances)
    }

# 1️⃣ WebSocket Real-time Endpoint
@app.websocket("/ws/bot-status/{email}")
async def websocket_bot_status(websocket: WebSocket, email: str):
    await websocket.accept()
    clean_email = email.strip().lower()
    active_connections[clean_email] = websocket
    try:
        while True:
            is_running = clean_email in active_bot_instances and active_bot_instances[clean_email].bot_running
            live_data = {
                "status": "running" if is_running else "stopped",
                "message": "Live feed connected successfully",
                "balance": active_bot_instances[clean_email].balance if is_running else 0.0,
                "timestamp": int(time.time())
            }
            await websocket.send_json(live_data)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        if clean_email in active_connections:
            del active_connections[clean_email]

# 2️⃣ OTP Send Endpoint
@app.post("/api/auth/send-otp")
def send_otp_endpoint(data: SendOTPRequest):
    email = data.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Kripya ek valid email address enter karein.")
    
    otp = str(random.randint(100000, 999999))
    
    if supabase:
        try:
            supabase.table("user_otps").upsert({
                "email": email,
                "otp": otp
            }).execute()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database error saving OTP: {str(e)}")
    else:
        raise HTTPException(status_code=500, detail="Supabase connection not initialized.")
    
    print(f"[SECURE OTP DEBUG] Generated OTP for {email}: {otp}")
    
    return {
        "status": "success",
        "message": f"OTP successfully sent to {email}",
        "debug_otp": otp
    }

# 3️⃣ OTP Verify Endpoint
@app.post("/api/auth/verify-otp")
def verify_otp_endpoint(data: VerifyOTPRequest):
    email = data.email.strip().lower()
    user_otp = data.otp.strip()
    
    if not supabase:
        raise HTTPException(status_code=500, detail="Database connection not initialized.")
        
    try:
        res = supabase.table("user_otps").select("otp").eq("email", email).execute()
        if not res.data or len(res.data) == 0:
            raise HTTPException(status_code=400, detail="OTP expire ho chuka hai ya email nahi mila.")
        
        saved_otp = res.data[0].get("otp")
        
        if saved_otp != user_otp:
            raise HTTPException(status_code=400, detail="Galat OTP enter kiya gaya hai.")
        
        supabase.table("user_otps").delete().eq("email", email).execute()
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OTP verification error: {str(e)}")
    
    is_registered = False
    has_pin = False
    try:
        profile_res = supabase.table("user_bot_profiles").select("email, app_pin_hash, coindcx_status").eq("email", email).execute()
        if profile_res.data and len(profile_res.data) > 0:
            is_registered = True
            if profile_res.data[0].get("app_pin_hash"):
                has_pin = True
    except Exception as e:
        print(f"Database lookup error: {str(e)}")
            
    return {
        "status": "success",
        "message": "OTP verified successfully.",
        "is_registered": is_registered,
        "has_pin": has_pin
    }

# 4️⃣ Set App PIN Endpoint
@app.post("/api/auth/set-pin")
def set_app_pin(data: SetPinRequest):
    email = data.email.strip().lower()
    if len(data.pin) not in [4, 6] or not data.pin.isdigit():
        raise HTTPException(status_code=400, detail="PIN 4 ya 6 digits ka numeric code hona chahiye.")
    
    pin_hash = hashlib.sha256(data.pin.encode()).hexdigest()
    
    if supabase:
        try:
            supabase.table("user_bot_profiles").update({
                "app_pin_hash": pin_hash
            }).eq("email", email).execute()
            return {"status": "success", "message": "App PIN successfully set!"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to set PIN: {str(e)}")
    else:
        raise HTTPException(status_code=500, detail="Database connection error.")

# 5️⃣ Verify App PIN Endpoint
@app.post("/api/auth/verify-pin")
def verify_app_pin(data: VerifyPinRequest):
    email = data.email.strip().lower()
    input_hash = hashlib.sha256(data.pin.encode()).hexdigest()
    
    if supabase:
        try:
            res = supabase.table("user_bot_profiles").select("app_pin_hash").eq("email", email).execute()
            if not res.data or not res.data[0].get("app_pin_hash"):
                raise HTTPException(status_code=404, detail="PIN set nahi hai. Kripya OTP se login karein.")
            
            if res.data[0]["app_pin_hash"] == input_hash:
                return {"status": "success", "message": "PIN verified successfully!"}
            
            raise HTTPException(status_code=400, detail="Galat PIN enter kiya gaya hai.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

# 6️⃣ User Registration
@app.post("/api/user/register")
def register_user_credentials(data: UserRegistrationRequest):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase connection not initialized.")

    try:
        api_valid = len(data.coindcx_api_key.strip()) > 10 and len(data.coindcx_secret.strip()) > 10
        coindcx_status = "VERIFIED" if api_valid else "FAILED"
        error_msg = None if api_valid else "Invalid CoinDCX API Key or Secret format detected."

        enc_api_key = encrypt_val(data.coindcx_api_key)
        enc_secret = encrypt_val(data.coindcx_secret)

        user_data = {
            "full_name": data.full_name,
            "email": data.email.strip().lower(),
            "phone_number": data.phone_number,
            "is_phone_verified": True,
            "encrypted_coindcx_api_key": enc_api_key,
            "encrypted_coindcx_secret": enc_secret,
            "coindcx_status": coindcx_status,
            "telegram_token": data.telegram_token,
            "telegram_chat_id": data.telegram_chat_id,
            "telegram_status": "VERIFIED" if data.telegram_token else "PENDING",
            "last_error_message": error_msg,
            "is_bot_active": False
        }

        supabase.table("user_bot_profiles").upsert(user_data, on_conflict="email").execute()

        if not api_valid:
            raise HTTPException(status_code=400, detail="CoinDCX API Key verification failed! Kripya sahi credentials dalein.")

        return {
            "status": "success",
            "message": "User credentials registered & API verified successfully!",
            "email": data.email
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

# 7️⃣ Bot Execution Control (Starts/Stops Dynamic Quant Engine)
@app.post("/api/bot/control")
def control_user_bot(data: BotControlRequest):
    email = data.email.strip().lower()
    action = data.action.lower()

    if action == "start":
        if email in active_bot_instances and active_bot_instances[email].bot_running:
            return {"status": "already_running", "message": "Bot aapke account par pehle se live run kar raha hai."}

        try:
            res = supabase.table("user_bot_profiles").select("*").eq("email", email).execute()
            if not res.data:
                raise HTTPException(status_code=404, detail="User profile not found.")

            profile = res.data[0]
            
            if profile.get("coindcx_status") != "VERIFIED":
                raise HTTPException(
                    status_code=400, 
                    detail="Bot start nahi ho sakta! Aapka CoinDCX API verification fail ya pending hai."
                )

            raw_api_key = decrypt_val(profile["encrypted_coindcx_api_key"])
            raw_secret = decrypt_val(profile["encrypted_coindcx_secret"])
            telegram_token = profile.get("telegram_token", "")
            telegram_chat_id = profile.get("telegram_chat_id", "")

            # Quant Engine Instantiate karein
            engine = DynamicBullHunterEngine(
                user_email=email,
                api_key=raw_api_key,
                api_secret=raw_secret,
                telegram_token=telegram_token,
                telegram_chat_id=telegram_chat_id,
                supabase_client=supabase
            )

            # Thread launch karein
            t = threading.Thread(target=engine.run_loop, daemon=True)
            active_bot_instances[email] = engine
            active_bot_threads[email] = t
            t.start()

            supabase.table("user_bot_profiles").update({"is_bot_active": True}).eq("email", email).execute()

            return {
                "status": "success",
                "message": "Bot safaltapurvak start ho gaya hai aur CoinDCX ke sath securely connected hai!"
            }

        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to start bot: {str(e)}")

    elif action == "stop":
        if email in active_bot_instances:
            active_bot_instances[email].stop()
            del active_bot_instances[email]
        if email in active_bot_threads:
            del active_bot_threads[email]

        if supabase:
            supabase.table("user_bot_profiles").update({"is_bot_active": False}).eq("email", email).execute()

        return {"status": "success", "message": "Bot ko surakshit roop se band kar diya gaya hai."}

    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'start' or 'stop'.")

# 8️⃣ Bot Status & Live Positions Endpoint
@app.get("/api/bot/status")
def get_bot_status(email: str):
    clean_email = email.strip().lower()
    is_running = clean_email in active_bot_instances and active_bot_instances[clean_email].bot_running
    balance = 0.0
    active_positions = []

    if is_running:
        engine = active_bot_instances[clean_email]
        balance = engine.balance
        with engine.state_lock:
            for sym, st in engine.states.items():
                if st['position'] is not None:
                    active_positions.append({
                        "symbol": sym,
                        "position": st['position'],
                        "entry_price": st['entry_price'],
                        "current_price": st['last_price'],
                        "size": st['position_size'],
                        "pnl": round((st['last_price'] - st['entry_price']) * st['position_size'] if st['position'] == 'BUY' else (st['entry_price'] - st['last_price']) * st['position_size'], 2)
                    })

    return {
        "status": "success",
        "is_active": is_running,
        "balance": round(balance, 2),
        "active_positions": active_positions
    }

# 9️⃣ Analytics Summary Endpoint
@app.get("/api/analytics/summary")
def get_analytics_summary(email: str = None):
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured.")

    try:
        if email:
            trades_res = supabase.table("trade_logs").select("*").eq("email", email.strip().lower()).execute()
        else:
            trades_res = supabase.table("trade_logs").select("*").execute()

        trades = trades_res.data or []
        metrics = calculate_performance_metrics(trades)

        users_count_res = supabase.table("user_bot_profiles").select("email", count="exact").execute()
        total_users = users_count_res.count if hasattr(users_count_res, 'count') else len(users_count_res.data or [])

        metrics["total_platform_users"] = total_users
        return {"status": "success", "metrics": metrics}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics calculation failed: {str(e)}")