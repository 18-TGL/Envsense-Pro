# ─────────────────────────────────────────────────────────────
# EnvSense Pro — Air Quality Tracker + Eco Scoreboard + Pollution Reporting
# ─────────────────────────────────────────────────────────────
import os, requests, pandas as pd, streamlit as st
from datetime import date
from dotenv import load_dotenv
import math

load_dotenv()

# ─── Navigation ───────────────────────────────────────────────
st.sidebar.title("🌍 EnvSense Pro Navigation")
page = st.sidebar.selectbox(
    "Choose a tool to use:",
    ["🌫️ Air Quality Tracker", "🌱 Eco Scoreboard", "📢 Report Pollution"]
)

OWM_KEY = os.getenv("OPENWEATHER_API_KEY", "").strip()
WAQI_KEY = os.getenv("WAQI_API_KEY", "").strip()

# ==============================================================
# PAGE 1 — AIR QUALITY TRACKER
# ==============================================================
if page == "🌫️ Air Quality Tracker":
    import math

    # ──────────── Helper Functions ─────────────
    def get_cpcb_aqi_info(aqi):
        if aqi <= 50: return "🟢 Good", "Minimal impact"
        elif aqi <= 100: return "🟡 Satisfactory", "Minor breathing discomfort"
        elif aqi <= 200: return "🟠 Moderate", "Discomfort to sensitive groups"
        elif aqi <= 300: return "🔴 Poor", "Discomfort to most on prolonged exposure"
        elif aqi <= 400: return "🟣 Very Poor", "Respiratory illness likely"
        else: return "⚫ Severe", "Serious impact even on healthy people"

    def gauge_color(aqi):
        if aqi <= 50: return "#4CAF50"
        elif aqi <= 100: return "#FFEB3B"
        elif aqi <= 200: return "#FF9800"
        elif aqi <= 300: return "#F44336"
        elif aqi <= 400: return "#9C27B0"
        else: return "#000000"

    @st.cache_data(ttl=900)
    def geocode_city(name, owm_key):
        r = requests.get(
            "http://api.openweathermap.org/geo/1.0/direct",
            params={"q": name, "limit": 1, "appid": owm_key}, timeout=10).json()
        if not r: return None
        return {"lat": r[0]["lat"], "lon": r[0]["lon"], "country": r[0].get("country", "")}

    @st.cache_data(ttl=600)
    def fetch_weather(lat, lon, key):
        try:
            w = requests.get("https://api.openweathermap.org/data/2.5/weather",
                             params={"lat": lat, "lon": lon, "appid": key, "units": "metric"},
                             timeout=10).json()
            return w
        except Exception:
            return None

    @st.cache_data(ttl=300)
    def fetch_waqi(lat, lon, token):
        try:
            r = requests.get(f"https://api.waqi.info/feed/geo:{lat};{lon}/",
                             params={"token": token}, timeout=10).json()
            if r.get("status") != "ok": return None
            d = r["data"]
            return {
                "aqi": d.get("aqi"),
                "dominentpol": d.get("dominentpol"),
                "city": d.get("city", {}).get("name"),
                "time": d.get("time", {}).get("s"),
                "url": d.get("city", {}).get("url")
            }
        except Exception:
            return None

    @st.cache_data(ttl=600)
    def fetch_concentrations(lat, lon, radius_m=40000):
        try:
            r = requests.get("https://api.openaq.org/v2/latest",
                params={
                    "coordinates": f"{lat},{lon}",
                    "radius": radius_m,
                    "parameter": "pm25,pm10,o3,no2,so2,co,nh3",
                    "order_by": "distance",
                    "limit": 1,
                }, timeout=10).json()
            if not r.get("results"): return None, None, None
            res = r["results"][0]
            concs = {m["parameter"]: {"value": m["value"], "unit": m["unit"]}
                     for m in res.get("measurements", [])}
            return concs, res.get("location"), res.get("measurements")[0].get("lastUpdated")
        except Exception:
            return None, None, None

    # ──────────── UI ─────────────
    st.title("🌫️ EnvSense Pro — Air Quality Tracker")
    st.markdown("Check live AQI, pollutants, and weather for any city 🌍")

    location = st.text_input("📍 Enter city or area", placeholder="e.g., Mumbai")
    selected_date = st.date_input("📅 Select date", value=date.today())

    if st.button("🔍 Fetch AQI"):
        geo = geocode_city(location, OWM_KEY)
        if not geo:
            st.error("❌ City not found."); st.stop()
        lat, lon = geo["lat"], geo["lon"]

        waqi = fetch_waqi(lat, lon, WAQI_KEY)
        if not waqi:
            st.error("⚠️ WAQI data unavailable."); st.stop()

        aqi = int(waqi["aqi"])
        band, health = get_cpcb_aqi_info(aqi)

        st.subheader(f"📊 {location.title()} — AQI {aqi} ({band})")
        st.markdown(f"**🧠 Health Impact:** {health}")

        # Dynamic Advice
        def build_advice(aqi):
            if aqi <= 50:
                return "Enjoy the fresh air! Perfect for outdoor activities."
            elif aqi <= 100:
                return "Air is satisfactory. Sensitive people should stay alert."
            elif aqi <= 200:
                return "Limit outdoor activity; wear a mask if sensitive."
            elif aqi <= 300:
                return "Avoid outdoor exercise. Keep windows closed."
            elif aqi <= 400:
                return "Stay indoors; wear N95 if you must go out."
            else:
                return "Avoid outdoor activity completely. Use air purifier."

        st.info(f"💡 {build_advice(aqi)}")

        color = gauge_color(aqi)
        st.markdown(
            f"""
            <div style="background:linear-gradient(to right,green,yellow,orange,red,purple,black);
            height:15px;border-radius:10px;position:relative;">
            <div style="position:absolute;left:{min(aqi,500)/5}%;width:2px;height:20px;
            background-color:{color};"></div></div>""",
            unsafe_allow_html=True)

        concs, station, last = fetch_concentrations(lat, lon)
        if concs:
            st.subheader("🧪 Pollutants (µg/m³)")
            st.caption(f"Station: {station or 'nearest'} · Updated: {last or 'N/A'}")
            limits = {"pm25":60,"pm10":100,"so2":80,"no2":80,"o3":100,"co":2000,"nh3":400}
            for p,v in concs.items():
                lim = limits.get(p)
                if not lim: continue
                status = "✅ Safe" if v["value"]<=lim else "⚠️ High"
                st.write(f"• **{p.upper()}**: {v['value']:.1f} {v['unit']} (Limit: {lim}) → {status}")
        else:
            st.warning("No pollutant data available from nearby stations.")

        w = fetch_weather(lat, lon, OWM_KEY)
        if w and "weather" in w:
            desc = w["weather"][0]["description"].title()
            temp = w["main"]["temp"]; hum = w["main"]["humidity"]; wind = w["wind"]["speed"]
            st.subheader("🌤️ Weather")
            st.info(f"{desc} · 🌡️temp {temp}°C · 💧humidity {hum}% · 💨wind speed {wind} m/s")

        st.caption(f"Source: WAQI · OpenAQ · OpenWeather · Updated {waqi.get('time') or 'recently'}")
        st.caption("[CPCB Dashboard](https://airquality.cpcb.gov.in/AQI_India/)")

