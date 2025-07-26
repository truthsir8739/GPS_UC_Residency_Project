import time
from residency.navigation import EnhancedRealWorldGPS
import re
import logging

logging.basicConfig(level=logging.INFO, filename='gps.log', format='%(asctime)s - %(levelname)s - %(message)s')

def is_valid_address(address):
    """Basic validation for address format: street, city, state, optional ZIP code."""
    pattern = r"^\d+\s+[\w\s]+,\s*[\w\s]+,\s*[A-Z]{2}(?:\s+\d{5})?$"
    return bool(re.match(pattern, address.strip()))

def run_navigation_test():
    print("\n🚗 Welcome to GPS Navigation System v1.0")
    print("🌍 Plan a route around the University of Kentucky campus")
    print("============================================================\n")
    
    gps = EnhancedRealWorldGPS()
    print("📍 Initializing map for University of Kentucky campus...")
    try:
        gps.load_area_by_name("University of Kentucky, Lexington, KY")
        if not gps.node_coords or len(gps.node_coords) < 10:
            raise Exception("Not enough road data")
        print(f"✅ Map loaded with {len(gps.node_coords)} waypoints")
    except Exception as e:
        print(f"❌ Failed to load map: {e}")
        logging.error(f"Failed to load map: {str(e)}")
        print("🔄 Falling back to default coordinates...")
        gps.load_area_by_coordinates(38.0307, -84.5041, distance_km=1.0)
        if not gps.node_coords:
            print("❌ Unable to load map data. Please check your internet connection and try again.")
            return
    
    print(f"\n📍 AREA OVERVIEW:")
    print(f"   🏛️ Location: {gps.area_name}")
    print(f"   🛣️ Waypoints: {len(gps.node_coords)}")
    print(f"   🔗 Road segments: {sum(len(edges) for edges in gps.adj_list.values())//2}")
    print(f"   🏢 Landmarks: {len(gps.landmarks)}")
    
    while True:
        input_type = input("\n📥 Choose input method: (1) Coordinates or (2) Addresses? [1/2]: ").strip()
        if input_type in ['1', '2']:
            break
        print("❌ Invalid choice. Please enter '1' for coordinates or '2' for addresses.")
    
    learner_mode = input("🎓 Enable Learner Mode for safer routes? [y/n]: ").strip().lower() == 'y'
    mode_desc = "safer route with tips" if learner_mode else "fastest route"
    print(f"🚦 Mode selected: {'Learner' if learner_mode else 'Normal'} ({mode_desc})")
    
    if input_type == '1':
        while True:
            try:
                start_lat = float(input("🚩 Enter start latitude (e.g., 38.0382): "))
                start_lon = float(input("🚩 Enter start longitude (e.g., -84.4992): "))
                end_lat = float(input("🏁 Enter end latitude (e.g., 38.0249): "))
                end_lon = float(input("🏁 Enter end longitude (e.g., -84.5074): "))
                break
            except ValueError:
                print("❌ Invalid coordinates. Please enter numeric values (e.g., 38.0382).")
        lats = [coord['lat'] for coord in gps.node_coords.values()]
        lons = [coord['lon'] for coord in gps.node_coords.values()]
        if not (min(lats) - 0.01 <= start_lat <= max(lats) + 0.01 and min(lons) - 0.01 <= start_lon <= max(lons) + 0.01):
            print("⚠️ Start coordinates outside area. Using default: 1234 Rose St")
            start_lat, start_lon = 38.038237, -84.499202
        if not (min(lats) - 0.01 <= end_lat <= max(lats) + 0.01 and min(lons) - 0.01 <= end_lon <= max(lons) + 0.01):
            print("⚠️ End coordinates outside area. Using default: 5678 Uk Farm Road")
            end_lat, end_lon = 38.024878, -84.507439
        start_address = f"({start_lat:.6f}, {start_lon:.6f})"
        end_address = f"({end_lat:.6f}, {end_lon:.6f})"
    else:
        max_attempts = 3
        attempts = 0
        start_lat, start_lon, end_lat, end_lon = None, None, None, None
        while attempts < max_attempts:
            start_address = input("🚩 Enter start address (e.g., 1234 Rose St, Lexington, KY 40506): ").strip()
            if not start_address:
                print("❌ Start address cannot be empty. Please enter a valid address.")
                attempts += 1
                continue
            if not is_valid_address(start_address):
                print("❌ Invalid address format. Please use: street, city, state [ZIP code].")
                attempts += 1
                continue
            end_address = input("🏁 Enter end address (e.g., 5678 Uk Farm Road, Lexington, KY 40508): ").strip()
            if not end_address:
                print("❌ End address cannot be empty. Please enter a valid address.")
                attempts += 1
                continue
            if not is_valid_address(end_address):
                print("❌ Invalid address format. Please use: street, city, state [ZIP code].")
                attempts += 1
                continue
            print("📍 Converting addresses to coordinates...")
            start_lat, start_lon = gps.geocode_address(start_address)
            end_lat, end_lon = gps.geocode_address(end_address)
            time.sleep(1)  # Respect Nominatim rate limits
            if start_lat is not None and end_lat is not None:
                break
            print("❌ Failed to geocode one or both addresses. Possible reasons:")
            print("   - Address may not exist or is outside the map area (University of Kentucky, Lexington, KY).")
            print("   - Ensure the address includes street, city, state, and optionally ZIP code.")
            print("   - Check for typos or try a nearby known address.")
            print(f"🔄 Attempt {attempts + 1}/{max_attempts}.")
            attempts += 1
        if start_lat is None or end_lat is None:
            print("❌ Max attempts reached. Using default coordinates.")
            print("ℹ️ Please ensure addresses are within the University of Kentucky campus area.")
            start_lat, start_lon = 38.038237, -84.499202
            end_lat, end_lon = 38.024878, -84.507439
            start_address = "1234 Rose St, Lexington, KY 40506"
            end_address = "5678 Uk Farm Road, Lexington, KY 40508"
    
    print(f"\n🚩 Start: {start_address}")
    print(f"🏁 End: {end_address}")
    print("🚗 Calculating route...\n")
    
    path, tips, alerts = gps.route_between_coordinates(
        start_lat, start_lon, end_lat, end_lon, learner_mode=learner_mode
    )
    
    if not path:
        print("❌ No route found. Please check start/end points and try again.")
        return
    
    print(f"\n✅ Navigation Complete! Safe travels!")

if __name__ == "__main__":
    run_navigation_test()