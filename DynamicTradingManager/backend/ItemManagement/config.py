import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from backend root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Get paths from environment variables with fallbacks
GAME_PATH_ENV = os.getenv("GAME_PATH")
DT_PATH_ENV = os.getenv("DYNAMIC_TRADING_PATH")

# Default Paths - use absolute parent path
# SCRIPT_DIR should now point to the project root
SCRIPT_DIR = Path(DT_PATH_ENV) if DT_PATH_ENV else Path(__file__).parent.parent.parent.parent

# VANILLA_DIR should point to the media/scripts directory
if GAME_PATH_ENV:
    VANILLA_DIR = os.path.join(GAME_PATH_ENV, "scripts")
else:
    # Fallback to hardcoded paths if env not set
    VANILLA_DIR = "/home/psychopatz/.steam/steamapps/common/ProjectZomboid/projectzomboid/media/scripts/"
    if not os.path.exists(VANILLA_DIR):
        VANILLA_DIR = "/home/psychopatz/.steam/steam/steamapps/common/ProjectZomboid/projectzomboid/media/scripts/"

VANILLA_SCRIPTS_DIR = os.path.join(VANILLA_DIR, "generated/items/")

# Distribution files for spawn rate analysis
_DISTRIB_BASE = VANILLA_DIR.replace("/scripts/", "/lua/server/")
DISTRIBUTIONS_DIR = os.path.join(_DISTRIB_BASE, "Items/")

MOD_ITEMS_DIR = str(SCRIPT_DIR / "Contents/mods/DynamicTradingCommon/42.13/media/lua/shared/DT/Common/Items")
OUTPUT_DIR = str(SCRIPT_DIR / "Scripts/Output")

# Exclusion patterns for item registration
EXCLUDED_PATTERNS = [
    r'^Corpse',           # Zombie corpses
    r'^CraftedElectronic', # Crafted items
    r'^Crafted',
    r'^Radio',            # Radio transmissions
    r'^Move_',            # Moveable furniture
    r'^farming',          # Farming-specific
    r'^Hydrocraft',       # Mod items
]

