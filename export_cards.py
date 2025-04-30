import asyncio
import os
import sys
from pathlib import Path

# Check for required packages
try:
    from PIL import Image
    from tortoise import Tortoise
except ImportError:
    print("Required packages not found. Please install Pillow and Tortoise-ORM:")
    print("  pip install pillow tortoise-orm")
    sys.exit(1)

# Setup paths
MEDIA_PATH = Path("./admin_panel/media")
OUTPUT_DIR = Path("./exported_cards")

# Make sure output directories exist
OUTPUT_DIR.mkdir(exist_ok=True)
for subdir in ["normal", "special", "regimes", "balls", "economy_icons"]:
    (OUTPUT_DIR / subdir).mkdir(exist_ok=True)

# Database config
DB_CONFIG = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.asyncpg",
            "credentials": {
                "database": "ballsdex",
                "host": "localhost",  # Change if needed
                "password": "defaultballsdexpassword",  # Change if needed
                "port": 5432,
                "user": "ballsdex",  # Change if needed
            }
        }
    },
    "apps": {
        "models": {
            "models": ["ballsdex.core.models"],
            "default_connection": "default",
        }
    }
}

async def export_raw_assets():
    """Export all raw assets (backgrounds, ball images, icons)"""
    from ballsdex.core.models import Ball, Economy, Regime, Special
    
    print("Exporting raw assets...")
    
    # Export regime backgrounds
    regimes = await Regime.all()
    print(f"Found {len(regimes)} regimes")
    for regime in regimes:
        try:
            if not regime.background:
                continue
                
            image_path = MEDIA_PATH / regime.background.lstrip('/')
            if not image_path.exists():
                print(f"Warning: File not found: {image_path}")
                continue
                
            img = Image.open(image_path)
            output_path = OUTPUT_DIR / "regimes" / f"{regime.name}.webp"
            img.save(output_path, format="WEBP")
            print(f"Exported regime: {regime.name}")
        except Exception as e:
            print(f"Error exporting regime {regime.name}: {e}")
    
    # Export economy icons
    economies = await Economy.all()
    print(f"Found {len(economies)} economies")
    for economy in economies:
        try:
            if not economy.icon:
                continue
                
            image_path = MEDIA_PATH / economy.icon.lstrip('/')
            if not image_path.exists():
                print(f"Warning: File not found: {image_path}")
                continue
                
            img = Image.open(image_path)
            output_path = OUTPUT_DIR / "economy_icons" / f"{economy.name}.webp"
            img.save(output_path, format="WEBP")
            print(f"Exported economy: {economy.name}")
        except Exception as e:
            print(f"Error exporting economy {economy.name}: {e}")
    
    # Export ball images
    balls = await Ball.all()
    print(f"Found {len(balls)} balls")
    for ball in balls:
        try:
            # Export collection card
            if ball.collection_card:
                image_path = MEDIA_PATH / ball.collection_card.lstrip('/')
                if image_path.exists():
                    img = Image.open(image_path)
                    output_path = OUTPUT_DIR / "balls" / f"{ball.country}_collection.webp"
                    img.save(output_path, format="WEBP")
            
            # Export wild card
            if ball.wild_card and ball.wild_card != "/default.png":
                image_path = MEDIA_PATH / ball.wild_card.lstrip('/')
                if image_path.exists():
                    img = Image.open(image_path)
                    output_path = OUTPUT_DIR / "balls" / f"{ball.country}_wild.webp" 
                    img.save(output_path, format="WEBP")
            
            print(f"Exported ball: {ball.country}")
        except Exception as e:
            print(f"Error exporting ball {ball.country}: {e}")
    
    # Export special backgrounds
    specials = await Special.all()
    print(f"Found {len(specials)} special events")
    for special in specials:
        try:
            if not special.background:
                continue
                
            image_path = MEDIA_PATH / special.background.lstrip('/')
            if not image_path.exists():
                print(f"Warning: File not found: {image_path}")
                continue
                
            img = Image.open(image_path)
            output_path = OUTPUT_DIR / "special" / f"{special.name}.webp"
            img.save(output_path, format="WEBP")
            print(f"Exported special: {special.name}")
        except Exception as e:
            print(f"Error exporting special {special.name}: {e}")

async def generate_cards():
    """Generate actual cards with all variations"""
    from ballsdex.core.models import Ball, BallInstance, Special
    from ballsdex.core.image_generator.image_gen import draw_card
    
    print("\nGenerating card variations...")
    
    balls = await Ball.all()
    specials = await Special.all()
    
    for ball in balls:
        print(f"Generating cards for {ball.country}...")
        
        # Create a temporary ball instance
        instance = BallInstance(
            ball=ball,
            health_bonus=0,
            attack_bonus=0,
            special=None
        )
        
        # Basic card
        try:
            image, kwargs = draw_card(instance, media_path=str(MEDIA_PATH) + "/")
            output_path = OUTPUT_DIR / "normal" / f"{ball.country}_normal.webp"
            image.save(output_path, **kwargs)
            print(f"  - Generated normal card")
        except Exception as e:
            print(f"  - Error generating normal card: {e}")
        
        # Generate with specials
        for special in specials:
            if not special.background:
                continue
                
            try:
                instance.special = special
                image, kwargs = draw_card(instance, media_path=str(MEDIA_PATH) + "/")
                output_path = OUTPUT_DIR / "special" / f"{ball.country}_{special.name}.webp"
                image.save(output_path, **kwargs)
                print(f"  - Generated with special: {special.name}")
            except Exception as e:
                print(f"  - Error with special {special.name}: {e}")
        
        # Reset special
        instance.special = None
        
        # Generate stat variations
        for atk, hp, name in [
            (20, 20, "max_positive"),
            (-20, -20, "max_negative"),
            (10, -10, "mixed_1"),
            (-10, 10, "mixed_2")
        ]:
            try:
                instance.attack_bonus = atk
                instance.health_bonus = hp
                image, kwargs = draw_card(instance, media_path=str(MEDIA_PATH) + "/")
                output_path = OUTPUT_DIR / "normal" / f"{ball.country}_{name}.webp"
                image.save(output_path, **kwargs)
                print(f"  - Generated stat variation: {name}")
            except Exception as e:
                print(f"  - Error with variation {name}: {e}")

async def main():
    print("Initializing database connection...")
    
    # Get database URL from environment or use default config
    db_url = os.environ.get("BALLSDEXBOT_DB_URL")
    
    if db_url:
        # Use the provided URL
        await Tortoise.init(
            config={
                "connections": {"default": db_url},
                "apps": {
                    "models": {
                        "models": ["ballsdex.core.models"],
                        "default_connection": "default",
                    },
                },
            }
        )
    else:
        # Use the hardcoded config
        print("BALLSDEXBOT_DB_URL not set, using default config")
        await Tortoise.init(config=DB_CONFIG)
    
    try:
        # Export raw assets first
        await export_raw_assets()
        
        # Generate card variations
        await generate_cards()
        
        print(f"\nExport complete! All files saved to {OUTPUT_DIR}")
    
    except Exception as e:
        print(f"Error during export: {e}")
    
    finally:
        # Close database connection
        await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(main())