# -----------------------------------
# Page 2: Eco Scoreboard (Improved)
# -----------------------------------
elif page == "🌱 Eco Scoreboard":
    # -----------------------------------
    # Eco Scoreboard — full page
    # -----------------------------------
    import pandas as pd
    from datetime import datetime
    from pathlib import Path
    import streamlit as st
    import requests
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    import io

    # =============== Helpers ===============

    def get_badge(score: int) -> str:
        if score >= 200:  return "🌎 Climate Champion"
        if score >= 100:  return "🌿 Eco Hero"
        if score >= 50:   return "🍀 Green Achiever"
        if score >= 20:   return "🌱 Planet Helper"
        return "🌼 Eco Beginner"

    def _load_font(size: int):
        """Try nicer TTFs; fall back to default."""
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size)
        except:
            try:
                return ImageFont.truetype("arial.ttf", size)
            except:
                return ImageFont.load_default()

    def _make_linear_gradient(w, h, c1, c2):
        """Vertical gradient from hex c1 -> c2."""
        img = Image.new("RGB", (w, h), c1)
        r1, g1, b1 = tuple(int(c1[i:i+2], 16) for i in (1,3,5))
        r2, g2, b2 = tuple(int(c2[i:i+2], 16) for i in (1,3,5))
        px = img.load()
        for y in range(h):
            t = y / max(h-1, 1)
            r = int(r1 + (r2 - r1) * t)
            g = int(g1 + (g2 - g1) * t)
            b = int(b1 + (b2 - b1) * t)
            for x in range(w):
                px[x, y] = (r, g, b)
        return img

    def _center(draw, text, font, y, x_center):
        bbox = draw.textbbox((0,0), text, font=font)
        w = bbox[2]-bbox[0]
        return x_center - w//2, y

    def create_badge_image(name: str, badge_title: str, score: int,
                           theme: str = "Leaf", badge_emoji: str = "🎖️") -> bytes:
        """Return PNG bytes of a colorful badge."""
        W, H = 900, 520
        themes = {
            "Leaf":    ("#d0f9d8", "#6be585"),
            "Ocean":   ("#bbdefb", "#64b5f6"),
            "Sunrise": ("#ffe082", "#fb8c00"),
        }
        c1, c2 = themes.get(theme, themes["Leaf"])
        bg = _make_linear_gradient(W, H, c1, c2).convert("RGBA")

        # soft vignette
        shadow = Image.new("RGBA", (W, H), (0,0,0,0))
        sd = ImageDraw.Draw(shadow)
        sd.ellipse((-80, -80, W+80, H+80), fill=(0,0,0,60))
        shadow = shadow.filter(ImageFilter.GaussianBlur(40))
        out = Image.alpha_composite(bg, shadow)

        # rounded white card
        card = Image.new("RGBA", (W, H), (0,0,0,0))
        cd = ImageDraw.Draw(card)
        rr, pad = 28, 60
        cd.rounded_rectangle((pad, pad, W-pad, H-pad), radius=rr,
                             fill=(255,255,255,235), outline=(0,0,0,30), width=2)
        out = Image.alpha_composite(out, card)

        draw = ImageDraw.Draw(out)
        font_title = _load_font(48)
        font_name  = _load_font(42)
        font_body  = _load_font(30)
        font_small = _load_font(24)

        cx, y = W//2, 95

        # emoji
        ex, ey = _center(draw, badge_emoji, font_title, y, cx)
        draw.text((ex, ey), badge_emoji, font=font_title, fill=(40,40,40))
        y += 56

        # header
        hdr = "Eco Badge Awarded!"
        hx, hy = _center(draw, hdr, font_title, y, cx)
        draw.text((hx, hy), hdr, font=font_title, fill=(34,139,34))
        y += 68

        # name
        nm = f"Name: {name}"
        nx, ny = _center(draw, nm, font_name, y, cx)
        draw.text((nx, ny), nm, font=font_name, fill=(20,20,20))
        y += 58

        # badge title
        bt = f"Badge: {badge_title}"
        bx, by = _center(draw, bt, font_body, y, cx)
        draw.text((bx, by), bt, font=font_body, fill=(60,60,60))
        y += 44

        # score
        sc = f"Score Today: {score}"
        sx, sy = _center(draw, sc, font_body, y, cx)
        draw.text((sx, sy), sc, font=font_body, fill=(60,60,60))
        y += 56

        # tagline + leaves
        tag = "“Thank you for making Earth cleaner!”"
        tx, ty = _center(draw, tag, font_small, y, cx)
        draw.text((tx, ty), tag, font=font_small, fill=(80,80,80))
        leaf = "🌿"
        draw.text((78, 78), leaf, font=font_small, fill=(50,120,50))
        draw.text((W-110, 78), leaf, font=font_small, fill=(50,120,50))
        draw.text((78, H-110), leaf, font=font_small, fill=(50,120,50))
        draw.text((W-110, H-110), leaf, font=font_small, fill=(50,120,50))

        buf = io.BytesIO()
        out.convert("RGB").save(buf, format="PNG", optimize=True)
        return buf.getvalue()

    # =============== UI ===============
    st.title("🌱 Eco Scoreboard")
    st.markdown("Track your eco actions, earn badges, and inspire others 🌍")

    st.subheader("👤 Enter Your Details")
    name  = st.text_input("Your Name (public)", placeholder="e.g., Priya Sharma")
    email = st.text_input("Your Email (private; used to prevent duplicates)", placeholder="you@example.com")

    # storage
    score_log = Path("eco_score_log.csv")
    today_str = datetime.now().strftime("%Y-%m-%d")

    if name and email:
        # prevent duplicate same-day submissions for same email
        already_submitted = False
        if score_log.exists():
            df_existing = pd.read_csv(score_log)
            if ((df_existing["Email"] == email) & (df_existing["Date"] == today_str)).any():
                already_submitted = True

        if already_submitted:
            st.warning("⚠️ You’ve already submitted your eco actions today. Come back tomorrow.")
            with st.expander("✏️ Update your display name"):
                new_name = st.text_input("New name")
                if st.button("🔄 Update Name"):
                    df_existing.loc[df_existing["Email"] == email, "Name"] = new_name
                    df_existing.to_csv(score_log, index=False)
                    st.success(f"✅ Name updated to: **{new_name}**")
        else:
            st.subheader("🌿 What green actions did you take today?")
            actions = {
                "🌳 Planted a tree or sapling": 30,
                "🚶 Walked or cycled instead of driving": 10,
                "♻️ Segregated your waste properly": 10,
                "💧 Saved water consciously": 10,
                "🔌 Turned off unused appliances": 5,
                "📱 Reduced screen time": 5,
                "🛍️ Used reusable bags": 10,
                "🍲 Avoided food waste": 10,
                "❄️ Kept AC ≤ 25°C or used fan": 5,
                "🧼 Used eco-friendly/homemade cleaners": 5,
            }

            selected, total_score = [], 0
            c1, c2 = st.columns(2)
            items = list(actions.items())
            for i, (label, pts) in enumerate(items):
                with (c1 if i % 2 == 0 else c2):
                    if st.checkbox(label):
                        selected.append(label); total_score += pts

            if st.button("🎯 Submit My Score"):
                if not selected:
                    st.warning("⚠️ Please select at least one action before submitting.")
                else:
                    new_row = pd.DataFrame([{
                        "Name": name,
                        "Email": email,
                        "Date": today_str,
                        "Score": total_score,
                        "Actions": ", ".join(selected)
                    }])
                    if score_log.exists():
                        df = pd.read_csv(score_log)
                        df = pd.concat([df, new_row], ignore_index=True)
                    else:
                        df = new_row
                    df.to_csv(score_log, index=False)

                    st.success(f"🎉 {name}, you scored **{total_score}** eco-points today!")

                    # small impact metrics
                    co2_saved = round(total_score * 0.2, 1)    # kg CO2
                    water_saved = round(total_score * 5)       # liters
                    m1, m2 = st.columns(2)
                    m1.metric("🌱 CO₂ Saved", f"{co2_saved} kg")
                    m2.metric("🚿 Water Saved", f"{water_saved} L")
                    st.caption("📎 *Estimates based on average lifestyle impacts; actual savings vary.*")

                    # badge
                    badge_title = get_badge(total_score)
                    st.success(f"🏅 You’ve earned the badge: **{badge_title}**")

                    # colorful badge image + download
                    theme = st.selectbox("🎨 Badge Theme", ["Leaf", "Ocean", "Sunrise"], index=0)
                    badge_symbol = st.selectbox("🏅 Badge Symbol", ["🎖️", "🏆", "🌿", "💚", "✨"], index=0)

                    png_bytes = create_badge_image(name, badge_title, total_score,
                                                   theme=theme, badge_emoji=badge_symbol)
                    st.image(png_bytes, caption="Your Eco Badge", use_container_width=True)
                    st.download_button(
                        "📥 Download Badge as PNG",
                        data=png_bytes,
                        file_name=f"{name or 'eco'}_badge.png",
                        mime="image/png"
                    )

                    # share links (message only; link is your site)
                    st.markdown("#### 📤 Share Your Achievement")
                    share_text = f"{name} scored {total_score} eco-points and earned the badge ‘{badge_title}’ 🌿 via EnvSense Pro!"
                    encoded = requests.utils.quote(share_text)
                    st.markdown(
                        f"- [💬 WhatsApp](https://wa.me/?text={encoded})\n"
                        f"- [📘 Facebook](https://www.facebook.com/sharer/sharer.php?u=https://yourwebsite.com&quote={encoded})\n"
                        f"- [🔗 LinkedIn](https://www.linkedin.com/sharing/share-offsite/?url=https://yourwebsite.com)\n"
                        f"- 📸 For Instagram Stories: share the downloaded badge image."
                    )

        # history & streak (per email)
        if score_log.exists():
            df_user = pd.read_csv(score_log)
            df_user = df_user[df_user["Email"] == email]
            if not df_user.empty:
                df_user["Date"] = pd.to_datetime(df_user["Date"])
                streak_days = df_user["Date"].dt.date.nunique()
                st.info(f"🔥 {name}, you’ve submitted on **{streak_days}** day(s)! Keep the streak going!")
                st.subheader("📅 Your Eco History")
                hist = df_user.groupby(df_user["Date"].dt.strftime("%Y-%m-%d"))["Score"].sum()
                st.line_chart(hist)

    # leaderboard (this month)
    st.subheader("🏆 Top Eco Heroes This Month")
    score_log = Path("eco_score_log.csv")
    if score_log.exists():
        df = pd.read_csv(score_log)
        if not df.empty:
            df["Date"] = pd.to_datetime(df["Date"])
            df["Month"] = df["Date"].dt.strftime("%Y-%m")
            current_m = datetime.now().strftime("%Y-%m")
            df_m = df[df["Month"] == current_m]
            if not df_m.empty:
                board = df_m.groupby("Name")["Score"].sum().reset_index()
                board["Badge"] = board["Score"].apply(get_badge)
                board = board.sort_values("Score", ascending=False).head(10)
                st.dataframe(board.rename(columns={"Name":"User", "Score":"Total Score"}))
            else:
                st.info("No submissions yet this month. Be the first!")
        else:
            st.info("No data yet. Be the first to submit your actions!")
    else:
        st.info("No data yet. Be the first to submit your actions!")


