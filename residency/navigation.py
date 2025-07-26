from collections import deque, defaultdict
import math
import osmnx as ox
import networkx as nx
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time
from residency.graph import Graph
import logging

logging.basicConfig(level=logging.INFO, filename='gps.log', format='%(asctime)s - %(levelname)s - %(message)s')

class EnhancedRealWorldGPS(Graph):
    def __init__(self):
        super().__init__()
        self.node_coords = {}
        self.node_info = {}
        self.osm_graph = None
        self.area_name = ""
        self.landmarks = {}
        self.place_cache = {}
        self.geocode_cache = {}  # New cache for geocoded addresses
        self.geolocator = Nominatim(user_agent="gps_village")

    def load_area_by_name(self, place_name, network_type='drive'):
        self.area_name = place_name
        print(f"🗺️ Loading street network for: {place_name}")
        try:
            self.osm_graph = ox.graph_from_place(place_name, network_type=network_type)
            if self.osm_graph.is_directed():
                self.osm_graph = ox.convert.to_undirected(self.osm_graph)
            
            if len(self.osm_graph.nodes) < 10 or len(self.osm_graph.edges) < 10:
                raise ValueError("Insufficient road data for routing.")
            
            print(f"✅ Successfully loaded {len(self.osm_graph.nodes)} intersections and {len(self.osm_graph.edges)} road segments")
            self._load_landmarks_and_poi()
            self._convert_osm_to_enhanced_graph()
            self._show_area_summary()
        except Exception as e:
            print(f"❌ Error loading area: {e}")
            logging.error(f"Error loading area {place_name}: {str(e)}")
            print("🔄 Trying fallback coordinates...")
            self.load_area_by_coordinates(38.0307, -84.5041, distance_km=2.0)

    def load_area_by_coordinates(self, center_lat, center_lon, distance_km=1.0, network_type='drive'):
        self.area_name = f"Area around ({center_lat:.4f}, {center_lon:.4f})"
        print(f"🗺️ Loading street network around ({center_lat}, {center_lon}) within {distance_km} km")
        try:
            self.osm_graph = ox.graph_from_point(
                (center_lat, center_lon), 
                dist=distance_km * 1000,
                network_type=network_type
            )
            if self.osm_graph.is_directed():
                self.osm_graph = ox.convert.to_undirected(self.osm_graph)
            
            if len(self.osm_graph.nodes) < 10 or len(self.osm_graph.edges) < 10:
                raise ValueError("Insufficient road data for routing.")
            
            print(f"✅ Successfully loaded {len(self.osm_graph.nodes)} intersections and {len(self.osm_graph.edges)} road segments")
            self._load_landmarks_and_poi()
            self._convert_osm_to_enhanced_graph()
            self._show_area_summary()
        except Exception as e:
            print(f"❌ Error loading area: {e}")
            logging.error(f"Error loading area at ({center_lat}, {center_lon}): {str(e)}")

    def _load_landmarks_and_poi(self):
        print("🏢 Fetching nearby landmarks and points of interest...")
        if not self.osm_graph:
            print("⚠️ No map data available. Skipping landmark loading.")
            return
        
        nodes_data = [(data['y'], data['x']) for _, data in self.osm_graph.nodes(data=True)]
        if not nodes_data:
            print("⚠️ No nodes found in map data. Skipping landmark loading.")
            return
        
        lats, lons = zip(*nodes_data)
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        print(f"📍 Map center: ({center_lat:.6f}, {center_lon:.6f})")
        
        predefined_landmarks = [
            {'name': 'Memorial Coliseum', 'type': 'Building', 'lat': 38.0297, 'lon': -84.5001},
            {'name': 'William T. Young Library', 'type': 'Library', 'lat': 38.0337, 'lon': -84.5057},
            {'name': 'Kroger Field', 'type': 'Stadium', 'lat': 38.0225, 'lon': -84.5051},
            {'name': 'Gatton Student Center', 'type': 'Building', 'lat': 38.0389, 'lon': -84.5041},
            {'name': 'UK HealthCare', 'type': 'Hospital', 'lat': 38.0312, 'lon': -84.5081}
        ]
        
        total_pois_found = 0
        for landmark in predefined_landmarks:
            poi_lat, poi_lon = landmark['lat'], landmark['lon']
            distance = self.haversine_distance(center_lat, center_lon, poi_lat, poi_lon)
            if distance > 500:
                continue
            
            landmark_key = f"{poi_lat:.6f},{poi_lon:.6f}"
            if landmark_key not in self.landmarks:
                self.landmarks[landmark_key] = {
                    'name': landmark['name'],
                    'type': landmark['type'],
                    'lat': poi_lat,
                    'lon': poi_lon
                }
                print(f"    📍 Loaded predefined: {landmark['name']} ({landmark['type']}) at ({poi_lat:.6f}, {poi_lon:.6f})")
                total_pois_found += 1
        
        poi_categories = [
            {'amenity': ['restaurant', 'cafe', 'hospital', 'school', 'bank']},
            {'amenity': ['gas_station', 'pharmacy', 'police', 'fire_station']},
            {'amenity': ['library', 'post_office']},
            {'shop': ['supermarket', 'convenience', 'mall']},
            {'tourism': ['attraction', 'museum', 'hotel']},
            {'leisure': ['park', 'sports_centre']},
            {'building': ['university', 'college']}
        ]
        
        for category in poi_categories:
            category_key = list(category.keys())[0]
            category_values = category[category_key]
            category_count = 0
            
            for poi_type in category_values:
                for attempt in range(2):
                    try:
                        query = f"{poi_type.replace('_', ' ')}, Lexington, KY"
                        print(f"🔍 Querying {poi_type} near {self.area_name}...")
                        locations = self.geolocator.geocode(
                            query,
                            exactly_one=False,
                            limit=5,
                            timeout=10
                        )
                        if locations:
                            for location in locations:
                                poi_lat, poi_lon = location.latitude, location.longitude
                                distance = self.haversine_distance(center_lat, center_lon, poi_lat, poi_lon)
                                if distance > 500:
                                    continue
                                
                                poi_name = location.raw.get('display_name', '').split(',')[0].strip()
                                if not poi_name or 'Drive' in poi_name or 'Street' in poi_name or len(poi_name) > 50:
                                    continue
                                
                                landmark_key = f"{poi_lat:.6f},{poi_lon:.6f}"
                                if landmark_key not in self.landmarks:
                                    self.landmarks[landmark_key] = {
                                        'name': poi_name,
                                        'type': poi_type.replace('_', ' ').title(),
                                        'lat': poi_lat,
                                        'lon': poi_lon
                                    }
                                    print(f"    📍 Found: {poi_name} ({poi_type}) at ({poi_lat:.6f}, {poi_lon:.6f})")
                                    category_count += 1
                                    total_pois_found += 1
                        break
                    except (GeocoderTimedOut, GeocoderServiceError) as e:
                        print(f"    ⚠️ Error querying {poi_type}: {str(e)}")
                        logging.error(f"Error querying {poi_type}: {str(e)}")
                        if attempt == 1:
                            print(f"    Skipping {poi_type} after retry")
                        time.sleep(1)
                        continue
                    time.sleep(1)
            
            if category_count > 0:
                print(f"    ✅ Loaded {category_count} {category_key} locations")
            else:
                print(f"    ⚠️ No {category_key} locations found")
        
        if total_pois_found > 0:
            print(f"✅ Successfully loaded {total_pois_found} landmarks and points of interest")
        else:
            print("⚠️ No landmarks available. Using street names for navigation.")

    def _get_poi_type(self, poi):
        if 'amenity' in poi and poi['amenity']:
            return poi['amenity'].replace('_', ' ').title()
        elif 'shop' in poi and poi['shop']:
            return f"{poi['shop'].replace('_', ' ').title()} Shop"
        elif 'tourism' in poi and poi['tourism']:
            return poi['tourism'].replace('_', ' ').title()
        elif 'leisure' in poi and poi['leisure']:
            return poi['leisure'].replace('_', ' ').title()
        elif 'building' in poi and poi['building']:
            return poi['building'].replace('_', ' ').title()
        return "Point of Interest"

    def _convert_osm_to_enhanced_graph(self):
        print("🔄 Building navigation graph from map data...")
        self.adj_list = defaultdict(list)
        self.node_coords = {}
        self.node_info = {}
        
        for node_id, data in self.osm_graph.nodes(data=True):
            node_str = str(node_id)
            self.node_coords[node_str] = {'lat': data['y'], 'lon': data['x']}
            
            street_names = set()
            for u, v, edge_data in self.osm_graph.edges(node_id, data=True):
                if 'name' in edge_data and edge_data['name']:
                    if isinstance(edge_data['name'], list):
                        street_names.update(edge_data['name'])
                    else:
                        street_names.add(edge_data['name'])
            
            nearby_landmarks = self._find_nearby_landmarks(data['y'], data['x'])
            self.node_info[node_str] = {
                'streets': list(street_names)[:2],
                'location_desc': self._get_enhanced_location_description(
                    data['y'], data['x'], street_names, nearby_landmarks
                ),
                'nearby_landmarks': nearby_landmarks
            }
        
        for u, v, data in self.osm_graph.edges(data=True):
            u_str, v_str = str(u), str(v)
            distance_m = data.get('length', self.haversine_distance(
                self.node_coords[u_str]['lat'], self.node_coords[u_str]['lon'],
                self.node_coords[v_str]['lat'], self.node_coords[v_str]['lon']
            ))
            crowd_level = self._get_crowd_level(data)
            tip = self._generate_enhanced_tip(data)
            blind_spot = self._is_blind_spot(data)
            
            self.add_edge(u_str, v_str, distance_m, crowd_level, tip, blind_spot)
            self.add_edge(v_str, u_str, distance_m, crowd_level, tip, blind_spot)
        
        print(f"✅ Navigation graph ready with {len(self.adj_list)} intersections")
        print(f"🔍 Graph stats: {len(self.adj_list)} nodes, {sum(len(edges) for edges in self.adj_list.values())//2} edges")

    def find_nearest_node_enhanced(self, lat, lon):
        if not self.node_coords:
            return None
        
        min_distance = float('inf')
        nearest_node = None
        nearest_info = None
        
        for node_id, coords in self.node_coords.items():
            distance = self.haversine_distance(lat, lon, coords['lat'], coords['lon'])
            if distance < min_distance and node_id in self.adj_list:
                min_distance = distance
                nearest_node = node_id
                nearest_info = self.node_info.get(node_id)
        
        if nearest_node:
            return nearest_node, min_distance, nearest_info
        return None

    def route_between_coordinates(self, start_lat, start_lon, end_lat, end_lon, learner_mode=False):
        print(f"\n🚗 Planning route in {self.area_name}")
        print("=" * 60)
        
        start_place_info = self._get_place_name_from_coordinates(start_lat, start_lon)
        end_place_info = self._get_place_name_from_coordinates(end_lat, end_lon)
        
        print(f"🚩 STARTING POINT:")
        print(f"   📍 Coordinates: ({start_lat:.6f}, {start_lon:.6f})")
        print(f"   🏗️ Location: {start_place_info['description']}")
        if start_place_info['nearby_landmarks']:
            print(f"   🏢 Near: {', '.join([lm['name'] for lm in start_place_info['nearby_landmarks']])}")
        
        print(f"\n🏁 DESTINATION:")
        print(f"   📍 Coordinates: ({end_lat:.6f}, {end_lon:.6f})")
        print(f"   🏗️ Destination: {end_place_info['description']}")
        if end_place_info['nearby_landmarks']:
            print(f"   🏢 Near: {', '.join([lm['name'] for lm in end_place_info['nearby_landmarks']])}")
        
        start_result = self.find_nearest_node_enhanced(start_lat, start_lon)
        end_result = self.find_nearest_node_enhanced(end_lat, end_lon)
        
        if not start_result or not end_result:
            print("\n❌ Could not find nearby roads for routing")
            return [], [], []
        
        start_node, start_dist, start_info = start_result
        end_node, end_dist, end_info = end_result
        
        if not self._is_connected(start_node, end_node):
            print("\n❌ No path exists between start and end points")
            return [], [], []
        
        print(f"\n🛣️ ROUTE PLANNING:")
        print(f"   📍 Starting road: {start_info['location_desc']}")
        print(f"      Distance to starting road: {self.meters_to_miles(start_dist):.2f} miles")
        print(f"   🏁 Ending road: {end_info['location_desc']}")
        print(f"      Distance to ending road: {self.meters_to_miles(end_dist):.2f} miles")
        
        mode_desc = "🎓 Learner Mode (safer route)" if learner_mode else "⚡ Normal Mode (fastest route)"
        print(f"   🚦 Navigation mode: {mode_desc}")
        
        path, tips, alerts = self.dijkstra(start_node, end_node, learner_mode)
        
        if path:
            self._display_route_details_with_places(path, tips, alerts, learner_mode)
        else:
            print("\n❌ No route found between these locations")
        
        return path, tips, alerts

    def _is_connected(self, start, end):
        if start == end:
            return True
        visited = set()
        queue = deque([start])
        visited.add(start)
        
        while queue:
            current = queue.popleft()
            for neighbor, _, _, _, _ in self.adj_list.get(current, []):
                if neighbor == end:
                    return True
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return False

    def _get_place_name_from_coordinates(self, lat, lon):
        cache_key = f"{lat:.6f},{lon:.6f}"
        if cache_key in self.place_cache:
            return self.place_cache[cache_key]
        
        nearby_landmarks = self._find_nearby_landmarks(lat, lon)
        description = f"Coordinates ({lat:.4f}, {lon:.4f})"
        if nearby_landmarks:
            closest = nearby_landmarks[0]
            description = f"Near {closest['name']} ({closest['type']})" if closest['distance_m'] < 100 else f"About {int(closest['distance_m'])}m from {closest['name']} ({closest['type']})"
        
        result = {'description': description, 'nearby_landmarks': nearby_landmarks}
        self.place_cache[cache_key] = result
        return result

    def _display_route_details_with_places(self, path, tips, alerts, learner_mode):
        if not path:
            return
        
        summary = self.get_enhanced_route_summary(path)
        print(f"\n✅ Route Found!")
        print(f"📏 Distance: {summary['distance_miles']:.2f} miles ({summary['distance_km']:.1f} km)")
        print(f"⏱️ Estimated Time: {summary['time_minutes']:.0f} minutes")
        print(f"🔄 Turns: {summary['turns']}")
        
        print(f"\n🗺️ Step-by-Step Directions:")
        self._show_route_progress_with_places(path)
        
        if learner_mode:
            print(f"\n🎓 Learner Mode Safety Information:")
            if tips:
                print(f"💡 Safety Tips ({len(tips)} total):")
                for i, tip in enumerate(tips[:4], 1):
                    print(f"    {i}. {tip}")
                if len(tips) > 4:
                    print(f"    ... and {len(tips) - 4} more tips")
            if alerts:
                print(f"🚨 Blind Spot Alerts ({len(alerts)} total):")
                for i, alert in enumerate(alerts[:2], 1):
                    print(f"    {i}. {alert}")
                if len(alerts) > 2:
                    print(f"    ... and {len(alerts) - 2} more alerts")
        else:
            print(f"\n⚡ Normal Mode - Fastest Route")
            if alerts:
                print(f"🚨 Blind Spot Alerts ({len(alerts)} total):")
                for i, alert in enumerate(alerts[:2], 1):
                    print(f"    {i}. {alert}")
                if len(alerts) > 2:
                    print(f"    ... and {len(alerts) - 2} more alerts")

    def _show_route_progress_with_places(self, path):
        waypoints_to_show = min(8, len(path))
        for i in range(waypoints_to_show):
            node = path[i]
            node_info = self.node_info.get(node, {})
            location = node_info.get('location_desc', f'Waypoint {i+1}')
            nearby_landmarks = node_info.get('nearby_landmarks', [])
            
            if i == 0:
                step_icon = "🚗️"
                action = "Start at"
            elif i == len(path) - 1 or i == waypoints_to_show - 1:
                step_icon = "🏁"
                action = "Arrive at"
            else:
                step_icon = "📍"
                action = "Turn onto" if nearby_landmarks or node_info.get('streets') else "Continue to"
            
            print(f"    {step_icon} {action} {location}")
            if nearby_landmarks:
                landmark_names = [lm['name'] for lm in nearby_landmarks[:2]]
                print(f"        🏢 Near: {', '.join(landmark_names)}")
            if i < len(path) - 1 and i < waypoints_to_show - 1:
                distance = self._get_distance_between_nodes(path[i], path[i+1])
                if distance:
                    print(f"        ↳ Proceed {self.meters_to_miles(distance):.2f} miles")
                print()

    def _find_nearby_landmarks(self, lat, lon, max_distance_m=500):
        nearby = []
        for landmark_key, landmark_data in self.landmarks.items():
            distance = self.haversine_distance(lat, lon, landmark_data['lat'], landmark_data['lon'])
            if distance <= max_distance_m:
                nearby.append({
                    'name': landmark_data['name'],
                    'type': landmark_data['type'],
                    'distance_m': distance,
                    'priority': 1 if landmark_data['type'] in ['Building', 'Stadium', 'Hospital', 'Library'] else 2
                })
        nearby.sort(key=lambda x: (x['distance_m'], x['priority'], len(x['name'])))
        return nearby[:2]

    def _get_enhanced_location_description(self, lat, lon, street_names, nearby_landmarks):
        description_parts = []
        if nearby_landmarks:
            closest_landmark = nearby_landmarks[0]
            distance_m = closest_landmark['distance_m']
            distance_desc = "very close to" if distance_m < 50 else f"about {int(distance_m)}m from" if distance_m > 200 else "near"
            description_parts.append(f"{distance_desc} {closest_landmark['name']} ({closest_landmark['type']})")
        if street_names:
            primary_street = list(street_names)[0]
            if len(street_names) > 1:
                secondary_street = list(street_names)[1]
                description_parts.append(f"intersection of {primary_street} and {secondary_street}")
            else:
                description_parts.append(f"on {primary_street}")
        return " - ".join(description_parts) if description_parts else f"Coordinates ({lat:.4f}, {lon:.4f})"

    def meters_to_miles(self, meters):
        return meters * 0.000621371

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371000
        return c * r

    def _get_distance_between_nodes(self, node1, node2):
        for neighbor, weight, _, _, _ in self.adj_list[node1]:
            if neighbor == node2:
                return weight
        return None

    def get_enhanced_route_summary(self, path):
        if not path or len(path) < 2:
            return {
                "distance_meters": 0, "distance_km": 0, "distance_miles": 0,
                "time_minutes": 0, "turns": 0, "nodes": 0
            }
        
        total_distance_m = 0
        turns = len(path) - 2
        for i in range(1, len(path)):
            u, v = path[i-1], path[i]
            for neighbor, weight, _, _, _ in self.adj_list[u]:
                if neighbor == v:
                    total_distance_m += weight
                    break
        
        time_minutes = self._estimate_travel_time(path, total_distance_m)
        return {
            "distance_meters": total_distance_m,
            "distance_km": total_distance_m / 1000,
            "distance_miles": self.meters_to_miles(total_distance_m),
            "time_minutes": time_minutes,
            "turns": turns,
            "nodes": len(path)
        }

    def _estimate_travel_time(self, path, total_distance_m):
        avg_speed_mph = 30
        return (self.meters_to_miles(total_distance_m) / avg_speed_mph) * 60

    def _show_area_summary(self):
        if not self.node_coords:
            return
        lats = [coord['lat'] for coord in self.node_coords.values()]
        lons = [coord['lon'] for coord in self.node_coords.values()]
        print(f"\n📍 AREA OVERVIEW:")
        print(f"   🏛️ Location: {self.area_name}")
        print(f"   📐 Coverage: {min(lats):.4f} to {max(lats):.4f} lat, {min(lons):.4f} to {max(lons):.4f} lon")
        print(f"   🛣️ Waypoints: {len(self.node_coords):,}")
        print(f"   🏢 Landmarks: {len(self.landmarks)}")

    def _generate_enhanced_tip(self, edge_data):
        highway_type = edge_data.get('highway', 'unclassified')
        name = edge_data.get('name', '')
        maxspeed = edge_data.get('maxspeed', '')
        if isinstance(highway_type, list):
            highway_type = highway_type[0]
        
        base_tips = {
            'motorway': f'🛣️ Highway driving on {name}: Check mirrors, maintain 65+ mph',
            'primary': f'🏙️ Main road {name}: Be alert for intersections, 35-45 mph',
            'residential': f'🏠 Residential street {name}: Watch for children, 25 mph max'
        }
        tip = base_tips.get(highway_type, f'🚙 Navigate carefully on {name}' if name else '🚙 Drive safely')
        if maxspeed:
            tip += f' (Speed limit: {maxspeed})'
        return tip

    def _get_crowd_level(self, edge_data):
        highway_type = edge_data.get('highway', 'unclassified')
        high_traffic = ['motorway', 'trunk', 'primary']
        medium_traffic = ['secondary', 'tertiary']
        if isinstance(highway_type, list):
            highway_type = highway_type[0]
        return 'high' if highway_type in high_traffic else 'medium' if highway_type in medium_traffic else 'low'

    def _is_blind_spot(self, edge_data):
        highway_type = edge_data.get('highway', 'unclassified')
        if isinstance(highway_type, list):
            highway_type = highway_type[0]
        return highway_type in ['motorway_link', 'trunk_link', 'primary_link']

    def geocode_address(self, address):
        """Convert address to coordinates using Nominatim with retries and caching."""
        if not address.strip():
            print(f"❌ Empty address provided.")
            logging.error("Empty address provided for geocoding")
            return None, None
        
        # Check cache
        cache_key = address.lower().strip()
        if cache_key in self.geocode_cache:
            lat, lon = self.geocode_cache[cache_key]
            print(f"✅ Retrieved {address} from cache: ({lat:.6f}, {lon:.6f})")
            return lat, lon

        max_retries = 2
        for attempt in range(max_retries):
            try:
                location = self.geolocator.geocode(address, timeout=10)
                if location:
                    lat, lon = location.latitude, location.longitude
                    # Validate coordinates against map area
                    lats = [coord['lat'] for coord in self.node_coords.values()]
                    lons = [coord['lon'] for coord in self.node_coords.values()]
                    if not (min(lats) - 0.01 <= lat <= max(lats) + 0.01 and min(lons) - 0.01 <= lon <= max(lons) + 0.01):
                        print(f"❌ Address {address} is outside the loaded map area (University of Kentucky, Lexington, KY).")
                        logging.error(f"Address {address} geocoded to ({lat:.6f}, {lon:.6f}) outside map area")
                        return None, None
                    # Cache the result
                    self.geocode_cache[cache_key] = (lat, lon)
                    print(f"✅ Successfully geocoded {address} to ({lat:.6f}, {lon:.6f})")
                    return lat, lon
                else:
                    print(f"❌ Could not geocode address: {address}")
                    logging.error(f"Could not geocode address: {address}")
                    return None, None
            except (GeocoderTimedOut, GeocoderServiceError) as e:
                print(f"❌ Geocoding attempt {attempt + 1}/{max_retries} failed for {address}: {str(e)}")
                logging.error(f"Geocoding failed for {address}: {str(e)}")
                if attempt == max_retries - 1:
                    print(f"❌ Max retries reached for {address}")
                    return None, None
                time.sleep(2)  # Wait before retrying