# Category to file mapping
CATEGORY_FILE_MAP = {
    'Food': {
        'Meat': 'Food/DT_Meat.lua',
        'Fruit': 'Food/DT_Fruit.lua',
        'Vegetable': 'Food/DT_Vegetable.lua',
        'Alcohol': 'Food/DT_Alcohol.lua',
        'Drink': 'Food/DT_Drink.lua',
        'Canned': 'Food/DT_Canned.lua',
        'Grain': 'Food/DT_Grain.lua',
        'Sweets': 'Food/DT_Sweets.lua',
        'Spice': 'Food/DT_Spice.lua',
        'Cooking': 'Food/DT_Cooking.lua',
        'Perishable': 'Food/DT_General.lua',
        'NonPerishable': 'Food/DT_General.lua',
        'General': 'Food/DT_General.lua',
    },
    'Literature': {
        'SkillBook': 'Literature/DT_SkillBook.lua',
        'Recipe': 'Literature/DT_Recipe.lua',
        'Media': 'Literature/DT_Media.lua',
        'Cards': 'Literature/DT_Cards.lua',
        'Book': 'Literature/DT_Book.lua',
    },
    'Weapon': {
        'Explosive': 'Weapon/DT_Explosive.lua',
        'Ranged.Firearm': 'Weapon/DT_Ranged.lua',
        'Ranged.Ammo': 'Weapon/DT_Ammo.lua',
        'Ranged': 'Weapon/DT_Ranged.lua',
        'Melee.Axe': 'Weapon/DT_Axe.lua',
        'Melee.Blade': 'Weapon/DT_Blade.lua',
        'Melee.Blunt': 'Weapon/DT_Blunt.lua',
        'Melee.General': 'Weapon/DT_Melee.lua',
        'Melee': 'Weapon/DT_Melee.lua',
        'Part.Ammo': 'Weapon/DT_Part_Ammo.lua',
        'Part.Accessory': 'Weapon/DT_Part.lua',
        'Part': 'Weapon/DT_Part.lua',
    },
    'Clothing': {
        'Armor': 'Clothing/DT_Armor.lua',
        'Head': 'Clothing/DT_Head.lua',
        'Face': 'Clothing/DT_Face.lua',
        'Top': 'Clothing/DT_Top.lua',
        'Outerwear': 'Clothing/DT_Outerwear.lua',
        'Bottom': 'Clothing/DT_Bottom.lua',
        'Underwear': 'Clothing/DT_Underwear.lua',
        'Dress': 'Clothing/DT_Dress.lua',
        'FullBody': 'Clothing/DT_FullBody.lua',
        'Hands': 'Clothing/DT_Hands.lua',
        'Feet': 'Clothing/DT_Feet.lua',
        'Accessory.Jewelry': 'Clothing/DT_Jewelry.lua',
        'Accessory.Eyes': 'Clothing/DT_Eyewear.lua',
        'Accessory.Wrist': 'Clothing/DT_Accessory.lua',
        'Accessory.Neck': 'Clothing/DT_Accessory.lua',
        'Accessory.Utility': 'Clothing/DT_Accessory.lua',
        'Accessory.Cosmetic': 'Clothing/DT_Accessory.lua',
        'Accessory': 'Clothing/DT_Accessory.lua',
        'General': 'Clothing/DT_General.lua',
    },
    'Medical': {
        'General.Drug': 'Medical/DT_Drugs.lua',
        'General.Pills': 'Medical/DT_Pills.lua',
        'General.Vitamin': 'Medical/DT_Vitamin.lua',
        'General.Clinical': 'Medical/DT_Clinical.lua',
        'General.Poison': 'Medical/DT_Poison.lua',
        'Healthcare.Botanical': 'Medical/DT_Botanical.lua',
        'Surgical': 'Medical/DT_Surgical.lua',
        'Healthcare': 'Medical/DT_Healthcare.lua',
        'General': 'Medical/DT_General.lua',
    },
    'Container': {
        'Bag.Backpack': 'Container/DT_Backpack.lua',
        'Bag.Duffel': 'Container/DT_Duffel.lua',
        'Bag.Satchel': 'Container/DT_Satchel.lua',
        'Bag.Fanny': 'Container/DT_Fanny.lua',
        'Bag.Handbag': 'Container/DT_Handbag.lua',
        'Bag.Cooler': 'Container/DT_Cooler.lua',
        'Bag.Sack': 'Container/DT_Sack.lua',
        'Bag.Rig': 'Container/DT_Wearable.lua',
        'Bag.Bandolier': 'Container/DT_Wearable.lua',
        'Bag.Holster': 'Container/DT_Wearable.lua',
        'Bag.General': 'Container/DT_Bag.lua',
        'Bag': 'Container/DT_Bag.lua',
        'Liquid': 'Container/DT_Liquid.lua',
        'Stash': 'Container/DT_Stash.lua',
        'Utility': 'Container/DT_Utility.lua',
        'Backpack': 'Container/DT_Backpack.lua',
        'Accessory': 'Container/DT_Wearable.lua',
        'General': 'Container/DT_Organizer.lua',
    },
    'Tool': {
        'Medical.Surgical': 'Tool/DT_Medical_Surgical.lua',
        'Medical': 'Tool/DT_Medical.lua',
        'Cookware': 'Tool/DT_Cookware.lua',
        'Crafting': 'Tool/DT_Crafting.lua',
        'Farming': 'Tool/DT_Farming.lua',
        'Fishing': 'Tool/DT_Fishing.lua',
        'General': 'Tool/DT_General.lua',
    },
    'Resource': {
        'Fishing': 'Resource/DT_Fishing.lua',
        'Fuel.Liquid': 'Resource/DT_Fuel.lua',
        'Fuel.Gas': 'Resource/DT_Fuel.lua',
        'Fuel.Solid': 'Resource/DT_Fuel.lua',
        'Fuel': 'Resource/DT_Fuel.lua',
        'Material.Adhesive': 'Resource/DT_Adhesive.lua',
        'Material.Ammo': 'Resource/DT_AmmoMaterial.lua',
        'Material.Ceramic': 'Resource/DT_Ceramic.lua',
        'Material.Chemical': 'Resource/DT_Chemical.lua',
        'Material.Glass': 'Resource/DT_Glass.lua',
        'Material.Hardware': 'Resource/DT_Hardware.lua',
        'Material.Leather': 'Resource/DT_Leather.lua',
        'Material.Metal': 'Resource/DT_Metal.lua',
        'Material.Mineral': 'Resource/DT_Mineral.lua',
        'Material.Packaging': 'Resource/DT_Packaging.lua',
        'Material.Paper': 'Resource/DT_Paper.lua',
        'Material.Textile': 'Resource/DT_Textile.lua',
        'Material.Wood': 'Resource/DT_Wood.lua',
        'Material.General': 'Resource/DT_Material.lua',
        'Material': 'Resource/DT_Material.lua',
        'Parts': 'Resource/DT_Parts.lua',
    },
    'Electronics': {
        'Battery': 'Electronics/DT_Battery.lua',
        'Generator': 'Electronics/DT_Generator.lua',
        'Light.Flashlight': 'Electronics/DT_Flashlight.lua',
        'Light.Lantern': 'Electronics/DT_Lantern.lua',
        'Light.Component': 'Electronics/DT_Lighting.lua',
        'Gadget.Audio': 'Electronics/DT_Audio.lua',
        'Gadget.Communication': 'Electronics/DT_Communication.lua',
        'Gadget.Control': 'Electronics/DT_Control.lua',
        'Gadget.General': 'Electronics/DT_Gadget.lua',
        'Radio.Broadcast': 'Electronics/DT_Radio.lua',
        'Radio.TwoWay.Walkie': 'Electronics/DT_Walkie.lua',
        'Radio.TwoWay.Ham': 'Electronics/DT_HamRadio.lua',
        'Radio.TwoWay.Portable': 'Electronics/DT_FieldRadio.lua',
        'Television': 'Electronics/DT_Television.lua',
        'Gadget': 'Electronics/DT_Gadget.lua',
        'General': 'Electronics/DT_General.lua',
    },
    'Building': {
        'Moveable':   'Building/DT_Moveable.lua',
        'Material':   'Building/DT_Material.lua',
        'Furniture':  'Building/DT_Furniture.lua',
        'Fixture':    'Building/DT_Fixture.lua',
        'Vehicle':    'Building/DT_Vehicle.lua',
        'Garden':     'Building/DT_Garden.lua',
        'Survival':   'Building/DT_Survival.lua',
    },
    'Misc': {
        'General': 'Misc/DT_General.lua',
    },
}