# -----------------------------------
# Page 3: Report Pollution Concerns
# -----------------------------------
elif page == "📢 Report Pollution":
    st.title("📢 Report Pollution Concern")
    st.write("Help us track environmental pollution issues by reporting what you observe in your area. 🌍")

    with st.form("pollution_form"):
        name = st.text_input("👤 Your Name (Optional)")
        location = st.text_input("📍 Location of Incident", placeholder="e.g., Andheri East, Mumbai")
        region = st.text_input("🌐 Region", placeholder="e.g., Maharashtra")
        category = st.selectbox("🚨 Type of Issue", ["Air Pollution", "Water Pollution", "Waste Dumping", "Noise", "Others"])
        description = st.text_area("📝 Describe the Issue", placeholder="e.g., Burning of garbage, chemical smell in air")

        uploaded_image = st.file_uploader("📸 Upload Image (Optional)", type=["png", "jpg", "jpeg"])

        submitted = st.form_submit_button("🚀 Submit Report")

        if submitted:
            from datetime import datetime
            from pathlib import Path

            report_data = {
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Name": name,
                "Location": location,
                "Region": region,
                "Category": category,
                "Description": description,
                "Image Filename": uploaded_image.name if uploaded_image else "None"
            }

            report_file = Path("pollution_reports.csv")
            if not report_file.exists():
                pd.DataFrame([report_data]).to_csv(report_file, index=False)
            else:
                pd.DataFrame([report_data]).to_csv(report_file, mode='a', header=False, index=False)

            if uploaded_image:
                image_dir = Path("pollution_images")
                image_dir.mkdir(exist_ok=True)
                with open(image_dir / uploaded_image.name, "wb") as f:
                    f.write(uploaded_image.read())

            st.success("✅ Your pollution report has been submitted.")
            st.info("💚 Thank you for taking action for a cleaner planet!")

    with st.expander("🔐 Admin Access"):
        admin_pass = st.text_input("Enter admin password", type="password")

        if admin_pass == "green@123":  # ← change this to your secret password
            st.success("🔓 Access Granted")

            if Path("pollution_reports.csv").exists():
                df_reports = pd.read_csv("pollution_reports.csv")
                st.dataframe(df_reports)

                csv = df_reports.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Reports as CSV", csv, "pollution_reports.csv", "text/csv")
            else:
                st.warning("📂 No reports submitted yet.")
        elif admin_pass:
            st.error("❌ Incorrect password")
