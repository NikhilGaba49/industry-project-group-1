"""Domain.com.au Victorian rental scraper -> data/listings.parquet.

Domain's WAF hard-blocks any Selenium/ChromeDriver session outright, even
undetected-chromedriver, with an "Access Denied" -- testing pointed at
detection of the DevTools/CDP debugging channel itself. So instead of a
webdriver, this drives a real, completely ordinary Google Chrome via macOS
Apple Events (no debugging port, no automation flags at all).

One-time setup: in Chrome, View > Developer > Allow JavaScript from Apple
Events, and approve the macOS Automation permission prompt on first run.
macOS only.
"""

import json
import random
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

BASE = "https://www.domain.com.au"
OUT_PATH = Path("data") / "listings.parquet"

MAX_PAGES_PER_SUBURB = 20
MIN_DELAY, MAX_DELAY = 2.0, 5.0

SUBURB_TEXT = (
    # Melbourne CBD & inner
    "Melbourne 3000, East Melbourne 3002, West Melbourne 3003, Southbank 3006, "
    "Docklands 3008, South Melbourne 3205, Albert Park 3206, Middle Park 3206, "
    "Port Melbourne 3207, North Melbourne 3051, Parkville 3052, Carlton 3053, "
    "Carlton North 3054, Princes Hill 3054, Fitzroy 3065, Fitzroy North 3068, "
    "Collingwood 3066, Abbotsford 3067, Clifton Hill 3068, Richmond 3121, "
    "Cremorne 3121, Burnley 3121, Kensington 3031, Flemington 3031, "
    # Inner north
    "Brunswick 3056, Brunswick East 3057, Brunswick West 3055, Coburg 3058, "
    "Coburg North 3058, Pascoe Vale 3044, Pascoe Vale South 3044, Oak Park 3046, "
    "Glenroy 3046, Hadfield 3046, Fawkner 3060, Northcote 3070, Thornbury 3071, "
    "Preston 3072, Reservoir 3073, Thomastown 3074, Lalor 3075, Epping 3076, "
    "Fairfield 3078, Alphington 3078, Ivanhoe 3079, Ivanhoe East 3079, "
    "Heidelberg 3084, Rosanna 3084, Viewbank 3084, Eaglemont 3084, "
    "Heidelberg West 3081, Heidelberg Heights 3081, Bellfield 3081, Mill Park 3082, "
    "Bundoora 3083, Kingsbury 3083, Macleod 3085, Watsonia 3087, "
    "Watsonia North 3087, Greensborough 3088, Briar Hill 3088, Diamond Creek 3089, "
    "Plenty 3090, Yarrambat 3091, Lower Plenty 3093, Montmorency 3094, Eltham 3095, "
    "Eltham North 3095, Research 3095, Wattle Glen 3096, Hurstbridge 3099, "
    # Outer north
    "Wollert 3750, South Morang 3752, Beveridge 3753, Mernda 3754, Doreen 3754, "
    "Wallan 3756, Whittlesea 3757, Broadford 3658, Kilmore 3764, Kinglake 3763, "
    "Craigieburn 3064, Roxburgh Park 3064, Mickleham 3064, Kalkallo 3064, "
    "Donnybrook 3064, Greenvale 3059, Meadow Heights 3048, Coolaroo 3048, "
    "Broadmeadows 3047, Dallas 3047, Jacana 3047, Campbellfield 3061, Somerton 3062, "
    "Westmeadows 3049, Attwood 3049, Gladstone Park 3043, Tullamarine 3043, "
    # North west
    "Airport West 3042, Niddrie 3042, Keilor Park 3042, Essendon 3040, "
    "Essendon West 3040, Aberfeldie 3040, Essendon North 3041, Strathmore 3041, "
    "Strathmore Heights 3041, Moonee Ponds 3039, Ascot Vale 3032, Travancore 3032, "
    "Maribyrnong 3032, Keilor East 3033, Avondale Heights 3034, Keilor 3036, "
    "Sydenham 3037, Delahey 3037, Hillside 3037, Taylors Hill 3037, "
    "Taylors Lakes 3038, Keilor Downs 3038, Keilor Lodge 3038, Sunbury 3429, "
    "Diggers Rest 3427, "
    # West
    "Footscray 3011, Seddon 3011, West Footscray 3012, Maidstone 3012, "
    "Kingsville 3012, Tottenham 3012, Brooklyn 3012, Yarraville 3013, Newport 3015, "
    "Spotswood 3015, Williamstown 3016, Williamstown North 3016, Altona 3018, "
    "Braybrook 3019, Sunshine 3020, Sunshine North 3020, Sunshine West 3020, "
    "Albion 3020, St Albans 3021, Kealba 3021, Kings Park 3021, Albanvale 3021, "
    "Ardeer 3022, Deer Park 3023, Caroline Springs 3023, Burnside 3023, "
    "Burnside Heights 3023, Cairnlea 3023, Ravenhall 3023, Altona North 3025, "
    "Derrimut 3026, Laverton North 3026, Williams Landing 3027, Laverton 3028, "
    "Altona Meadows 3028, Seabrook 3028, Hoppers Crossing 3029, Tarneit 3029, "
    "Truganina 3029, Werribee 3030, Point Cook 3030, Wyndham Vale 3024, "
    "Manor Lakes 3024, Rockbank 3335, Plumpton 3335, Thornhill Park 3335, "
    "Aintree 3336, Fraser Rise 3336, Deanside 3336, Melton 3337, Melton West 3337, "
    "Melton South 3338, Brookfield 3338, Weir Views 3338, Strathtulloh 3338, "
    "Bacchus Marsh 3340, Ballan 3342, "
    # Inner east
    "Kew 3101, Kew East 3102, Balwyn 3103, Deepdene 3103, Balwyn North 3104, "
    "Bulleen 3105, Templestowe 3106, Templestowe Lower 3107, Doncaster 3108, "
    "Doncaster East 3109, Donvale 3111, Warrandyte 3113, Park Orchards 3114, "
    "Wonga Park 3115, Chirnside Park 3116, Hawthorn 3122, Hawthorn East 3123, "
    "Camberwell 3124, Burwood 3125, Canterbury 3126, Surrey Hills 3127, "
    "Mont Albert 3127, Box Hill 3128, Box Hill South 3128, Box Hill North 3129, "
    "Mont Albert North 3129, Blackburn 3130, Blackburn North 3130, "
    "Blackburn South 3130, Nunawading 3131, Forest Hill 3131, Mitcham 3132, "
    "Vermont 3133, Vermont South 3133, "
    # Outer east
    "Ringwood 3134, Ringwood North 3134, Ringwood East 3135, Heathmont 3135, "
    "Croydon 3136, Croydon North 3136, Croydon South 3136, Croydon Hills 3136, "
    "Kilsyth 3137, Mooroolbark 3138, Wandin North 3139, Seville 3139, Lilydale 3140, "
    "Montrose 3765, Mount Evelyn 3796, Silvan 3795, Coldstream 3770, Yarra Glen 3775, "
    "Healesville 3777, Marysville 3779, Yarra Junction 3797, Warburton 3799, "
    "Mount Dandenong 3767, Olinda 3788, Sassafras 3787, Kallista 3791, Monbulk 3793, "
    "Emerald 3782, Cockatoo 3781, Gembrook 3783, "
    # South east (inner)
    "South Yarra 3141, Toorak 3142, Armadale 3143, Malvern 3144, Kooyong 3144, "
    "Malvern East 3145, Caulfield East 3145, Glen Iris 3146, Ashburton 3147, "
    "Ashwood 3147, Chadstone 3148, Mount Waverley 3149, Glen Waverley 3150, "
    "Wheelers Hill 3150, Burwood East 3151, Wantirna 3152, Wantirna South 3152, "
    "Bayswater 3153, Bayswater North 3153, Boronia 3155, Ferntree Gully 3156, "
    "Upper Ferntree Gully 3156, Lysterfield 3156, Upwey 3158, Belgrave 3160, "
    "Tecoma 3160, Caulfield North 3161, Caulfield 3162, Caulfield South 3162, "
    "Carnegie 3163, Murrumbeena 3163, Glen Huntly 3163, Bentleigh East 3165, "
    "Oakleigh 3166, Oakleigh East 3166, Hughesdale 3166, Oakleigh South 3167, "
    "Clayton 3168, Notting Hill 3168, Clayton South 3169, Clarinda 3169, "
    "Mulgrave 3170, Springvale 3171, Springvale South 3172, Dingley Village 3172, "
    "Keysborough 3173, Noble Park 3174, Dandenong 3175, Dandenong North 3175, "
    "Doveton 3177, Rowville 3178, Scoresby 3179, Knoxfield 3180, "
    # Bayside & southern
    "Prahran 3181, Windsor 3181, St Kilda 3182, St Kilda West 3182, "
    "St Kilda East 3183, Balaclava 3183, Elwood 3184, Elsternwick 3185, "
    "Ripponlea 3185, Gardenvale 3185, Brighton 3186, Brighton East 3187, "
    "Hampton 3188, Hampton East 3188, Moorabbin 3189, Highett 3190, "
    "Sandringham 3191, Cheltenham 3192, Black Rock 3193, Beaumaris 3193, "
    "Mentone 3194, Mordialloc 3195, Parkdale 3195, Aspendale 3195, "
    "Aspendale Gardens 3195, Braeside 3195, Edithvale 3196, Chelsea 3196, "
    "Chelsea Heights 3196, Bonbeach 3196, Carrum 3197, Patterson Lakes 3197, "
    "Seaford 3198, Frankston 3199, Frankston South 3199, Frankston North 3200, "
    "Carrum Downs 3201, Heatherton 3202, Bentleigh 3204, McKinnon 3204, Ormond 3204, "
    # Casey / Cardinia
    "Endeavour Hills 3802, Hallam 3803, Narre Warren 3805, Narre Warren South 3805, "
    "Berwick 3806, Beaconsfield 3807, Officer 3809, Pakenham 3810, Nar Nar Goon 3812, "
    "Garfield 3814, Bunyip 3815, Hampton Park 3976, Lynbrook 3975, Lyndhurst 3975, "
    "Cranbourne 3977, Cranbourne East 3977, Cranbourne North 3977, "
    "Cranbourne West 3977, Cranbourne South 3977, Botanic Ridge 3977, "
    "Devon Meadows 3977, Skye 3977, Clyde 3978, Clyde North 3978, Tooradin 3980, "
    "Koo Wee Rup 3981, "
    # Mornington Peninsula
    "Langwarrin 3910, Baxter 3911, Somerville 3912, Pearcedale 3912, Tyabb 3913, "
    "Hastings 3915, Bittern 3918, Crib Point 3919, Balnarring 3926, Flinders 3929, "
    "Mount Eliza 3930, Mornington 3931, Mount Martha 3934, Dromana 3936, "
    "Safety Beach 3936, Red Hill 3937, Rosebud 3939, Rye 3941, Blairgowrie 3942, "
    "Sorrento 3943, Portsea 3944, Cowes 3922, San Remo 3925, "
    # Geelong & Bellarine
    "Geelong 3220, Newtown 3220, South Geelong 3220, Geelong West 3218, "
    "Herne Hill 3218, Manifold Heights 3218, East Geelong 3219, Belmont 3216, "
    "Highton 3216, Waurn Ponds 3216, Grovedale 3216, Marshall 3216, "
    "Armstrong Creek 3217, North Geelong 3215, Bell Park 3215, Bell Post Hill 3215, "
    "Hamlyn Heights 3215, Corio 3214, Norlane 3214, Lara 3212, Leopold 3224, "
    "Drysdale 3222, Clifton Springs 3222, Portarlington 3223, St Leonards 3223, "
    "Ocean Grove 3226, Barwon Heads 3227, Torquay 3228, Jan Juc 3228, Anglesea 3230, "
    "Lorne 3232, Apollo Bay 3233, Winchelsea 3241, Colac 3250, "
    # South west Victoria
    "Camperdown 3260, Terang 3264, Warrnambool 3280, Koroit 3282, Port Fairy 3284, "
    "Hamilton 3300, Heywood 3304, Portland 3305, Casterton 3311, "
    # Ballarat & central west
    "Ballarat Central 3350, Ballarat East 3350, Ballarat North 3350, Alfredton 3350, "
    "Mount Clear 3350, Mount Helen 3350, Miners Rest 3352, Wendouree 3355, "
    "Sebastopol 3356, Delacombe 3356, Buninyong 3357, Creswick 3363, Clunes 3370, "
    "Talbot 3371, Beaufort 3373, Ararat 3377, Stawell 3380, Horsham 3400, Nhill 3418, "
    "Warracknabeal 3393, St Arnaud 3478, Maryborough 3465, Daylesford 3460, "
    "Castlemaine 3450, Kyneton 3444, Woodend 3442, Macedon 3440, Gisborne 3437, "
    "Romsey 3434, Riddells Creek 3431, "
    # Bendigo & north central
    "Bendigo 3550, Kennington 3550, Flora Hill 3550, Strathdale 3550, "
    "White Hills 3550, Golden Square 3555, Kangaroo Flat 3555, Eaglehawk 3556, "
    "California Gully 3556, Strathfieldsaye 3551, Epsom 3551, Junortoun 3551, "
    "Maiden Gully 3551, Elmore 3558, Rochester 3561, Echuca 3564, Heathcote 3523, "
    "Nagambie 3608, Kyabram 3620, Tatura 3616, Mooroopna 3629, Shepparton 3630, "
    "Numurkah 3636, Cobram 3644, "
    # North east Victoria
    "Seymour 3660, Euroa 3666, Benalla 3672, Wangaratta 3677, Rutherglen 3685, "
    "Wodonga 3690, Mount Beauty 3699, Alexandra 3714, Yea 3717, Mansfield 3722, "
    "Yarrawonga 3730, Myrtleford 3737, Bright 3741, Beechworth 3747, "
    # Gippsland
    "Warragul 3820, Drouin 3818, Longwarry 3816, Yarragon 3823, Trafalgar 3824, "
    "Moe 3825, Newborough 3825, Yallourn North 3825, Neerim South 3831, Morwell 3840, "
    "Churchill 3842, Traralgon 3844, Rosedale 3847, Sale 3850, Heyfield 3858, "
    "Maffra 3860, Stratford 3862, Mirboo North 3871, Bairnsdale 3875, "
    "Paynesville 3880, Orbost 3888, Omeo 3898, Lakes Entrance 3909, Korumburra 3950, "
    "Leongatha 3953, Foster 3960, Yarram 3971, Wonthaggi 3995, Inverloch 3996"
)

