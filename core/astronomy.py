"""
ماژول نجوم — astronomy.py
تمام توابع مربوط به رویدادهای نجومی با استفاده از skyfield
"""
import logging
logger = logging.getLogger(__name__)

import os
from datetime import datetime, timezone, timedelta

# تایم‌زون ایران
IR = timezone(timedelta(hours=3, minutes=30))
# مختصات تهران
LAT, LON = 35.6892, 51.3890

# path فایل ephemeris
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EPH_PATH = os.path.join(BASE_DIR, "de421.bsp")

def _load_skyfield():
    from skyfield.api import load, wgs84, N, E
    from skyfield import almanac
    ts  = load.timescale()
    eph = load(EPH_PATH)
    loc = wgs84.latlon(LAT * N, LON * E)
    return ts, eph, loc, almanac

def _az_to_direction(az: float) -> str:
    """تبدیل آزیموت به جهت فارسی"""
    dirs = [
        (22.5,  "شمال"),
        (67.5,  "شمال‌شرق"),
        (112.5, "شرق"),
        (157.5, "جنوب‌شرق"),
        (202.5, "جنوب"),
        (247.5, "جنوب‌غرب"),
        (292.5, "غرب"),
        (337.5, "شمال‌غرب"),
        (360.0, "شمال"),
    ]
    for limit, name in dirs:
        if az < limit:
            return name
    return "شمال"

def moon_phase_accurate(now_ir: datetime) -> str:
    """فاز دقیق ماه"""
    try:
        ts, eph, _, almanac = _load_skyfield()
        t = ts.from_datetime(now_ir)
        deg = almanac.moon_phase(eph, t).degrees
        if deg < 22.5:    return "🌑 ماه نو (New Moon)"
        elif deg < 67.5:  return "🌒 هلال رو به رشد (Waxing Crescent)"
        elif deg < 112.5: return "🌓 ربع اول (First Quarter)"
        elif deg < 157.5: return "🌔 گیبوس رو به رشد (Waxing Gibbous)"
        elif deg < 202.5: return "🌕 ماه کامل (Full Moon)"
        elif deg < 247.5: return "🌖 گیبوس رو به کاهش (Waning Gibbous)"
        elif deg < 292.5: return "🌗 ربع آخر (Last Quarter)"
        elif deg < 337.5: return "🌘 هلال رو به کاهش (Waning Crescent)"
        else:             return "🌑 ماه نو (New Moon)"
    except Exception as e:
        logger.error(f"خطای فاز ماه: {e}")
        return None

def moon_constellation(now_ir: datetime) -> tuple:
    """صورت فلکی ماه و توضیح"""
    CONSTELLATIONS = {
        "Aries":       ("حمل (Aries) ♈",       "نماد آغاز و انرژی — شبی برای شروع‌های تازه"),
        "Taurus":      ("ثور (Taurus) ♉",       "نماد پایداری و زیبایی — شبی آرام برای لذت بردن"),
        "Gemini":      ("جوزا (Gemini) ♊",      "نماد دوگانگی و تضاد — شبی مناسب برای گفتگو"),
        "Cancer":      ("سرطان (Cancer) ♋",     "نماد احساس و خانه — شبی برای درون‌نگری"),
        "Leo":         ("اسد (Leo) ♌",          "نماد قدرت و اراده — شبی برای ابراز وجود"),
        "Virgo":       ("سنبله (Virgo) ♍",      "نماد نظم و دقت — شبی مناسب برای برنامه‌ریزی"),
        "Libra":       ("میزان (Libra) ♎",      "نماد تعادل و عدالت — شبی برای تصمیم‌گیری"),
        "Scorpius":    ("عقرب (Scorpius) ♏",    "نماد تحول و رمز — شبی پرانرژی و حساس"),
        "Ophiuchus":   ("حواء (Ophiuchus)",      "صورت فلکی چهاردهم — نماد دانش و شفا"),
        "Sagittarius": ("قوس (Sagittarius) ♐",  "نماد آزادی و جستجو — شبی برای رویاپردازی"),
        "Capricornus": ("جدی (Capricorn) ♑",    "نماد پشتکار و هدف — شبی برای تمرکز"),
        "Aquarius":    ("دلو (Aquarius) ♒",     "نماد نوآوری و آینده — شبی برای ایده‌های نو"),
        "Pisces":      ("حوت (Pisces) ♓",       "نماد خیال و شهود — شبی برای خلاقیت"),
    }
    try:
        from skyfield.api import Star
        ts, eph, _, _ = _load_skyfield()
        t = ts.from_datetime(now_ir)
        earth = eph['earth']
        astrometric = earth.at(t).observe(eph['moon'])
        ra, dec, _ = astrometric.apparent().radec()
        ra_hours = ra.hours

        boundaries = [
            (1.87,  "Pisces"),
            (3.33,  "Aries"),
            (5.53,  "Taurus"),
            (7.50,  "Gemini"),
            (9.22,  "Cancer"),
            (11.33, "Leo"),
            (13.67, "Virgo"),
            (15.17, "Libra"),
            (16.17, "Scorpius"),
            (17.60, "Ophiuchus"),
            (19.92, "Sagittarius"),
            (21.33, "Capricornus"),
            (22.83, "Aquarius"),
            (24.00, "Pisces"),
        ]
        const_key = "Pisces"
        for limit, name in boundaries:
            if ra_hours < limit:
                const_key = name
                break

        return CONSTELLATIONS.get(const_key, (const_key, ""))
    except Exception as e:
        logger.error(f"خطای صورت فلکی: {e}")
        return None, None

