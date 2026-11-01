# language: Python 3.11+, file: kory.py, target: Railway (Discord Bot)
# /ip /ip-list /dil /setlang

import discord
from discord import app_commands
from discord.ext import commands
import json
import urllib.request
import urllib.error
import asyncio
import io
import re
import os
from typing import Optional

# ─── CONFIG ───────────────────────────────────────────────────────────────────
BOT_TOKEN    = os.environ.get("BOT_TOKEN", "")
IPINFO_TOKEN = os.environ.get("IPINFO_TOKEN", "")
EMBED_COLOR  = 0x2B2D31
SUCCESS_COLOR= 0x57F287
ERROR_COLOR  = 0xED4245
WARN_COLOR   = 0xFEE75C
MAX_BULK     = 20
TIMEOUT      = 8
# ──────────────────────────────────────────────────────────────────────────────

# ─── I18N ─────────────────────────────────────────────────────────────────────
STRINGS = {
    "tr": {
        "ip_title":        "IP Raporu",
        "continent":       "Kita",
        "country":         "Ulke",
        "city_region":     "Sehir / Bolge",
        "district":        "Ilce",
        "zip":             "Posta Kodu",
        "timezone":        "Saat Dilimi",
        "isp":             "ISP",
        "org":             "Organizasyon",
        "as":              "AS",
        "coords":          "Koordinat",
        "status":          "Durum",
        "source":          "Kaynak",
        "proxy_vpn":       "Proxy/VPN",
        "hosting":         "Hosting/Datacenter",
        "clean":           "Temiz",
        "bulk_title":      "Toplu Sorgu",
        "bulk_success":    "basarili",
        "invalid_ips":     "Gecersiz IP'ler",
        "invalid_ip_msg":  "Gecersiz IP adresi",
        "empty_list":      "IP listesi bos.",
        "txt_only":        "Sadece .txt dosyasi kabul edilir.",
        "max_bulk":        "Maksimum {max} IP sorgulanabilir.",
        "no_valid":        "Gecerli IP bulunamadi.",
        "fail_title":      "Sorgu Basarisiz",
        "all_fail":        "Tum kaynaklar yanit vermedi.",
        "lang_set":        "Dil Turkce olarak ayarlandi.",
        "lang_set_server": "Sunucu dili Turkce olarak ayarlandi.",
        "no_perm":         "Bu komutu kullanmak icin yonetici yetkisi gereklidir.",
        "footer":          "Sorgulayan: {user}",
    },
    "en": {
        "ip_title":        "IP Report",
        "continent":       "Continent",
        "country":         "Country",
        "city_region":     "City / Region",
        "district":        "District",
        "zip":             "ZIP Code",
        "timezone":        "Timezone",
        "isp":             "ISP",
        "org":             "Organization",
        "as":              "AS Number",
        "coords":          "Coordinates",
        "status":          "Status",
        "source":          "Source",
        "proxy_vpn":       "Proxy/VPN",
        "hosting":         "Hosting/Datacenter",
        "clean":           "Clean",
        "bulk_title":      "Bulk Query",
        "bulk_success":    "successful",
        "invalid_ips":     "Invalid IPs",
        "invalid_ip_msg":  "Invalid IP address",
        "empty_list":      "IP list is empty.",
        "txt_only":        "Only .txt files are accepted.",
        "max_bulk":        "Maximum {max} IPs can be queried.",
        "no_valid":        "No valid IP found.",
        "fail_title":      "Query Failed",
        "all_fail":        "All sources failed to respond.",
        "lang_set":        "Language set to English.",
        "lang_set_server": "Server language set to English.",
        "no_perm":         "Administrator permission required.",
        "footer":          "Requested by: {user}",
    },
}

user_langs:   dict[int, str] = {}
server_langs: dict[int, str] = {}

def get_lang(interaction: discord.Interaction) -> str:
    if interaction.user.id in user_langs:
        return user_langs[interaction.user.id]
    if interaction.guild_id and interaction.guild_id in server_langs:
        return server_langs[interaction.guild_id]
    return "tr"

def t(interaction: discord.Interaction, key: str, **kwargs) -> str:
    lang = get_lang(interaction)
    s = STRINGS.get(lang, STRINGS["tr"]).get(key, key)
    return s.format(**kwargs) if kwargs else s

# ─── VALIDATION ───────────────────────────────────────────────────────────────
IP_RE = re.compile(
    r"^((\d{1,3}\.){3}\d{1,3}|([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4})$"
)

def valid_ip(ip: str) -> bool:
    return bool(IP_RE.match(ip.strip()))

# ─── SOURCES ──────────────────────────────────────────────────────────────────

def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "KoryBot/2.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode())