SUBURBS = [
    (entry.rsplit(" ", 1)[0], int(entry.rsplit(" ", 1)[1]))
    for entry in (part.strip() for part in SUBURB_TEXT.split(","))
    if entry
]

KNOWN_PROPERTY_TYPES = [
    "House", "Apartment", "Unit", "Townhouse", "Studio", "Villa", "Duplex",
]

LISTING_COLUMNS = [
    "listing_id", "url", "scraped_at", "search_suburb", "search_postcode",
    "raw_html_path", "parse_warnings",
    "price_raw", "price_pw", "price_min_pw", "price_max_pw", "price_is_range",
    "price_period_detected",
    "address_full", "address_line1", "address_line2", "suburb", "postcode",
    "state", "latitude", "longitude",
    "property_type", "property_type_raw", "bedrooms", "bathrooms", "parking",
    "land_size", "internal_area",
    "description_headline", "description_text", "additional_features",
    "available_from_raw", "available_from_date", "bond_raw", "bond_amount",
    "inspection_times_raw",
    "agency_name", "agent_names", "num_photos", "has_floorplan",
]

LISTING_HREF_RE = re.compile(r"-(\d+)/?$")
PRICE_RANGE_RE = re.compile(r"\$\s?([\d,]+(?:\.\d+)?)\s*-\s*\$?\s?([\d,]+(?:\.\d+)?)")
PRICE_SINGLE_RE = re.compile(r"\$\s?([\d,]+(?:\.\d+)?)")
PERIOD_WEEK_RE = re.compile(r"per\s*week|\bpw\b|p\.w\.", re.I)
PERIOD_MONTH_RE = re.compile(r"per\s*calendar\s*month|per\s*month|\bpcm\b", re.I)
BOND_RE = re.compile(r"bond[^\d$]*\$?\s?([\d,]+(?:\.\d+)?)", re.I)
ADDR_RE = re.compile(r"^(.*?),\s*([A-Za-z .'-]+)\s+VIC\s+(\d{4})$", re.I)
LAT_LNG_RE = re.compile(r"center=(-?\d+\.\d+),(-?\d+\.\d+)")