def next_moon_events(now_ir: datetime) -> list:
    """رویدادهای ماه ۳۰ روز آینده"""
    try:
        ts, eph, _, almanac = _load_skyfield()
        t0 = ts.from_datetime(now_ir)
        t1 = ts.from_datetime(now_ir + timedelta(days=30))
        times, events = almanac.find_discrete(t0, t1, almanac.moon_phases(eph))
        names = ['🌑 ماه نو', '🌓 ربع اول', '🌕 ماه کامل', '🌗 ربع آخر']
        result = []
        for t, e in zip(times, events):
            dt = t.astimezone(IR)
            result.append(f"{names[e]} — {dt.strftime('%d %b ساعت %H:%M')}")
        return result
    except Exception as e:
        logger.error(f"خطای رویداد ماه: {e}")
        return []

def next_solstice_equinox(now_ir: datetime) -> str:
    """انقلاب و اعتدال فصلی بعدی"""
    try:
        ts, eph, _, almanac = _load_skyfield()
        t0 = ts.from_datetime(now_ir)
        t1 = ts.from_datetime(now_ir + timedelta(days=100))
        times, events = almanac.find_discrete(t0, t1, almanac.seasons(eph))
        names = [
            '🌸 اعتدال بهاری (Spring Equinox)',
            '☀️ انقلاب تابستانی (Summer Solstice)',
            '🍂 اعتدال پاییزی (Autumn Equinox)',
            '❄️ انقلاب زمستانی (Winter Solstice)',
        ]
        if times:
            dt = times[0].astimezone(IR)
            return f"{names[events[0]]} — {dt.strftime('%d %b ساعت %H:%M')}"
    except Exception as e:
        logger.error(f"خطای فصل: {e}")
    return None

def closest_planet(now_ir: datetime) -> str:
    """نزدیک‌ترین سیاره به زمین"""
    try:
        ts, eph, _, _ = _load_skyfield()
        t = ts.from_datetime(now_ir)
        earth = eph['earth']
        planets = {
            'زهره ♀': 'venus',
            'مریخ ♂': 'mars',
            'مشتری ♃': 'jupiter barycenter',
            'زحل ♄': 'saturn barycenter',
        }
        distances = {}
        for name, key in planets.items():
            astrometric = earth.at(t).observe(eph[key])
            distances[name] = astrometric.distance().au
        closest = min(distances, key=distances.get)
        return f"🪐 نزدیک‌ترین سیاره به زمین: {closest} ({distances[closest]:.2f} AU)"
    except Exception as e:
        logger.error(f"خطای نزدیک‌ترین سیاره: {e}")
        return None

