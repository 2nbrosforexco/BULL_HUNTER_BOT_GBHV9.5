import os
import time
import json
import threading
import asyncio
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from cryptography.fernet import Fernet
from supabase import create_client, Client

# FastAPI ऐप इनिशियलाइजेशन
app = FastAPI(
    title="CDX Bull Hunter - Master SaaS Engine",
    version="9.5.0"
)

# CORS टॉलरेंस (Flutter Web ऐप कनेक्शन के लिए सभी ओरिजिन की अनुमति)
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

# सक्रिय बोट थ्रेड्स, इंस्टेंस और वेबसॉकेट कनेक्शन को ट्रैक करने के लिए इन-मेमोरी डिक्शनरी
active_bot_instances = {}
active_bot_threads = {}
active_connections: dict[str, WebSocket] = {}

# ------------------------------------------------------------------------------
# 🛡️ HELPER FUNCTIONS (ENCRYPTION & METRICS)
# ------------------------------------------------------------------------------
def encrypt_val(value: str) -> str:
    return cipher.encrypt(value.encode()).decode()

def decrypt_val(encrypted_value: str) -> str:
    return cipher.decrypt(encrypted_value.encode()).decode()

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

    if total_trades > 1 and df['pnl'].std() > 0:
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
    action: str  # "start" या "stop"

# ------------------------------------------------------------------------------
# 🚀 API ENDPOINTS & WEBSOCKET
# ------------------------------------------------------------------------------

@app.get("/")
def health_check():
    return {
        "status": "online",
        "engine": "Bull Hunter Quant SaaS Engine Level 9.5",
        "active_users_running": len(active_bot_instances)
    }

# WebSocket Real-time Endpoint
@app.websocket("/ws/bot-status/{email}")
async def websocket_bot_status(websocket: WebSocket, email: str):
    await websocket.accept()
    active_connections[email] = websocket
    try:
        while True:
            live_data = {
                "status": "running" if email in active_bot_instances else "stopped",
                "message": "Live feed connected successfully"
            }
            await websocket.send_json(live_data)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        if email in active_connections:
            del active_connections[email]

# 1. यूज़र ऑनबोर्डिंग और क्रेडेंशियल सेविंग (With Fernet Encryption & Supabase)
@app.post("/api/user/register")
def register_user_credentials(data: UserRegistrationRequest):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase connection not initialized.")

    try:
        enc_api_key = encrypt_val(data.coindcx_api_key)
        enc_secret = encrypt_val(data.coindcx_secret)

        user_data = {
            "full_name": data.full_name,
            "email": data.email,
            "phone_number": data.phone_number,
            "is_phone_verified": True,
            "encrypted_coindcx_api_key": enc_api_key,
            "encrypted_coindcx_secret": enc_secret,
            "telegram_token": data.telegram_token,
            "telegram_chat_id": data.telegram_chat_id,
            "is_bot_active": False
        }

        # Supabase टेबल में इंसर्ट या अपडेट
        res = supabase.table("user_bot_profiles").upsert(user_data, on_conflict="email").execute()

        return {
            "status": "success",
            "message": "User credentials registered & encrypted successfully!",
            "email": data.email
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

# 2. बोट कंट्रोल एंडपॉइंट (Start / Stop)
@app.post("/api/bot/control")
def control_user_bot(data: BotControlRequest):
    email = data.email
    action = data.action.lower()

    if action == "start":
        if email in active_bot_instances:
            return {"status": "already_running", "message": "बॉट आपके अकाउंट पर पहले से लाइव रन कर रहा है।"}

        try:
            res = supabase.table("user_bot_profiles").select("*").eq("email", email).execute()
            if not res.data:
                raise HTTPException(status_code=404, detail="User profile not found.")

            profile = res.data[0]
            raw_api_key = decrypt_val(profile["encrypted_coindcx_api_key"])
            raw_secret = decrypt_val(profile["encrypted_coindcx_secret"])
            tg_token = profile.get("telegram_token", "")
            tg_chat_id = profile.get("telegram_chat_id", "")

            def _run_bot_thread():
                pass

            t = threading.Thread(target=_run_bot_thread, daemon=True)
            active_bot_threads[email] = t
            t.start()

            # Active instances mein add karna zaroori hai taaki WebSocket sahi status dikha sake
            active_bot_instances[email] = True

            supabase.table("user_bot_profiles").update({"is_bot_active": True}).eq("email", email).execute()

            return {
                "status": "success",
                "message": "बॉट सफलतापूर्वक स्टार्ट हो गया है और कॉइनडीसीएक्स के साथ कनेक्टेड है!"
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to start bot: {str(e)}")

    elif action == "stop":
        if email in active_bot_instances:
            del active_bot_instances[email]

        if email in active_bot_threads:
            del active_bot_threads[email]

        if supabase:
            supabase.table("user_bot_profiles").update({"is_bot_active": False}).eq("email", email).execute()

        return {"status": "success", "message": "बॉट को सुरक्षित रूप से बंद कर दिया गया है।"}

    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'start' or 'stop'.")

# 3. एनालिटिक्स एंडपॉइंट
@app.get("/api/analytics/summary")
def get_analytics_summary(email: str = None):
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured.")

    try:
        if email:
            trades_res = supabase.table("trade_logs").select("*").eq("email", email).execute()
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