def osa(script):
    return subprocess.run(
        ["osascript", "-e", script], capture_output=True, text=True, check=True,
    ).stdout.rstrip("\n")


def fetch(url):
    """Navigate the shared Chrome window and return rendered HTML, or None.
    Domain is a client-rendered React app, so readyState fires before the
    listing content has hydrated -- hence the settle wait after it."""
    safe_url = url.replace("\\", "\\\\").replace('"', '\\"')
    try:
        osa(f'tell application "Google Chrome" to set URL of active tab of front window to "{safe_url}"')
    except subprocess.CalledProcessError as e:
        print(f"  fetch failed for {url}: {e.stderr.strip()}")
        return None

    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            state = osa(
                'tell application "Google Chrome" to execute active tab of '
                'front window javascript "document.readyState"'
            )
        except subprocess.CalledProcessError:
            state = ""
        if state.strip() == "complete":
            break
        time.sleep(0.5)
    time.sleep(3)
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    try:
        return osa(
            'tell application "Google Chrome" to execute active tab of '
            'front window javascript "document.documentElement.outerHTML"'
        )
    except subprocess.CalledProcessError as e:
        print(f"  fetch failed for {url}: {e.stderr.strip()}")
        return None


def text_of(soup, testid):
    el = soup.find(attrs={"data-testid": testid})
    return el.get_text(" ", strip=True) if el else None