def planets_position(now_ir: datetime) -> list:
    """موقعیت و طلوع/غروب سیارات"""
    try:
        from skyfield.api import wgs84
        ts, eph, loc, almanac = _load_skyfield()
        t_now = ts.from_datetime(now_ir)
        t0 = ts.from_datetime(now_ir.replace(hour=0, minute=0, second=0))
        t1 = ts.from_datetime(now_ir.replace(hour=23, minute=59, second=59))
        observer = wgs84.latlon(LAT, LON)

        planets = {
            'زهره ♀':    'venus',
            'مریخ ♂':    'mars',
            'مشتری ♃':   'jupiter barycenter',
            'زحل ♄':     'saturn barycenter',
        }
        result = []
        for name, key in planets.items():
            try:
                # موقعیت فعلی
                astro = (eph['earth'] + observer).at(t_now).observe(eph[key])
                alt, az, dist = astro.apparent().altaz()
                if alt.degrees > 5:
                    direction = _az_to_direction(az.degrees)
                    pos = f"قابل رویت — {direction}، ارتفاع {alt.degrees:.0f}° ✅"
                else:
                    pos = "در حال حاضر زیر افق ❌"

                # طلوع و غروب
                f = almanac.risings_and_settings(eph, eph[key], loc)
                times, events = almanac.find_discrete(t0, t1, f)
                rise_set = []
                for t, e in zip(times, events):
                    dt = t.astimezone(IR)
                    rise_set.append(f"{'طلوع 🌅' if e else 'غروب 🌇'} {dt.strftime('%H:%M')}")

                rs_text = " | ".join(rise_set) if rise_set else "—"
                result.append(f"• {name}: {pos}\n  ⏰ {rs_text}\n")
            except Exception as e:
                logger.error(f"خطای سیاره {name}: {e}")
        return result
    except Exception as e:
        logger.error(f"خطای موقعیت سیارات: {e}")
        return []

def nav_stars_position(now_ir: datetime) -> list:
    """موقعیت ستاره‌های ناوبری"""
    STARS_INFO = {
        "Polaris":  ("قطبی (Polaris)", "راهنمای شمال از دوران باستان"),
        "Sirius":   ("شعرای یمانی (Sirius)", "درخشان‌ترین ستاره آسمان"),
        "Antares":  ("قلب‌العقرب (Antares)", "قلب صورت فلکی عقرب"),
        "Vega":     ("النسر الواقع (Vega)", "یکی از سه ستاره مثلث تابستانی"),
    }
    # مختصات ستاره‌ها (RA, Dec)
    STARS_COORDS = {
        "Polaris": (37.9529, 89.2641),
        "Sirius":  (101.2872, -16.7161),
        "Antares": (247.3519, -26.4320),
        "Vega":    (279.2347, 38.7837),
    }
    try:
        from skyfield.api import wgs84, Star
        ts, eph, _, _ = _load_skyfield()
        t = ts.from_datetime(now_ir)
        observer = wgs84.latlon(LAT, LON)
        earth = eph['earth']
        result = []
        for key, (name, desc) in STARS_INFO.items():
            try:
                ra_deg, dec_deg = STARS_COORDS[key]
                star = Star(ra_hours=ra_deg/15, dec_degrees=dec_deg)
                astro = (earth + observer).at(t).observe(star)
                alt, az, _ = astro.apparent().altaz()
                if alt.degrees > 5:
                    direction = _az_to_direction(az.degrees)
                    result.append(
                        f"⭐ {name}\n"
                        f"  📍 {direction}، ارتفاع {alt.degrees:.0f}° ✅\n"
                        f"  💡 {desc}\n"
                    )
                else:
                    result.append(
                        f"⭐ {name}\n"
                        f"  📍 در حال حاضر زیر افق ❌\n"
                        f"  💡 {desc}\n"
                    )
            except Exception as e:
                logger.error(f"خطای ستاره {key}: {e}")
        return result
    except Exception as e:
        logger.error(f"خطای ستاره‌های ناوبری: {e}")
        return []


