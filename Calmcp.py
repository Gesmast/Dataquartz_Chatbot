import httpx
import os
from fastmcp import FastMCP
from datetime import datetime
from supabase import create_client
import streamlit as st

  # --- Import base from secrets ---
CAL_API_BASE = st.secrets["CAL_API_BASE"]
CAL_API_KEY = st.secrets["CAL_API_KEY"]
EVENT_TYPE_ID = st.secrets["EVENT_TYPE_ID"]
# Initialize the MCP Server
mcp = FastMCP("Dataquartz Calendar")

# --- 1. THE TOOLS ---

@mcp.tool()
async def get_available_slots(date: str, start_hour: str = "00:00:00", end_hour: str = "23:59:59") -> str:
    """
    Fetches available booking slots for a specific date and time range.
    date: 'YYYY-MM-DD'
    start_hour: 'HH:MM:SS' (Optional, defaults to start of day)
    end_hour: 'HH:MM:SS' (Optional, defaults to end of day)
    """
  
    url = f"{CAL_API_BASE}/slots"
    
    # We combine the date and the specific hours requested
    # Note: Cal.com API expects UTC or ISO format; we specify the window here.
    params = {
        "apiKey": CAL_API_KEY,
        "eventTypeId": EVENT_TYPE_ID,
        "startTime": f"{date}T{start_hour}Z",
        "endTime": f"{date}T{end_hour}Z",
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        data = response.json()
        
        slots = data.get("slots", {})
        day_slots = slots.get(date, [])
        
        if not day_slots:
            return f"I couldn't find any open slots between {start_hour} and {end_hour} on {date}."
        
        # Format slots for the AI (e.g., 14:30)
        times = [s['time'].split('T')[1][:5] for s in day_slots]
        return f"Available slots for {date} from {start_hour[:5]} to {end_hour[:5]}: " + ", ".join(times)



# Initialize Supabase (using your existing secrets)
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

@mcp.tool()
async def create_cal_booking(name: str, email: str, start_time: str, session_id: str) -> str:
    """
    1. Books on Cal.com
    2. Saves metadata to Supabase for zero-login tracking
    """
    url = f"{CAL_API_BASE}/bookings?apiKey={CAL_API_KEY}"
    payload = {
        "eventTypeId": EVENT_TYPE_ID,
        "start": start_time,
        "responses": {"name": name, "email": email},
        "timeZone": "Asia/Karachi"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        if response.status_code == 201:
            data = response.json()
            booking_id = data['booking']['id']
            
            # --- THE SUPABASE LOGGING LOGIC ---
            supabase.table("meetings").insert({
                "cal_booking_id": booking_id,
                "user_email": email,
                "user_name": name,
                "start_time": start_time,
                "session_id": session_id,
                "status": "confirmed"
            }).execute()
            
            return f"Confirmed! Booking ID {booking_id} created for {name}."
        return f"Error: {response.text}"
    
@mcp.tool()
async def reschedule_cal_booking(booking_id: int, new_start_time: str) -> str:
    """
    Updates an existing booking on Cal.com and synchronizes the Supabase ledger.
    new_start_time: ISO format 'YYYY-MM-DDTHH:MM:SS'
    """
    # 1. Update Cal.com (Using PATCH for V1)
    url = f"{CAL_API_BASE}/bookings/{booking_id}?apiKey={CAL_API_KEY}"
    payload = {
        "start": new_start_time,
        "timeZone": "Asia/Karachi"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.patch(url, json=payload)
        if response.status_code == 200:
            # 2. Sync with Supabase (Update the ledger)
            try:
                supabase.table("meetings") \
                    .update({"start_time": new_start_time, "status": "rescheduled"}) \
                    .eq("cal_booking_id", booking_id) \
                    .execute()
                return f"Successfully rescheduled meeting {booking_id} to {new_start_time} (PKT)."
            except Exception as e:
                return f"Rescheduled on Cal.com, but Supabase sync failed: {str(e)}"
        return f"Cal.com reschedule error: {response.text}"
    
@mcp.tool()
async def cancel_cal_booking(booking_id: int, reason: str = "User requested") -> str:
    """
    Cancels the booking on Cal.com and REMOVES it from the Supabase guest ledger.
    """
    # 1. Cancel on Cal.com (V1 uses DELETE or POST to /cancel depending on setup)
    url = f"{CAL_API_BASE}/bookings/{booking_id}/cancel?apiKey={CAL_API_KEY}"
    payload = {"reason": reason}
    
    async with httpx.AsyncClient() as client:
        # V1 typically uses DELETE for cancellation as per docs
        response = await client.request("DELETE", url, json=payload)
        
        if response.status_code in [200, 204]:
            # 2. Remove from Supabase (Clean up the guest ledger)
            try:
                supabase.table("meetings") \
                    .delete() \
                    .eq("cal_booking_id", booking_id) \
                    .execute()
                return f"Booking {booking_id} has been cancelled and removed from our records."
            except Exception as e:
                return f"Cancelled on Cal.com, but failed to remove from database: {str(e)}"
        return f"Cal.com cancellation error: {response.text}"
    
@mcp.tool()
async def get_booking_by_email(email: str) -> str:
    """
    Searches Supabase for any existing guest bookings linked to this email.
    """
    try:
        # Query Supabase for the guest ledger
        response = supabase.table("meetings") \
            .select("cal_booking_id, start_time, user_name, status") \
            .eq("user_email", email) \
            .order("start_time", desc=True) \
            .execute()

        if not response.data:
            return f"No bookings found in our records for {email}."

        # Format the data so the AI can read it easily
        booking_list = []
        for b in response.data:
            time_str = b['start_time'].replace("T", " at ")
            booking_list.append(
                f"ID: {b['cal_booking_id']} | Name: {b['user_name']} | "
                f"Time: {time_str} | Status: {b['status']}"
            )
        
        return "I found the following bookings for you:\n" + "\n".join(booking_list)
    
    except Exception as e:

        return f"Database error: {str(e)}"