def find_listing_root(data, listing_id):
    """Locate the JSON node for this specific listing by matching its id. The
    page also embeds a listingsMap of nearby listings, so fields must be read
    from this scoped node, never via an unscoped recursive search."""
    stack = [data]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            for key in ("id", "listingId", "adId"):
                if key in node and str(node[key]) == str(listing_id):
                    return node
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return None


suburb_count = input(f"How many suburbs to scrape? [default: all {len(SUBURBS)}]: ").strip()
max_pages = input(f"Max search pages per suburb? [default: {MAX_PAGES_PER_SUBURB}]: ").strip()
listing_cap = input("Max total listings to scrape details for? [default: no limit]: ").strip()

SUBURBS = SUBURBS[:int(suburb_count)] if suburb_count else SUBURBS
MAX_PAGES_PER_SUBURB = int(max_pages) if max_pages else MAX_PAGES_PER_SUBURB
MAX_LISTINGS = int(listing_cap) if listing_cap else None

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
subprocess.run(["open", "-a", "Google Chrome"], check=True)
time.sleep(2)
osa('tell application "Google Chrome" to make new window')
time.sleep(1)


# ---------------------------------------------------------------------------
# Phase 1 -- walk the search pages of every suburb, collect listing URLs
# ---------------------------------------------------------------------------