def fetch_ipapi(ip: str) -> Optional[dict]:
    try:
        fields = "status,message,continent,country,countryCode,regionName,city,district,zip,lat,lon,timezone,isp,org,as,proxy,hosting,query"
        d = _get(f"http://ip-api.com/json/{ip}?fields={fields}")
        if d.get("status") != "success":
            return None
        return {
            "query": d.get("query", ip), "continent": d.get("continent", "—"),
            "country": d.get("country", "—"), "countryCode": d.get("countryCode", "—"),
            "region": d.get("regionName", "—"), "city": d.get("city", "—"),
            "district": d.get("district") or "—", "zip": d.get("zip") or "—",
            "lat": d.get("lat"), "lon": d.get("lon"),
            "timezone": d.get("timezone", "—"), "isp": d.get("isp", "—"),
            "org": d.get("org", "—"), "as": d.get("as", "—"),
            "proxy": d.get("proxy", False), "hosting": d.get("hosting", False),
            "source": "ip-api.com",
        }
    except Exception:
        return None

def fetch_ipinfo(ip: str) -> Optional[dict]:
    try:
        token = f"?token={IPINFO_TOKEN}" if IPINFO_TOKEN else ""
        d = _get(f"https://ipinfo.io/{ip}/json{token}")
        if not d.get("ip"):
            return None
        lat = lon = None
        if loc := d.get("loc"):
            parts = loc.split(",")
            if len(parts) == 2:
                lat, lon = float(parts[0]), float(parts[1])
        return {
            "query": d.get("ip", ip), "continent": "—",
            "country": d.get("country", "—"), "countryCode": d.get("country", "—"),
            "region": d.get("region", "—"), "city": d.get("city", "—"),
            "district": "—", "zip": d.get("postal") or "—",
            "lat": lat, "lon": lon,
            "timezone": d.get("timezone", "—"), "isp": d.get("org", "—"),
            "org": d.get("org", "—"), "as": d.get("org", "—"),
            "proxy": False, "hosting": False,
            "source": "ipinfo.io",
        }
    except Exception:
        return None

def fetch_ipwho(ip: str) -> Optional[dict]:
    try:
        d = _get(f"https://ipwho.is/{ip}")
        if not d.get("success"):
            return None
        conn = d.get("connection", {})
        return {
            "query": d.get("ip", ip), "continent": d.get("continent", "—"),
            "country": d.get("country", "—"), "countryCode": d.get("country_code", "—"),
            "region": d.get("region", "—"), "city": d.get("city", "—"),
            "district": "—", "zip": d.get("postal") or "—",
            "lat": d.get("latitude"), "lon": d.get("longitude"),
            "timezone": d.get("timezone", {}).get("id", "—"),
            "isp": conn.get("isp", "—"), "org": conn.get("org", "—"),
            "as": f"AS{conn.get('asn', '—')}",
            "proxy": False, "hosting": False,
            "source": "ipwho.is",
        }
    except Exception:
        return None

def fetch_all(ip: str) -> dict:
    result = fetch_ipapi(ip) or fetch_ipinfo(ip) or fetch_ipwho(ip)
    return result if result else {"error": True, "query": ip}

async def async_fetch(ip: str) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, fetch_all, ip)

# ─── EMBEDS ───────────────────────────────────────────────────────────────────

def build_embed(data: dict, interaction: discord.Interaction) -> discord.Embed:
    if data.get("error"):
        e = discord.Embed(
            title=t(interaction, "fail_title"),
            description=t(interaction, "all_fail"),
            color=ERROR_COLOR,
        )
        e.set_footer(text=t(interaction, "footer", user=interaction.user))
        return e

    flags = []
    if data.get("proxy"):   flags.append(t(interaction, "proxy_vpn"))
    if data.get("hosting"): flags.append(t(interaction, "hosting"))
    if not flags:           flags.append(t(interaction, "clean"))

    e = discord.Embed(
        title=f"{t(interaction, 'ip_title')} — `{data['query']}`",
        color=EMBED_COLOR,
    )
    e.add_field(name=t(interaction, "continent"),   value=data["continent"],                             inline=True)
    e.add_field(name=t(interaction, "country"),     value=f"{data['country']} ({data['countryCode']})", inline=True)
    e.add_field(name=t(interaction, "city_region"), value=f"{data['city']} / {data['region']}",         inline=True)
    e.add_field(name=t(interaction, "district"),    value=data["district"],                              inline=True)
    e.add_field(name=t(interaction, "zip"),         value=data["zip"],                                   inline=True)
    e.add_field(name=t(interaction, "timezone"),    value=data["timezone"],                              inline=True)
    e.add_field(name=t(interaction, "isp"),         value=data["isp"],                                   inline=False)
    e.add_field(name=t(interaction, "org"),         value=data["org"],                                   inline=True)
    e.add_field(name=t(interaction, "as"),          value=data["as"],                                    inline=True)

    if data.get("lat") and data.get("lon"):
        e.add_field(
            name=t(interaction, "coords"),
            value=f"[{data['lat']}, {data['lon']}](https://www.google.com/maps?q={data['lat']},{data['lon']})",
            inline=True,
        )

    e.add_field(name=t(interaction, "status"), value=" | ".join(flags),     inline=True)
    e.add_field(name=t(interaction, "source"), value=f"`{data['source']}`", inline=True)
    e.set_footer(text=t(interaction, "footer", user=interaction.user))
    return e

