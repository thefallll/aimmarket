from urllib.parse import quote
from core.items_manager import ItemsManager

WEAPON_TYPE_MAP = {
    # Rifles
    "AK-47": "Rifle", "M4A4": "Rifle", "M4A1-S": "Rifle", "FAMAS": "Rifle", "Galil AR": "Rifle", "AUG": "Rifle", "SG 553": "Rifle",
    # SMG
    "P90": "SMG", "UMP-45": "SMG", "MP7": "SMG", "MP5-SD": "SMG", "MP9": "SMG", "MAC-10": "SMG", "PP-Bizon": "SMG",
    # Sniper Rifles
    "AWP": "Sniper Rifle", "SSG 08": "Sniper Rifle", "SCAR-20": "Sniper Rifle", "G3SG1": "Sniper Rifle",
    # Pistols
    "Glock-18": "Pistol", "USP-S": "Pistol", "P2000": "Pistol", "P250": "Pistol", "Five-SeveN": "Pistol", "Tec-9": "Pistol", "CZ75-Auto": "Pistol", "Dual Berettas": "Pistol", "Desert Eagle": "Pistol", "R8 Revolver": "Pistol",
    # Shotguns
    "Nova": "Shotgun", "XM1014": "Shotgun", "MAG-7": "Shotgun", "Sawed-Off": "Shotgun",
    # Heavy (Machineguns)
    "M249": "Machinegun", "Negev": "Machinegun",
    # Grenades
    "HE Grenade": "Grenade", "Flashbang": "Grenade", "Smoke Grenade": "Grenade", "Decoy Grenade": "Grenade", "Molotov": "Grenade", "Incendiary Grenade": "Grenade",
    # Knives
    "★": "Knife",
    "Bayonet": "Knife", "Bowie Knife": "Knife", "Butterfly Knife": "Knife", "Classic Knife": "Knife", "Falchion Knife": "Knife",
    "Flip Knife": "Knife", "Gut Knife": "Knife", "Huntsman Knife": "Knife", "Karambit": "Knife", "M9 Bayonet": "Knife",
    "Navaja Knife": "Knife", "Nomad Knife": "Knife", "Paracord Knife": "Knife", "Shadow Daggers": "Knife", "Skeleton Knife": "Knife",
    "Stiletto Knife": "Knife", "Survival Knife": "Knife", "Talon Knife": "Knife", "Ursus Knife": "Knife", "Stock Knife": "Knife",
    # Gloves
    "Gloves": "Gloves", "Hydra Gloves": "Gloves", "Sport Gloves": "Gloves", "Moto Gloves": "Gloves", "Specialist Gloves": "Gloves",
    "Hand Wraps": "Gloves", "Driver Gloves": "Gloves", "Bloodhound Gloves": "Gloves",
    # Cases
    "Case": "Case", "Fever Case": "Case", "Snakebite Case": "Case", "Recoil Case": "Case", "Fracture Case": "Case", "Clutch Case": "Case",
    "Prisma Case": "Case", "Prisma 2 Case": "Case", "Danger Zone Case": "Case", "Horizon Case": "Case", "Spectrum Case": "Case", "Spectrum 2 Case": "Case",
    "Glove Case": "Case", "Chroma Case": "Case", "Chroma 2 Case": "Case", "Chroma 3 Case": "Case", "Gamma Case": "Case", "Gamma 2 Case": "Case",
    "Operation Broken Fang Case": "Case", "Operation Riptide Case": "Case", "Operation Shattered Web Case": "Case", "Operation Hydra Case": "Case",
    # Stickers
    "Sticker": "Sticker",
    # Agents
    "Agent": "Agent",
    # Patches
    "Patch": "Patch",
    # Graffiti
    "Graffiti": "Graffiti",
    # Music Kits
    "Music Kit": "Music Kit",
    # Other (fallbacks)
    "Souvenir Package": "Package", "Capsule": "Capsule", "Pin": "Pin", "Collectible": "Collectible"
}

class Links:
    def __init__(self, items_manager: ItemsManager):
        self.items_manager = items_manager

    def extract_weapon_and_type(self, hash_name):
        name = hash_name
        if name.startswith("Souvenir "):
            name = name[len("Souvenir "):]
        if name.startswith("StatTrak™ "):
            name = name[len("StatTrak™ "):]
        for weapon, weapon_type in WEAPON_TYPE_MAP.items():
            if name.startswith("★"):
                if weapon in name:
                    return weapon_type, weapon
            else:
                if name.startswith(weapon):
                    return weapon_type, weapon
        return None, None

    def make_aimmarket_link(self, hash_name: str, item_id: str = None) -> str:
        encoded_name = quote(hash_name)
        if item_id:
            return f"https://aim.market/en/buy/csgo/{encoded_name}?id={item_id}"
        else:
            return f"https://aim.market/en/buy/csgo/{encoded_name}"

    def make_csmarket_link(self, hash_name):
            is_souvenir = hash_name.startswith("Souvenir ")
            weapon_type, weapon_name = self.extract_weapon_and_type(hash_name)
            if weapon_type and weapon_name:
                encoded_type = quote(weapon_type)
                encoded_name = quote(weapon_name)
                encoded_hash = quote(hash_name)
                return f"https://market.csgo.com/ru/{encoded_type}/{encoded_name}/{encoded_hash}"
            else:
                encoded_hash = quote(hash_name)
                return f"https://market.csgo.com/ru/search?query={encoded_hash}"

    def make_buff_link(self, hash_name):
        good_id = self.items_manager.items.get(hash_name, {}).get('buff', {}).get('good_id')
        if good_id:
            return f"https://buff.163.com/goods/{good_id}"
        else:
            encoded_name = quote(hash_name)
            return f"https://buff.163.com/market/csgo#search={encoded_name}"