listings = {}

for name, postcode in SUBURBS:
    print(f"Suburb: {name} ({postcode})")
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    found = {}
    previous_ids = set()

    for page in range(1, MAX_PAGES_PER_SUBURB + 1):
        url = f"{BASE}/rent/{slug}-vic-{postcode}/"
        if page > 1:
            url += f"?page={page}"
        html = fetch(url)
        if html is None:
            break

        soup = BeautifulSoup(html, "html.parser")
        page_links = {}
        for address_el in soup.find_all(attrs={"data-testid": "address-line1"}):
            anchor = address_el.find_parent("a")
            if anchor is None:
                continue
            href = anchor.get("href", "")
            if href.startswith("/"):
                href = BASE + href
            match = LISTING_HREF_RE.search(href.split("?")[0])
            if match:
                page_links[match.group(1)] = href

        if not page_links or set(page_links) == previous_ids:
            break
        previous_ids = set(page_links)
        found.update(page_links)
        print(f"  {name} ({postcode}) page {page}: {len(found)} listings so far")

    for listing_id, href in found.items():
        listings.setdefault(listing_id, (href, name, postcode))

listings = dict(list(listings.items())[:MAX_LISTINGS]) if MAX_LISTINGS else listings
print(f"\n{len(listings)} unique listings to scrape\n")