def build_txt(results: list[dict]) -> str:
    lines = []
    for d in results:
        if d.get("error"):
            lines.append(f"[FAIL] {d.get('query', '?')} -> all sources failed\n{'─'*45}")
            continue
        lines.append(
            f"IP      : {d['query']}\n"
            f"Country : {d['country']} ({d['countryCode']})\n"
            f"City    : {d['city']} / {d['region']}\n"
            f"ISP     : {d['isp']}\n"
            f"Org     : {d['org']}\n"
            f"AS      : {d['as']}\n"
            f"Proxy   : {'Yes' if d.get('proxy') else 'No'} | "
            f"Hosting : {'Yes' if d.get('hosting') else 'No'}\n"
            f"Coords  : {d.get('lat')}, {d.get('lon')}\n"
            f"Source  : {d['source']}\n"
            f"{'─'*45}"
        )
    return "\n".join(lines)

# ─── BOT ──────────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
bot  = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

@tree.command(name="ip", description="Query an IP address / Bir IP adresini sorgular")
@app_commands.describe(address="IPv4 or IPv6 / IPv4 veya IPv6 adresi")
async def cmd_ip(interaction: discord.Interaction, address: str):
    address = address.strip()
    if not valid_ip(address):
        await interaction.response.send_message(
            f"{t(interaction, 'invalid_ip_msg')}: `{address}`", ephemeral=True
        )
        return
    await interaction.response.defer()
    data = await async_fetch(address)
    await interaction.followup.send(embed=build_embed(data, interaction))


@tree.command(name="ip-list", description="Query multiple IPs / Birden fazla IP sorgular")
@app_commands.describe(
    list="Comma-separated IPs / Virgülle ayrılmış IP'ler",
    file=".txt file, one IP per line / Her satırda bir IP"
)
async def cmd_ip_list(
    interaction: discord.Interaction,
    list: Optional[str] = None,
    file: Optional[discord.Attachment] = None,
):
    await interaction.response.defer()
    raw: list[str] = []

    if file:
        if not file.filename.endswith(".txt"):
            await interaction.followup.send(t(interaction, "txt_only"), ephemeral=True)
            return
        raw = (await file.read()).decode("utf-8", errors="ignore").splitlines()
        raw = [ln.strip() for ln in raw if ln.strip()]

    if list:
        raw += [ip.strip() for ip in list.split(",") if ip.strip()]

    if not raw:
        await interaction.followup.send(t(interaction, "empty_list"), ephemeral=True)
        return

    valid   = [ip for ip in raw if valid_ip(ip)]
    invalid = [ip for ip in raw if not valid_ip(ip)]

    if len(valid) > MAX_BULK:
        await interaction.followup.send(t(interaction, "max_bulk", max=MAX_BULK), ephemeral=True)
        return
    if not valid:
        await interaction.followup.send(t(interaction, "no_valid"), ephemeral=True)
        return

    results = list(await asyncio.gather(*[async_fetch(ip) for ip in valid]))
    for ip, res in zip(valid, results):
        res.setdefault("query", ip)

    success = sum(1 for r in results if not r.get("error"))
    summary = discord.Embed(
        title=f"{t(interaction, 'bulk_title')} — {success}/{len(valid)} {t(interaction, 'bulk_success')}",
        color=SUCCESS_COLOR if success == len(valid) else WARN_COLOR,
    )
    if invalid:
        summary.add_field(
            name=t(interaction, "invalid_ips"),
            value=", ".join(f"`{ip}`" for ip in invalid),
            inline=False,
        )
    summary.set_footer(text=t(interaction, "footer", user=interaction.user))

    await interaction.followup.send(
        embed=summary,
        file=discord.File(
            fp=io.BytesIO(build_txt(results).encode("utf-8")),
            filename="kory_results.txt"
        )
    )


@tree.command(name="dil", description="Kisisel dilinizi secin / Set your language")
@app_commands.choices(secim=[
    app_commands.Choice(name="Turkce", value="tr"),
    app_commands.Choice(name="English", value="en"),
])
async def cmd_dil(interaction: discord.Interaction, secim: str):
    user_langs[interaction.user.id] = secim
    await interaction.response.send_message(STRINGS[secim]["lang_set"], ephemeral=True)


@tree.command(name="setlang", description="[Admin] Set default server language")
@app_commands.choices(lang=[
    app_commands.Choice(name="Turkish", value="tr"),
    app_commands.Choice(name="English", value="en"),
])
async def cmd_setlang(interaction: discord.Interaction, lang: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(t(interaction, "no_perm"), ephemeral=True)
        return
    if interaction.guild_id:
        server_langs[interaction.guild_id] = lang
    await interaction.response.send_message(STRINGS[lang]["lang_set_server"], ephemeral=True)


@bot.event
async def on_ready():
    await tree.sync()
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="/ip | Kory v2.0")
    )
    print(f"[KORY] {bot.user} online.")

if not BOT_TOKEN:
    raise ValueError("[KORY] BOT_TOKEN environment variable is not set.")

bot.run(BOT_TOKEN)