def visible_constellations(now_ir: datetime) -> list:
    """صورت‌های فلکی قابل رویت از تهران"""
    CONSTELLATIONS = [
        ("Orion",       "شکارچی (Orion)",        (83.82,  5.39),  "پرجمعیت‌ترین صورت فلکی — سه ستاره کمربند اوریون معروفند"),
        ("Scorpius",    "عقرب (Scorpius) ♏",     (247.35,-26.43), "قلبش ستاره سرخ قلب‌العقرب (Antares) است"),
        ("Gemini",      "جوزا (Gemini) ♊",       (113.65, 31.89), "دو ستاره روشن کاستور و پولوکس چشمانش هستند"),
        ("Leo",         "اسد (Leo) ♌",            (152.09, 11.97), "ستاره قلب‌الاسد (Regulus) قلب این شیر آسمانی است"),
        ("Cygnus",      "دجاجه (Cygnus)",          (305.56, 40.26), "صلیب شمال — النسر الطائر (Deneb) دم قوست"),
        ("Perseus",     "برساووش (Perseus)",       (51.08,  48.05), "قهرمان اسطوره‌ای که مدوسا را کشت"),
        ("Aquila",      "عقاب (Aquila)",           (286.35,  8.87), "النسر الطائر (Altair) یکی از سه ستاره مثلث تابستانی"),
        ("Sagittarius", "قوس (Sagittarius) ♐",   (283.82,-29.83), "به سمت مرکز کهکشان راه شیری اشاره دارد"),
        ("Virgo",       "سنبله (Virgo) ♍",        (201.30, -11.16),"ستاره سماک اعزل (Spica) درخشان‌ترین ستاره‌اش است"),
        ("Cassiopeia",  "ذات‌الکرسی (Cassiopeia)",(10.13,  59.15), "شکل W در آسمان شمالی — همیشه نزدیک قطبی است"),
    ]
    try:
        from skyfield.api import Star, wgs84
        ts, eph, _, _ = _load_skyfield()
        t = ts.from_datetime(now_ir)
        observer = wgs84.latlon(LAT, LON)
        earth = eph['earth']
        result = []
        for key, name, (ra_deg, dec_deg), desc in CONSTELLATIONS:
            try:
                star = Star(ra_hours=ra_deg/15, dec_degrees=dec_deg)
                astro = (earth + observer).at(t).observe(star)
                alt, az, _ = astro.apparent().altaz()
                if alt.degrees > 10:
                    direction = _az_to_direction(az.degrees)
                    result.append(
                        f"🌌 {name}\n"
                        f"  📍 {direction}، ارتفاع {alt.degrees:.0f}°\n"
                        f"  ✨ {desc}\n"
                    )
            except Exception as e:
                logger.error(f"خطای صورت فلکی {key}: {e}")
        return result
    except Exception as e:
        logger.error(f"خطای صورت‌های فلکی: {e}")
        return []

def get_sky_report(now_ir: datetime) -> str:
    """گزارش کامل آسمان"""
    lines = ["🔭 آسمان امشب\n"]

    # فاز ماه
    phase = moon_phase_accurate(now_ir)
    if phase:
        lines.append(f"🌙 فاز ماه: {phase}")

    # صورت فلکی ماه
    const_name, const_desc = moon_constellation(now_ir)
    if const_name:
        lines.append(f"🌙 ماه امشب در صورت فلکی {const_name}")
        if const_desc:
            lines.append(f"✨ {const_desc}")

    # رویدادهای ماه
    moon_events = next_moon_events(now_ir)
    if moon_events:
        lines.append("\n📅 رویدادهای ماه (۳۰ روز آینده):")
        for e in moon_events[:3]:
            lines.append(f"  • {e}")

    # فصل بعدی
    season = next_solstice_equinox(now_ir)
    if season:
        lines.append(f"\n🗓 فصل بعدی: {season}")

    # نزدیک‌ترین سیاره
    closest = closest_planet(now_ir)
    if closest:
        lines.append(f"\n{closest}")

    # موقعیت سیارات + طلوع/غروب
    planets = planets_position(now_ir)
    if planets:
        lines.append("\n🪐 سیارات (موقعیت فعلی + طلوع/غروب به وقت تهران):")
        for p in planets:
            lines.append(p)

    # صورت‌های فلکی قابل رویت
    consts = visible_constellations(now_ir)
    if consts:
        lines.append("\n🌌 صورت‌های فلکی قابل رویت (همین لحظه از تهران):")
        for c in consts:
            lines.append(c)

    # ستاره‌های ناوبری
    stars = nav_stars_position(now_ir)
    if stars:
        lines.append("\n⭐ ستاره‌های ناوبری (الان از تهران):")
        for s in stars:
            lines.append(s)

    return "\n".join(lines)