# ---------------------------------------------------------------------------
# Phase 2 -- fetch each detail page and parse it (JSON first, DOM fallback)
# ---------------------------------------------------------------------------

rows = []

for i, (listing_id, (url, search_suburb, search_postcode)) in enumerate(listings.items(), 1):
    html = fetch(url)
    if html is None:
        print(f"[{i}/{len(listings)}] failed to fetch {listing_id}, skipping")
        continue

    warnings = []
    soup = BeautifulSoup(html, "html.parser")

    next_data = None
    script_tag = soup.find("script", id="__NEXT_DATA__")
    if script_tag and script_tag.string:
        try:
            next_data = json.loads(script_tag.string)
        except json.JSONDecodeError:
            next_data = None

    root = {}
    if next_data is None:
        warnings.append("__NEXT_DATA__ not found, using DOM fallback for all fields")
    else:
        root = find_listing_root(next_data, listing_id)
        if root is None:
            warnings.append("__NEXT_DATA__ present but listing root not matched by id")
            root = {}
    gql = (root.get("rootGraphQuery") or {}).get("listingByIdV2") or {}

    # --- price ---
    price_details = gql.get("priceDetails") if isinstance(gql.get("priceDetails"), dict) else {}
    price_raw = price_details.get("displayPrice")
    if not price_raw:
        price_raw = (root.get("listingsMap") or {}).get(str(listing_id), {}).get("listingModel", {}).get("price")
    if not price_raw:
        price_raw = text_of(soup, "listing-details__listing-summary-title-name")
    if not price_raw:
        warnings.append("price not found in JSON or DOM")

    price_pw = price_min_pw = price_max_pw = None
    price_is_range = False
    period = "unknown"

    if not price_raw:
        warnings.append("price_raw missing")
    elif any(k in price_raw.lower() for k in ("contact agent", "application approved", "under application")):
        warnings.append(f"unparseable price text: {price_raw.strip()!r}")
    else:
        price_text = price_raw.strip()
        price_part = re.split(r"\bbond\b", price_text, flags=re.I)[0]
        if PERIOD_MONTH_RE.search(price_text):
            period = "monthly"
        elif PERIOD_WEEK_RE.search(price_text):
            period = "weekly"
        factor = 12 / 52 if period == "monthly" else 1.0

        range_match = PRICE_RANGE_RE.search(price_part)
        single_match = PRICE_SINGLE_RE.search(price_part)
        if range_match:
            low = float(range_match.group(1).replace(",", ""))
            high = float(range_match.group(2).replace(",", ""))
            price_min_pw = round(low * factor, 2)
            price_max_pw = round(high * factor, 2)
            price_pw = round((low + high) / 2 * factor, 2)
            price_is_range = True
        elif single_match and period != "unknown":
            price_pw = round(float(single_match.group(1).replace(",", "")) * factor, 2)
        elif single_match:
            warnings.append(f"price found but billing period unclear, left null: {price_text!r}")
        else:
            warnings.append(f"unparseable price text: {price_text!r}")

    # --- address ---
    address_full = root.get("address")
    suburb = root.get("suburb")
    postcode = str(root["postcode"]) if root.get("postcode") is not None else None
    state = (root.get("stateAbbreviation") or "").upper() or None
    unit_number, street_number, street = root.get("unitNumber"), root.get("streetNumber"), root.get("street")

    address_line1 = None
    if street_number or street:
        prefix = f"{unit_number}/" if unit_number else ""
        address_line1 = f"{prefix}{street_number} {street}".strip()
    address_line2 = f"{suburb} {state} {postcode}" if suburb and state and postcode else None

    if not address_full:
        h1 = soup.find("h1")
        address_full = h1.get_text(" ", strip=True) if h1 else None
    if not address_full:
        warnings.append("address not found in JSON or DOM")

    if address_line1 is None and address_full:
        address_match = ADDR_RE.search(address_full.strip())
        if address_match:
            address_line1 = address_match.group(1).strip()
            address_line2 = address_line2 or f"{address_match.group(2).strip()} VIC {address_match.group(3)}"
            suburb = suburb or address_match.group(2).strip()
            postcode = postcode or address_match.group(3)
            state = state or "VIC"
        else:
            address_line1 = address_full

    latitude = longitude = None
    static_map = gql.get("staticMapUrl")
    if static_map:
        coords = LAT_LNG_RE.search(static_map)
        if coords:
            latitude, longitude = float(coords.group(1)), float(coords.group(2))
    if latitude is None:
        warnings.append("latitude/longitude not found in JSON or DOM")

    # --- beds / baths / parking: read by label, since a zero count is
    #     omitted from the DOM entirely rather than rendered as "0" ---
    bedrooms = root.get("beds")
    bathrooms = gql.get("bathrooms")
    parking = gql.get("carspaces")
    if bedrooms is None and bathrooms is None and parking is None:
        wrapper = soup.find(attrs={"data-testid": "property-features-wrapper"})
        for feature in wrapper.find_all(attrs={"data-testid": "property-features-feature"}) if wrapper else []:
            feature_match = re.match(r"(\d+)\s*(Bed|Bath|Parking|Car)", feature.get_text(" ", strip=True), re.I)
            if not feature_match:
                continue
            count, label = int(feature_match.group(1)), feature_match.group(2).lower()
            if label.startswith("bed"):
                bedrooms = count
            elif label.startswith("bath"):
                bathrooms = count
            else:
                parking = count

    # --- property type ---
    property_type_raw = root.get("propertyType") or text_of(soup, "listing-summary-property-type")
    property_type = None
    if property_type_raw:
        property_type = next(
            (t for t in KNOWN_PROPERTY_TYPES if t.lower() in property_type_raw.lower()), "other"
        )

    # --- description ---
    description_headline = root.get("headline")
    description = root.get("description")
    description_text = "\n".join(description) if isinstance(description, list) else description
    if not description_text:
        headline_el = soup.find(attrs={"data-testid": "listing-details__description-headline"})
        if headline_el is None:
            description_headline = description_text = None
        else:
            description_headline = headline_el.get_text(" ", strip=True)
            description_text = None
            parent = headline_el.find_parent()
            if parent:
                for br in parent.find_all("br"):
                    br.replace_with("\n")
                description_text = parent.get_text("", strip=True)
    if not description_headline and not description_text:
        warnings.append("description not found in JSON or DOM")

    # --- additional features ---
    additional_features = root.get("features")
    if not (isinstance(additional_features, list) and additional_features):
        container = soup.find(attrs={"data-testid": "listing-details__additional-features-listing"})
        additional_features = [li.get_text(" ", strip=True) for li in container.find_all("li")] if container else []

    # --- tenancy ---
    available_from_raw = available_from_date = None
    date_available = gql.get("dateAvailableV2")
    if isinstance(date_available, dict) and date_available.get("isoDate"):
        available_from_raw = date_available["isoDate"]
        try:
            available_from_date = datetime.fromisoformat(available_from_raw).date().isoformat()
        except ValueError:
            warnings.append(f"available_from unparseable: {available_from_raw!r}")
    else:
        warnings.append("available_from not found in JSON or DOM")

    # bond is a raw number in JSON, or text inside the price string on fallback
    bond = price_details.get("bond")
    bond_raw = str(bond) if bond is not None else None
    bond_amount = float(bond) if isinstance(bond, (int, float)) else None
    if bond_amount is None and price_raw:
        bond_match = BOND_RE.search(str(price_raw))
        if bond_match:
            bond_amount = float(bond_match.group(1).replace(",", ""))
            bond_raw = price_raw

    inspection_times_raw = None
    inspections = (gql.get("inspectionDetails") or {}).get("inspections")
    if not inspections:
        inspections = (root.get("inspection") or {}).get("inspectionTimes")
    if isinstance(inspections, list) and inspections:
        parts = []
        for inspection in inspections:
            opening = (inspection.get("openingDateTime") or {}).get("isoDate", "")
            closing = (inspection.get("closingDateTime") or {}).get("isoDate", "")
            parts.append(f"{opening} - {closing}" if opening or closing else str(inspection))
        inspection_times_raw = " | ".join(parts)
    if inspection_times_raw is None:
        block = soup.find(attrs={"data-testid": "listing-details__inspections-block-container"})
        parts = []
        for day_el in block.find_all(attrs={"data-testid": "listing-details__inspections-block-day"}) if block else []:
            time_el = day_el.find_next(attrs={"data-testid": "listing-details__inspections-block-time"})
            day_text = day_el.get_text(" ", strip=True)
            parts.append(f"{day_text} {time_el.get_text(' ', strip=True) if time_el else ''}".strip())
        inspection_times_raw = " | ".join(parts) if parts else None

    # --- agency, photos, floorplan ---
    agency_name = root.get("agencyName") or text_of(soup, "listing-details__agent-details-agency-name")
    agents = root.get("agents")
    agent_names = None
    if isinstance(agents, list) and agents:
        agent_names = " | ".join(a.get("name", "") for a in agents if isinstance(a, dict))
    if not agent_names:
        agent_names = text_of(soup, "listing-details__agent-details-agent-name")

    photos = (root.get("galleryV2") or {}).get("photos")
    num_photos = len(photos) if isinstance(photos, list) else None

    has_floorplan = None
    media = gql.get("largeMedia")
    if isinstance(media, list):
        has_floorplan = any(isinstance(m, dict) and m.get("type") == "floorplan" for m in media)
    if has_floorplan is None:
        has_floorplan = False
        for el in soup.find_all(attrs={"data-testid": True}):
            testid = el.get("data-testid", "")
            if testid.startswith("listing-details__toolbar-icon floorplan"):
                has_floorplan = "disabled" not in testid
                break

    rows.append({
        "listing_id": listing_id, "url": url,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "search_suburb": search_suburb, "search_postcode": search_postcode,
        "raw_html_path": None, "parse_warnings": " | ".join(warnings),
        "price_raw": price_raw, "price_pw": price_pw,
        "price_min_pw": price_min_pw, "price_max_pw": price_max_pw,
        "price_is_range": price_is_range, "price_period_detected": period,
        "address_full": address_full, "address_line1": address_line1,
        "address_line2": address_line2, "suburb": suburb, "postcode": postcode,
        "state": state, "latitude": latitude, "longitude": longitude,
        "property_type": property_type, "property_type_raw": property_type_raw,
        "bedrooms": bedrooms, "bathrooms": bathrooms, "parking": parking,
        "land_size": gql.get("landAreaSqm"), "internal_area": gql.get("buildingArea"),
        "description_headline": description_headline, "description_text": description_text,
        "additional_features": " | ".join(additional_features) if additional_features else None,
        "available_from_raw": available_from_raw, "available_from_date": available_from_date,
        "bond_raw": bond_raw, "bond_amount": bond_amount,
        "inspection_times_raw": inspection_times_raw,
        "agency_name": agency_name, "agent_names": agent_names,
        "num_photos": num_photos, "has_floorplan": bool(has_floorplan),
    })
    print(f"[{i}/{len(listings)}] parsed {listing_id} (warnings: {rows[-1]['parse_warnings'] or 'none'})")

    if i % 20 == 0:
        pd.DataFrame(rows, columns=LISTING_COLUMNS).to_parquet(OUT_PATH, index=False)

pd.DataFrame(rows, columns=LISTING_COLUMNS).to_parquet(OUT_PATH, index=False)
print(f"\nDone: {len(rows)} listings written to {OUT_PATH}")