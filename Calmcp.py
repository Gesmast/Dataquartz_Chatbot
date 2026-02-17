import httpx
import os
from fastmcp import FastMCP
from datetime import datetime
from supabase import create_client
import streamlit as st



# Initialize the MCP Server
mcp = FastMCP("Dataquartz Calendar")

# --- 1. THE TOOLS ---

@mcp.tool()
async def get_available_slots(date: str, start_hour: str, end_time: str, detected_tz: str) -> str:
   """
    Fetches available slots for a specific timeframe.
    - date: 'YYYY-MM-DD'
    - start_time: ISO 8601 string for search start (e.g., '2026-02-15T09:00:00Z')
    - end_time: ISO 8601 string for search end (e.g., '2026-02-15T09:30:00Z')
   """
    url = "https://api.cal.com/v2/slots"

    headers = {
        "cal-api-version": "2024-09-04",
        "Authorization": f"Bearer {st.secrets['CAL_API_KEY']}",
        "Content-Type": "application/json"
    }

    start_time = f"{date}T{start_hour}Z"
    end_time = f"{date}T{end_hour}Z"

    params = {
        "eventTypeId": int(st.secrets["EVENT_TYPE_ID"]),
        "eventTypeSlug": "connect-with-dataquartz",
        "start":start_time,           
        "end":end_time,
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)

        if response.status_code != 200:
            return f"Error {response.status_code}: {response.text}"

        data = response.json()
        # V2 response structure: data -> slots -> {date}
        slots_data = data.get("data", {}).get("slots", {})

        # Pull slots for the requested date
        day_slots = slots_data.get(date, [])

        if not day_slots:
            return f"No available slots found on {date} between those times."

        # Extract times (e.g., '15:00') for the chatbot to evaluate
        times = [s['time'].split('T')[1][:5] for s in day_slots]
        return f"Available bookable slots on {date}: " + ", ".join(times)


# Initialize Supabase (using your existing secrets)
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

@mcp.tool()
async def create_cal_booking(name, email, start_time, session_id, detected_tz: str):

    """
    Creates a new booking on Cal.com using the attendee's detected timezone.
    - name: Attendee's full name.
    - email: Attendee's email address.
    - start_time: ISO 8601 string in UTC timezone(e.g., '2026-02-15T14:30:00Z').
    - detected_tz: The attendee's browser timezone .
    """
    
    CAL_API_KEY = st.secrets["CAL_API_KEY"]
    EVENT_TYPE_ID = int(st.secrets["EVENT_TYPE_ID"])  # Force to Integer

    url =f'https://api.cal.com/v2/bookings'

    headers = {
        "Authorization": f"Bearer {CAL_API_KEY}",
        "cal-api-version": "2024-08-13",
        "Content-Type": "application/json"
    }

    payload = {
        "start": start_time,
        "eventTypeId": EVENT_TYPE_ID,
        "eventTypeSlug": "connect-with-dataquartz",
        "username": st.secrets["cal_username"],
        "attendee": {
            "name": name,
            "email": email,
            "timeZone": detected_tz,
            "language": "en"
        }
    

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code == 201:
            return response.json()
        else:
            # This will show you exactly what is wrong in the 400 error
            st.error(f"Booking Failed: {response.text}")
            return None


@mcp.tool()
async def reschedule_cal_booking(booking_id: int, new_start_time: str) -> str:
    """
    Updates an existing booking on Cal.com and synchronizes the Supabase ledger.
    new_start_time: ISO format 'YYYY-MM-DDTHH:MM:SS'
    """
    
    CAL_API_KEY = st.secrets["CAL_API_KEY"]

    # 1. Update Cal.com (Using PATCH for V1)
    url = f"https://api.cal.com/v2/bookings/{booking_uid}/reschedule"
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
    
    CAL_API_KEY = st.secrets["CAL_API_KEY"]

    # 1. Cancel on Cal.com (V1 uses DELETE or POST to /cancel depending on setup)
    url =f"https://api.cal.com/v2/bookings/{booking_uid}/cancel"
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













