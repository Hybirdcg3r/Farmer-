#!/usr/bin/env python3
"""
Happy Farmer v1.0.1 - Full Fixed Code (user_data issue fixed)
စိုက်ပျိုးသူများအတွက် ရာသီဥတု အချက်အလက်များ
"""

import os
import logging
import requests
import json
from datetime import datetime
from telegram import (
    Update, 
    KeyboardButton, 
    ReplyKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ============ CONFIGURATION ============
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8729156078:AAFkIsDmAJ-qdMjJghKhCyYAMrU0O4j7rJQ")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "JAWS543ERKH67S8LL49TZPNGQ")

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============ BOTTOM MENUS ============

def get_main_menu():
    """Main menu - အဓိက menu"""
    keyboard = [
        [KeyboardButton("📍 Location Share", request_location=True)],
        ["🌦️ ရာသီဥတု ကြည့်ရန်", "📅 ခန့်မှန်း ကြည့်ရန်"],
        ["❓ အကူအညီ", "ℹ️ အကြောင်း"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def get_weather_menu():
    """Weather submenu"""
    keyboard = [
        ["🌦️ ဒီနေ့ ရာသီဥတု", "📅 ၃ ရက် ခန့်မှန်း"],
        ["📍 တည်နေရာ ပြောင်းရန်", "🔙 နောက်သို့"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_location_menu():
    """Location menu"""
    keyboard = [
        [KeyboardButton("📍 Location အသစ် Share", request_location=True)],
        ["🔙 နောက်သို့"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ============ LOCATION SERVICE ============

class LocationService:
    """တည်နေရာ အပြည့်အစုံ ရယူခြင်း"""
    
    @staticmethod
    def get_full_address(lat, lon):
        """GPS → Full address"""
        try:
            url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&accept-language=my&addressdetails=1"
            headers = {
                'User-Agent': 'HappyFarmerBot/1.0 (happyfarmer@gmail.com)',
                'Accept-Language': 'my,en'
            }
            
            response = requests.get(url, headers=headers, timeout=8)
            response.raise_for_status()
            
            data = response.json()
            address = data.get('address', {})
            
            # Extract components
            village = address.get('village', '')
            suburb = address.get('suburb', '')
            town = address.get('town', '')
            city = address.get('city', '')
            municipality = address.get('municipality', '')
            county = address.get('county', '')
            state = address.get('state', '')
            
            # Build name
            parts = []
            local = village or suburb or town or city or municipality or ''
            if local:
                parts.append(local)
            
            if county and county not in local:
                parts.append(county)
            
            if state and state not in ''.join(parts):
                parts.append(state)
            
            if parts:
                return "၊ ".join(parts), address
            
            display = data.get('display_name', '')
            if display:
                parts = [p.strip() for p in display.split(',')[:3]]
                return "၊ ".join(parts), address
            
            return f"GPS: {lat:.4f}, {lon:.4f}", None
            
        except requests.exceptions.Timeout:
            logger.error("Geocoding timeout")
            return f"GPS: {lat:.4f}, {lon:.4f}", None
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error: {e}")
            return f"GPS: {lat:.4f}, {lon:.4f}", None
        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            return f"GPS: {lat:.4f}, {lon:.4f}", None

# ============ WEATHER SERVICE ============

class WeatherService:
    def __init__(self):
        self.api_key = WEATHER_API_KEY
        self.base_url = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"
    
    def get_weather(self, lat, lon, location_name=""):
        """ရာသီဥတု data ရယူ"""
        try:
            location_query = f"{lat},{lon}"
            url = f"{self.base_url}/{location_query}?unitGroup=metric&key={self.api_key}&contentType=json"
            
            logger.info(f"Fetching weather for: {location_name}")
            
            response = requests.get(url, timeout=12)
            response.raise_for_status()
            
            data = response.json()
            return self._format_weather(data, location_name)
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Weather API HTTP error: {e}")
            if response.status_code == 401:
                return {"error": "API key မမှန်ပါ။"}
            elif response.status_code == 429:
                return {"error": "API limit ကျော်သွားပါ။"}
            else:
                return {"error": f"API error: {response.status_code}"}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Weather network error: {e}")
            return {"error": "အင်တာနက် ပြဿနာ။"}
            
        except json.JSONDecodeError as e:
            logger.error(f"Weather JSON error: {e}")
            return {"error": "Data ဖတ်ရာမှာ ပြဿနာ။"}
            
        except Exception as e:
            logger.error(f"Weather error: {e}")
            return {"error": "မ unforeseen အမှား။"}
    
    def _format_weather(self, data, location_name):
        """ရာသီဥတု format"""
        try:
            current = data.get('currentConditions', {})
            days = data.get('days', [])
            
            if not days:
                return {"error": "ရာသီဥတု data မရရှိပါ။"}
            
            # Current weather
            if current:
                temp = current.get('temp', days[0].get('temp', 0))
                humidity = current.get('humidity', days[0].get('humidity', 0))
                wind = current.get('windspeed', days[0].get('windspeed', 0))
                condition = current.get('conditions', days[0].get('conditions', 'Unknown'))
                precip_prob = current.get('precipprob', days[0].get('precipprob', 0))
                icon = current.get('icon', days[0].get('icon', 'unknown'))
            else:
                temp = days[0].get('temp', 0)
                humidity = days[0].get('humidity', 0)
                wind = days[0].get('windspeed', 0)
                condition = days[0].get('conditions', 'Unknown')
                precip_prob = days[0].get('precipprob', 0)
                icon = days[0].get('icon', 'unknown')
            
            # 3-day forecast
            forecast = []
            myanmar_days = {
                "Monday": "တနင်္လာ", "Tuesday": "အင်္ဂါ", "Wednesday": "ဗုဒ္ဓဟူး",
                "Thursday": "ကြာသပတေး", "Friday": "သောကြာ", "Saturday": "စနေ", "Sunday": "တနင်္ဂဆွေ"
            }
            
            for day in days[1:4]:
                try:
                    date = datetime.strptime(day['datetime'], '%Y-%m-%d')
                    day_name = myanmar_days.get(date.strftime('%A'), date.strftime('%A'))
                    
                    forecast.append({
                        'day': day_name,
                        'temp_max': day.get('tempmax', 0),
                        'temp_min': day.get('tempmin', 0),
                        'rain_chance': day.get('precipprob', 0),
                        'emoji': self._get_emoji(day.get('icon', 'unknown'))
                    })
                except Exception as e:
                    logger.error(f"Forecast parse error: {e}")
                    continue
            
            return {
                'location': location_name,
                'current': {
                    'temp': temp,
                    'temp_max': days[0].get('tempmax', 0),
                    'temp_min': days[0].get('tempmin', 0),
                    'humidity': humidity,
                    'wind': wind,
                    'condition': condition,
                    'rain_chance': precip_prob,
                    'emoji': self._get_emoji(icon)
                },
                'forecast': forecast
            }
            
        except Exception as e:
            logger.error(f"Format weather error: {e}")
            return {"error": "ရာသီဥတု data ပြောင်းရာမှာ ပြဿနာ။"}
    
    def _get_emoji(self, icon):
        """Weather icon → Emoji"""
        if not icon:
            return '🌡️'
        
        try:
            icon_map = {
                'clear-day': '☀️', 'clear-night': '🌙',
                'partly-cloudy-day': '⛅', 'partly-cloudy-night': '☁️',
                'cloudy': '☁️', 'rain': '🌧️',
                'showers-day': '🌦️', 'showers-night': '🌧️',
                'thunder-rain': '⛈️', 'thunder-showers-day': '⛈️',
                'snow': '❄️', 'fog': '🌫️', 'wind': '💨'
            }
            return icon_map.get(icon.lower(), '🌡️')
        except:
            return '🌡️'

# ============ CONTENT BUILDER ============

class ContentBuilder:
    @staticmethod
    def build_message(weather_data):
        """ရာသီဥတု message"""
        
        if isinstance(weather_data, dict) and 'error' in weather_data:
            return f"""❌ **ရာသီဥတု ရယူ၍ မရပါ**

အကြောင်းရင်း: {weather_data['error']}

**ဖြေရှင်းနည်းများ:**
• နောက်မှ ထပ်ကြိုးစားပါ
• /location ဖြင့် တည်နေရာ အသစ် ထည့်ပါ"""
        
        if not weather_data:
            return "❌ ရာသီဥတု data ရယူ၍ မရပါ။"
        
        try:
            current = weather_data['current']
            forecast = weather_data['forecast']
            
            conditions = {
                "Clear": "သာယာသော ရာသီဥတု",
                "Partially cloudy": "တိမ်အနည်းငယ်",
                "Cloudy": "တိမ်ထူ", "Rain": "မိုးရွာ",
                "Rain, Partially cloudy": "မိုးရွာသွန်းမှု",
                "Overcast": "တိမ်ဖုံးလွှမ်း",
                "Rain, Overcast": "မိုးရွာ၊ တိမ်ဖုံး"
            }
            condition_my = conditions.get(current['condition'], current['condition'])
            
            msg = f"""🌾 **Happy Farmer - သင့်နေရာအတွက် ရာသီဥတု**

ဟိုင်း စိုက်ပျိုးသူကြီးရေ! 🧑‍🌾

📍 **{weather_data.get('location', 'မသိသေးသော နေရာ')}**

━━━━━━━━━━━━━━━━━━━━━━
🌦️ **ဒီနေ့ ရာသီဥတု** {current.get('emoji', '🌡️')}
━━━━━━━━━━━━━━━━━━━━━━
🌡️ လက်ရှိ: **{current.get('temp', 0):.0f}°C** (အမြင့် {current.get('temp_max', 0):.0f}°C / အနိမ့် {current.get('temp_min', 0):.0f}°C)
💧 စိုထိုင်းဆ: {current.get('humidity', 0):.0f}%
💨 လေတိုက်: {current.get('wind', 0):.0f} km/h
🌧️ မိုးရွာဖို့: {current.get('rain_chance', 0):.0f}%
📋 အခြေအနေ: {condition_my}

{ContentBuilder._get_advice(current)}

━━━━━━━━━━━━━━━━━━━━━━
📅 **လာမယ့် ၃ ရက် ခန့်မှန်း**
━━━━━━━━━━━━━━━━━━━━━━
"""
            
            for day in forecast:
                try:
                    rain_emoji = "🌧️" if day.get('rain_chance', 0) > 50 else "⛅" if day.get('rain_chance', 0) > 20 else "☀️"
                    msg += f"{day.get('emoji', '🌡️')} **{day.get('day', '?')}**: {day.get('temp_min', 0):.0f}-{day.get('temp_max', 0):.0f}°C ({rain_emoji} {day.get('rain_chance', 0):.0f}%)\n"
                except Exception as e:
                    logger.error(f"Forecast format error: {e}")
                    continue
            
            msg += f"\nပျော်ရွှင်စွာ စိုက်ပျိုးကြပါစေ! 🌾🚜\n`_Data: Visual Crossing API_`"
            
            return msg
            
        except Exception as e:
            logger.error(f"Build message error: {e}")
            return "❌ Message တည်ဆောက်ရာမှာ ပြဿနာ။"
    
    @staticmethod
    def _get_advice(current):
        """စိုက်ပျိုးရေးအကြံပြုချက်"""
        try:
            temp = current.get('temp', 25)
            rain = current.get('rain_chance', 0)
            
            advice = []
            if rain > 70:
                advice.append("🌧️ မိုးရွာမည် - ပျိုးထောင်ရန် မသင့်")
            elif 20 <= temp <= 30 and rain < 30:
                advice.append("✅ မြေဩဇာထည့်ရန် အကောင်းဆုံး နေ့")
            
            if temp > 35:
                advice.append("🔥 အပူချိန်မြင့် - ရေလောင်းရန်")
            
            if not advice:
                advice.append("✅ ပုံမှန် လုပ်ငန်းစဉ်များ ဆက်လုပ်ပါ")
            
            return "💡 **အကြံပြုချက်**: " + " | ".join(advice[:2])
        except:
            return "💡 **အကြံပြုချက်**: ပုံမှန် လုပ်ငန်းစဉ်များ ဆက်လုပ်ပါ"

# ============ SERVICES INIT ============

location_service = LocationService()
weather_service = WeatherService()
content_builder = ContentBuilder()

# ============ BOT HANDLERS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start with bottom menu"""
    try:
        welcome = """🌾 **Happy Farmer မှ ကြိုဆိုပါသည်!**

စိုက်ပျိုးသူများအတွက် ရာသီဥတု အချက်အလက်များ။

**အသုံးပြုနည်း:**
📍 Location Share ခလုတ်ကို နှိပ်ပြီး သင့်စိုက်ခင်း တည်နေရာ ထည့်ပါ။"""
        
        await update.message.reply_text(
            welcome, 
            reply_markup=get_main_menu(),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Start error: {e}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bottom menu text handlers"""
    text = update.message.text
    
    try:
        # Main Menu
        if text == "🌦️ ရာသီဥတု ကြည့်ရန်":
            await send_weather(update, context)
            
        elif text == "📅 ခန့်မှန်း ကြည့်ရန်":
            await send_forecast(update, context)
            
        elif text == "❓ အကူအညီ":
            await send_help(update, context)
            
        elif text == "ℹ️ အကြောင်း":
            await send_about(update, context)
            
        # Weather Submenu
        elif text == "🌦️ ဒီနေ့ ရာသီဥတု":
            await send_weather(update, context)
            
        elif text == "📅 ၃ ရက် ခန့်မှန်း":
            await send_forecast(update, context)
            
        elif text == "📍 တည်နေရာ ပြောင်းရန်":
            await update.message.reply_text(
                "📍 သင့်တည်နေရာ အသစ်ကို share လုပ်ပါ:",
                reply_markup=get_location_menu()
            )
            
        # Back button
        elif text == "🔙 နောက်သို့":
            await update.message.reply_text(
                "🌾 Main Menu",
                reply_markup=get_main_menu()
            )
            
        else:
            await update.message.reply_text(
                "❓ နားမလည်ပါ။ Menu ကနေ ရွေးချယ်ပါ။",
                reply_markup=get_main_menu()
            )
            
    except Exception as e:
        logger.error(f"Text handler error: {e}")
        await update.message.reply_text(
            "❌ အမှားတစ်ခု ဖြစ်ပါတယ်။",
            reply_markup=get_main_menu()
        )

async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """FIXED location handler - NO user_data assignment"""
    
    if not update or not update.message or not update.message.location:
        logger.error("Location data missing")
        return
    
    try:
        location = update.message.location
        lat = location.latitude
        lon = location.longitude
        
        logger.info(f"Received location: lat={lat}, lon={lon}")
        
        # Validate
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            raise ValueError("Invalid coordinates")
        
        # Check Myanmar bounds
        if not (9.5 <= lat <= 28.5 and 92.0 <= lon <= 101.5):
            await update.message.reply_text(
                "⚠️ မြန်မာနိုင်ငံထဲမှ Location share လုပ်ပါ။",
                reply_markup=get_main_menu()
            )
            return
        
        # Get address
        full_address, _ = location_service.get_full_address(lat, lon)
        
        # ✅ FIXED: Use context.user_data directly, NO assignment
        context.user_data['location'] = {
            'lat': float(lat),
            'lon': float(lon),
            'name': str(full_address)
        }
        
        logger.info(f"Saved location: {full_address}")
        
        # Send map
        try:
            await update.message.reply_location(
                latitude=float(lat),
                longitude=float(lon),
                title="🌾 Happy Farmer - စိုက်ခင်း",
                address=str(full_address)[:100]
            )
        except Exception as e:
            logger.error(f"Map error: {e}")
        
        # Send confirmation
        confirm_msg = f"""✅ **တည်နေရာ သိမ်းဆည်းပြီးပါပြီ!**

📍 {full_address[:150]}

🌐 `{lat:.6f}, {lon:.6f}`"""
        
        await update.message.reply_text(
            confirm_msg,
            reply_markup=get_weather_menu(),
            parse_mode='Markdown'
        )
        
        # Auto send weather
        await send_weather(update, context)
        
    except Exception as e:
        logger.error(f"Location handler error: {e}")
        await update.message.reply_text(
            "❌ တည်နေရာ ထည့်ရာမှာ ပြဿနာ။ /start ဖြင့် ပြန်စပါ။",
            reply_markup=get_main_menu()
        )

async def send_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """FIXED weather sender - NO user_data assignment"""
    try:
        # ✅ FIXED: Check user_data exists without assignment
        location_data = context.user_data.get('location') if context.user_data else None
        
        if not location_data:
            await update.message.reply_text(
                "❌ တည်နေရာ မသိရှိသေးပါ။ 📍 Location Share နှိပ်ပါ!",
                reply_markup=get_main_menu()
            )
            return
        
        # Validate
        required_keys = ['lat', 'lon', 'name']
        if not all(key in location_data for key in required_keys):
            logger.error(f"Invalid location data: {location_data}")
            await update.message.reply_text(
                "❌ တည်နေရာ data မှား။ 📍 ထပ်မံ share လုပ်ပါ။",
                reply_markup=get_main_menu()
            )
            return
        
        # Fetch weather
        weather = weather_service.get_weather(
            location_data['lat'],
            location_data['lon'],
            location_data['name']
        )
        
        # Send message
        message = content_builder.build_message(weather)
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Send weather error: {e}")
        await update.message.reply_text(
            "❌ ရာသီဥတု data ရယူ၍ မရပါ။",
            reply_markup=get_main_menu()
        )

async def send_forecast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """FIXED forecast sender - NO user_data assignment"""
    try:
        # ✅ FIXED: Check user_data exists without assignment
        location_data = context.user_data.get('location') if context.user_data else None
        
        if not location_data:
            await update.message.reply_text(
                "❌ တည်နေရာ မသိရှိသေးပါ။ 📍 Location Share နှိပ်ပါ!",
                reply_markup=get_main_menu()
            )
            return
        
        # Get weather
        weather = weather_service.get_weather(
            location_data['lat'],
            location_data['lon'],
            location_data['name']
        )
        
        if isinstance(weather, dict) and 'error' in weather:
            await update.message.reply_text(
                f"❌ {weather['error']}",
                reply_markup=get_main_menu()
            )
            return
        
        # Build forecast only
        forecast = weather.get('forecast', [])
        msg = f"""📅 **လာမယ့် ၃ ရက် ခန့်မှန်း**

📍 {weather.get('location', '')}

"""
        for day in forecast:
            try:
                rain_emoji = "🌧️" if day.get('rain_chance', 0) > 50 else "⛅" if day.get('rain_chance', 0) > 20 else "☀️"
                msg += f"{day.get('emoji', '🌡️')} **{day.get('day', '?')}**: {day.get('temp_min', 0):.0f}-{day.get('temp_max', 0):.0f}°C ({rain_emoji} {day.get('rain_chance', 0):.0f}%)\n"
            except:
                continue
        
        await update.message.reply_text(
            msg,
            reply_markup=get_weather_menu(),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Forecast error: {e}")
        await update.message.reply_text(
            "❌ ခန့်မှန်း data ရယူ၍ မရပါ။",
            reply_markup=get_main_menu()
        )

async def send_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help with menu"""
    try:
        help_text = """🌾 **အကူအညီ**

**ဘယ်လို အသုံးပြုရမလဲ:**

1️⃣ 📍 **Location Share** နှိပ်
   → သင့်စိုက်ခင်း တည်နေရာ share လုပ်

2️⃣ 🌦️ **ရာသီဥတု ကြည့်ရန်** နှိပ်
   → လက်ရှိ ရာသီဥတု + ခန့်မှန်း ရယူ

3️⃣ 📅 **ခန့်မှန်း ကြည့်ရန်** နှိပ်
   → ၃ ရက် ခန့်မှန်း သာ ကြည့်

**မြေပုံကြည့်ရန်:**
Location share လုပ်ထားရင် မြေပုံပေါ်က 
အနီရောင်အမှတ်အသားကို နှိပ်ပါ → Google Maps မှာ ဖွင့်လို့ရ"""
        
        await update.message.reply_text(
            help_text,
            reply_markup=get_main_menu(),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Help error: {e}")

async def send_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """About with menu"""
    try:
        about_text = """🌾 **Happy Farmer v1.0.1**

စိုက်ပျိုးသူများအတွက် ရာသီဥတု အချက်အလက်များ။

✨ Features:
• 📍 GPS-based weather
• 🇲🇲 Myanmar language
• 📅 3-day forecast
• 🌾 Farming advice

💻 Developed with ❤️
📅 Version: 1.0.1"""
        
        await update.message.reply_text(
            about_text,
            reply_markup=get_main_menu(),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"About error: {e}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Global error handler"""
    logger.error(f"Global error: {context.error}")
    
    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "❌ အမှားတစ်ခု ဖြစ်သွားပါသည်။\n"
                "• /start ဖြင့် ပြန်စပါ။",
                reply_markup=get_main_menu()
            )
    except Exception as e:
        logger.error(f"Error handler failed: {e}")

# ============ MAIN ============

def main():
    """Bot စတင်ခြင်း"""
    if TELEGRAM_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ ERROR: TELEGRAM_TOKEN ထည့်ပါ!")
        return
    
    if not WEATHER_API_KEY or WEATHER_API_KEY == "YOUR_API_KEY_HERE":
        print("⚠️ WARNING: WEATHER_API_KEY မထည့်သေးပါ")
    
    try:
        print(f"✅ Weather API: {WEATHER_API_KEY[:5]}...{WEATHER_API_KEY[-5:]}")
        print("🌾 Happy Farmer v1.0.1 စတင်နေပါသည်...")
        
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.LOCATION, location_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        application.add_error_handler(error_handler)
        
        print("✅ Bot ready!")
        print("👉 /start နှိပ်ပြီး စမ်းသပ်ပါ")
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Main error: {e}")
        print(f"❌ Bot စတင်ရာမှာ ပြဿနာ: {e}")

if __name__ == "__main__":
    main()
