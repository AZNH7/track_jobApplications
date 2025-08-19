"""
Scraper Utilities

Helper functions for job filtering, matching, and data processing.
"""

import re
import math
from typing import List, Dict, Set, Optional, Tuple
from collections import Counter

# Add language detection
try:
    from langdetect import detect, DetectorFactory
    # Set seed for consistent results
    DetectorFactory.seed = 0
    LANGUAGE_DETECTION_AVAILABLE = True
except ImportError:
    LANGUAGE_DETECTION_AVAILABLE = False


class JobFilters:
    """Job filtering utilities."""
    
    @staticmethod
    def filter_by_keywords(jobs: List[Dict], keywords: str, platform_name: str = "Unknown") -> List[Dict]:
        """
        Filter jobs by keyword relevance.
        
        Args:
            jobs: List of job dictionaries
            keywords: Search keywords
            platform_name: Name of the platform for logging
            
        Returns:
            Filtered list of jobs
        """
        if not keywords or not jobs:
            return jobs
        
        # Parse keywords
        keyword_list = JobFilters._parse_keywords(keywords)
        if not keyword_list:
            return jobs
        
        filtered_jobs = []
        
        for job in jobs:
            title = (job.get('title', '') or '').lower()
            description = (job.get('description', '') or '').lower()
            tags = (job.get('tags', '') or '').lower()
            
            # Calculate match score
            match_score = JobFilters._calculate_keyword_match_score(
                keyword_list, title, description, tags
            )
            
            # Keep jobs with reasonable match score
            if match_score >= 0.3:  # 30% match threshold
                job['keyword_match_score'] = match_score
                filtered_jobs.append(job)
        
        print(f"   🔍 {platform_name}: Filtered {len(jobs) - len(filtered_jobs)} jobs by keywords")
        return filtered_jobs
    
    @staticmethod
    def filter_by_location(jobs: List[Dict], searched_locations: Optional[List[str]] = None, 
                          platform_name: str = "Unknown", 
                          use_enhanced_filtering: bool = True,
                          max_distance_km: float = 50.0) -> List[Dict]:
        """
        Filter jobs by German location with optional distance-based filtering.
        
        Args:
            jobs: List of job dictionaries
            searched_locations: List of searched locations
            platform_name: Name of the platform for logging
            use_enhanced_filtering: Whether to use enhanced distance-based filtering
            max_distance_km: Maximum distance from Essen in kilometers
            
        Returns:
            Filtered list of jobs
        """
        if not jobs:
            return jobs
        
        filtered_jobs = []
        
        for job in jobs:
            location = job.get('location', '') or ''
            title = job.get('title', '') or ''
            description = job.get('description', '') or ''
            job_url = (job.get('url', '') or '').lower()
            
            # Skip location filtering for Indeed jobs since they already come with location-based filtering
            job_platform = (job.get('platform', '') or '').lower()
            job_source = (job.get('source', '') or '').lower()
            is_indeed_job = ('indeed.com' in job_url or 
                           job_platform == 'indeed' or 
                           job_source == 'indeed')
            
            if is_indeed_job:
                # Indeed jobs are already location-filtered by the search, so keep them
                filtered_jobs.append(job)
                continue
            
            # Choose filtering method for non-Indeed jobs
            if use_enhanced_filtering:
                is_valid = JobFilters._is_german_location_with_distance(
                    location, title, description, searched_locations, max_distance_km
                )
            else:
                is_valid = JobFilters._is_german_location(
                    location, title, description, searched_locations
                )
            
            if is_valid:
                filtered_jobs.append(job)
        
        filtered_count = len(jobs) - len(filtered_jobs)
        filter_type = f"enhanced distance ({max_distance_km}km)" if use_enhanced_filtering else "basic German"
        print(f"   🌍 {platform_name}: Filtered {filtered_count} jobs by location ({filter_type})")
        return filtered_jobs
    
    @staticmethod
    def filter_by_language(jobs: List[Dict], english_only: bool = False, 
                          platform_name: str = "Unknown") -> List[Dict]:
        """
        Filter jobs by language.
        
        Args:
            jobs: List of job dictionaries
            english_only: If True, keep only English jobs; if False, keep only German jobs
            platform_name: Name of the platform for logging
            
        Returns:
            Filtered list of jobs
        """
        if not jobs:
            return jobs
        
        filtered_jobs = []
        
        for job in jobs:
            title = job.get('title', '')
            description = job.get('description', '')
            
            is_english = JobFilters._is_english_job(title, description)
            
            if english_only and is_english:
                filtered_jobs.append(job)
            elif not english_only and not is_english:
                filtered_jobs.append(job)
        
        lang_type = "English" if english_only else "German"
        print(f"   🗣️ {platform_name}: Filtered {len(jobs) - len(filtered_jobs)} non-{lang_type} jobs")
        return filtered_jobs
    
    @staticmethod
    def _parse_keywords(keywords: str) -> List[str]:
        """Parse keywords string into list."""
        if not keywords:
            return []
        
        # Split by common separators
        keyword_list = re.split(r'[,;|+&]', keywords)
        
        # Clean and normalize
        cleaned_keywords = []
        for keyword in keyword_list:
            cleaned = keyword.strip().lower()
            if cleaned:
                cleaned_keywords.append(cleaned)
        
        return cleaned_keywords
    
    @staticmethod
    def _calculate_keyword_match_score(keywords: List[str], title: str, 
                                     description: str, tags: str) -> float:
        """Calculate keyword match score."""
        if not keywords:
            return 1.0
        
        # Combine all text
        all_text = f"{title} {description} {tags}".lower()
        
        # Count matches
        matches = 0
        for keyword in keywords:
            if keyword in all_text:
                matches += 1
        
        # Calculate score
        return matches / len(keywords)
    
    @staticmethod
    def _is_german_location(location: str, job_title: str = "", job_description: str = "", 
                           searched_locations: Optional[List[str]] = None) -> bool:
        """Check if a job location is in Germany."""
        if not location:
            return False
        
        location_lower = location.lower()
        
        # First, check for non-German countries and reject them immediately
        non_german_countries = [
            'usa', 'united states', 'america', 'american', 'u.s.', 'u.s.a.',
            'canada', 'canadian',
            'uk', 'united kingdom', 'england', 'scotland', 'wales',
            'australia', 'australian',
            'india', 'indian',
            'china', 'chinese',
            'japan', 'japanese',
            'singapore', 'singaporean',
            'hong kong',
            'belgium', 'belgian',
            'netherlands', 'dutch',
            'france', 'french',
            'austria', 'austrian',
            'switzerland', 'swiss',
            'poland', 'polish',
            'italy', 'italian',
            'spain', 'spanish'
        ]
        
        # Reject if location contains non-German country indicators
        if any(country in location_lower for country in non_german_countries):
            return False
        
        # Major US cities to reject
        us_cities = [
            'new york', 'los angeles', 'chicago', 'houston', 'phoenix', 'philadelphia',
            'san antonio', 'san diego', 'dallas', 'san jose', 'austin', 'jacksonville',
            'fort worth', 'columbus', 'charlotte', 'san francisco', 'indianapolis',
            'seattle', 'denver', 'washington', 'boston', 'el paso', 'nashville',
            'detroit', 'oklahoma city', 'portland', 'las vegas', 'memphis',
            'louisville', 'baltimore', 'milwaukee', 'albuquerque', 'tucson',
            'fresno', 'sacramento', 'atlanta', 'kansas city', 'long beach',
            'colorado springs', 'raleigh', 'miami', 'virginia beach', 'omaha',
            'oakland', 'minneapolis', 'tulsa', 'arlington', 'tampa', 'new orleans',
            'wichita', 'cleveland', 'bakersfield', 'aurora', 'anaheim', 'santa ana',
            'corpus christi', 'riverside', 'lexington', 'stockton', 'henderson',
            'saint paul', 'st. paul', 'st louis', 'cincinnati', 'pittsburgh',
            'anchorage', 'greensboro', 'plano', 'newark', 'durham', 'lincoln',
            'orlando', 'chula vista', 'irvine', 'laredo', 'norfolk', 'lubbock',
            'madison', 'gilbert', 'chandler', 'buffalo', 'north las vegas',
            'chandler', 'lubbock', 'madison', 'gilbert', 'buffalo', 'north las vegas'
        ]
        
        # Reject if location contains US city names
        if any(city in location_lower for city in us_cities):
            return False
        
        # German city patterns
        german_cities = [
            'berlin', 'hamburg', 'münchen', 'munich', 'köln', 'cologne', 'frankfurt',
            'stuttgart', 'düsseldorf', 'dortmund', 'essen', 'leipzig', 'bremen',
            'dresden', 'hannover', 'nürnberg', 'nuremberg', 'duisburg', 'bochum',
            'wuppertal', 'bielefeld', 'bonn', 'münster', 'karlsruhe', 'mannheim',
            'augsburg', 'wiesbaden', 'gelsenkirchen', 'mönchengladbach', 'braunschweig',
            'chemnitz', 'kiel', 'aachen', 'halle', 'magdeburg', 'freiburg', 'krefeld',
            'lübeck', 'oberhausen', 'erfurt', 'mainz', 'rostock', 'kassel', 'hagen',
            'potsdam', 'saarbrücken', 'hamm', 'mülheim', 'ludwigshafen', 'leverkusen',
            'oldenburg', 'osnabrück', 'solingen', 'heidelberg', 'herne', 'neuss',
            'darmstadt', 'paderborn', 'regensburg', 'ingolstadt', 'würzburg',
            'fürth', 'wolfsburg', 'offenbach', 'ulm', 'heilbronn', 'pforzheim',
            'göttingen', 'bottrop', 'trier', 'recklinghausen', 'reutlingen',
            'bremerhaven', 'koblenz', 'bergisch', 'gladbach', 'jena', 'remscheid',
            'erlangen', 'moers', 'siegen', 'hildesheim', 'salzgitter'
        ]
        
        # German state patterns
        german_states = [
            'baden-württemberg', 'bayern', 'bavaria', 'berlin', 'brandenburg',
            'bremen', 'hamburg', 'hessen', 'hesse', 'mecklenburg-vorpommern',
            'niedersachsen', 'lower saxony', 'nordrhein-westfalen', 'north rhine-westphalia',
            'rheinland-pfalz', 'rhineland-palatinate', 'saarland', 'sachsen', 'saxony',
            'sachsen-anhalt', 'saxony-anhalt', 'schleswig-holstein', 'thüringen', 'thuringia'
        ]
        
        # Country indicators
        if any(indicator in location_lower for indicator in ['deutschland', 'germany', 'de']):
            return True
        
        # City check
        if any(city in location_lower for city in german_cities):
            return True
        
        # State check
        if any(state in location_lower for state in german_states):
            return True
        
        # Check against searched locations if provided
        if searched_locations:
            for searched_loc in searched_locations:
                if searched_loc.lower() in location_lower:
                    return True
        
        return False

    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the Haversine distance between two points on Earth in kilometers.
        
        Args:
            lat1, lon1: Latitude and longitude of first point
            lat2, lon2: Latitude and longitude of second point
            
        Returns:
            Distance in kilometers
        """
        # Convert decimal degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of Earth in kilometers
        r = 6371
        
        return c * r

    @staticmethod
    def _get_city_coordinates() -> Dict[str, Tuple[float, float]]:
        """
        Get coordinates for German cities.
        
        Returns:
            Dictionary mapping city names to (latitude, longitude) tuples
        """
        return {
            # Reference point
            'essen': (51.4556, 7.0116),
            'berlin': (52.5200, 13.4050),
            
            # Cities within ~35km of Essen (should KEEP)
            'düsseldorf': (51.2277, 6.7735),
            'duisburg': (51.4344, 6.7623),
            'mülheim': (51.4267, 6.8833),
            'mülheim an der ruhr': (51.4267, 6.8833),
            'oberhausen': (51.4963, 6.8516),
            'neuss': (51.1979, 6.6906),
            'bochum': (51.4818, 7.2162),
            'wuppertal': (51.2562, 7.1508),
            'gelsenkirchen': (51.5177, 7.0857),
            'bottrop': (51.5216, 6.9289),
            'herne': (51.5386, 7.2256),
            'recklinghausen': (51.6142, 7.1963),
            'dorsten': (51.6563, 6.9663),
            'gladbeck': (51.5739, 6.9858),
            'marl': (51.6581, 7.0911),
            'herten': (51.5945, 7.1340),
            'castrop-rauxel': (51.5547, 7.3072),
            'datteln': (51.6456, 7.3397),
            'haltern am see': (51.7457, 7.1829),
            'erkrath': (51.2240, 6.9074),
            'ratingen': (51.2989, 6.8503),
            'heiligenhaus': (51.3228, 6.9697),
            'velbert': (51.3394, 7.0457),
            'mettmann': (51.2541, 6.9750),
            'moers': (51.4508, 6.6407),
            'krefeld': (51.3388, 6.5853),
            'kamp-lintfort': (51.4956, 6.5395),
            'rheinberg': (51.5441, 6.5959),
            'wesel': (51.6584, 6.6200),
            'voerde': (51.5969, 6.6944),
            'dinslaken': (51.5633, 6.7394),
            'hamminkeln': (51.7327, 6.5936),
            'rees': (51.7569, 6.3958),
            'xanten': (51.6619, 6.4453),
            'kevelaer': (51.5834, 6.2475),
            'goch': (51.6823, 6.1626),
            'kleve': (51.7890, 6.1384),
            
            # German cities outside 35km (should FILTER)
            'köln': (50.9375, 6.9603),
            'cologne': (50.9375, 6.9603),
            'bonn': (50.7374, 7.0982),
            'aachen': (50.7753, 6.0839),
            'münster': (51.9607, 7.6261),
            'dortmund': (51.5136, 7.4653),
            'berlin': (52.5200, 13.4050),
            'hamburg': (53.5511, 9.9937),
            'münchen': (48.1351, 11.5820),
            'munich': (48.1351, 11.5820),
            'stuttgart': (48.7758, 9.1829),
            'frankfurt': (50.1109, 8.6821),
            'bremen': (53.0793, 8.8017),
            'leipzig': (51.3397, 12.3731),
            'dresden': (51.0504, 13.7373),
            'hannover': (52.3759, 9.7320),
            'nürnberg': (49.4521, 11.0767),
            'nuremberg': (49.4521, 11.0767),
            'karlsruhe': (49.0069, 8.4037),
            'mannheim': (49.4875, 8.4660),
            'augsburg': (48.3705, 10.8978),
            'wiesbaden': (50.0782, 8.2398),
            'bielefeld': (52.0302, 8.5325),
            'braunschweig': (52.2689, 10.5268),
            'chemnitz': (50.8278, 12.9214),
            'kiel': (54.3233, 10.1228),
            'halle': (51.4969, 11.9695),
            'magdeburg': (52.1205, 11.6276),
            'freiburg': (47.9990, 7.8421),
            'lübeck': (53.8655, 10.6866),
            'erfurt': (50.9787, 11.0328),
            'mainz': (49.9929, 8.2473),
            'rostock': (54.0887, 12.1288),
            'kassel': (51.3127, 9.4797),
            'hagen': (51.3670, 7.4637),
            'potsdam': (52.3906, 13.0645),
            'saarbrücken': (49.2401, 6.9969),
            'hamm': (51.6806, 7.8142),
            'ludwigshafen': (49.4775, 8.4344),
            'leverkusen': (51.0353, 6.9804),
            'oldenburg': (53.1435, 8.2146),
            'osnabrück': (52.2799, 8.0472),
            'solingen': (51.1651, 7.0679),
            'heidelberg': (49.3988, 8.6724),
            'darmstadt': (49.8728, 8.6512),
            'paderborn': (51.7189, 8.7545),
            'regensburg': (49.0134, 12.1016),
            'ingolstadt': (48.7665, 11.4257),
            'würzburg': (49.7913, 9.9534),
            'fürth': (49.4771, 10.9886),
            'wolfsburg': (52.4227, 10.7865),
            'offenbach': (50.0955, 8.7761),
            'ulm': (48.3984, 9.9916),
            'heilbronn': (49.1427, 9.2109),
            'pforzheim': (48.8946, 8.7024),
            'göttingen': (51.5412, 9.9158),
            'trier': (49.7490, 6.6371),
            'reutlingen': (48.4919, 9.2042),
            'bremerhaven': (53.5396, 8.5809),
            'koblenz': (50.3569, 7.5890),
            'bergisch gladbach': (50.9924, 7.1287),
            'jena': (50.9248, 11.5806),
            'remscheid': (51.1790, 7.1937),
            'erlangen': (49.5896, 11.0040),
            'siegen': (50.8749, 8.0237),
            'hildesheim': (52.1561, 9.9511),
            'salzgitter': (52.1563, 10.4156),
            'rheinbach': (50.6236, 6.9482),
        }

    @staticmethod
    def _is_within_essen_radius(location: str, max_distance_km: float = 50.0) -> bool:
        """
        Check if a location is within the specified radius of Essen, Germany.
        
        Args:
            location: Location string to check
            max_distance_km: Maximum distance in kilometers (default: 35km)
            
        Returns:
            True if within radius or if location cannot be determined
        """
        if not location:
            return False
            
        location_lower = location.lower().strip()
        
        # Get city coordinates
        city_coords = JobFilters._get_city_coordinates()
        essen_coords = city_coords['essen']
        
        # Check for exact city name matches
        for city_name, (lat, lon) in city_coords.items():
            if city_name in location_lower:
                distance = JobFilters._haversine_distance(
                    essen_coords[0], essen_coords[1], lat, lon
                )
                print(f"   📍 Location check: {location} -> {city_name} = {distance:.1f}km from Essen (max: {max_distance_km}km)")
                return distance <= max_distance_km
        
        # Special handling for partial matches and common variations
        location_variations = {
            'mülheim': 'mülheim an der ruhr',
            'bergisch': 'bergisch gladbach',
            'gladbach': 'bergisch gladbach',
        }
        
        for variation, full_name in location_variations.items():
            if variation in location_lower and full_name in city_coords:
                coords = city_coords[full_name]
                distance = JobFilters._haversine_distance(
                    essen_coords[0], essen_coords[1], coords[0], coords[1]
                )
                return distance <= max_distance_km
        
        # If we can't determine the location, return False for safety
        return False

    @staticmethod
    def _is_within_location_radius(location: str, reference_location: str, max_distance_km: float = 50.0) -> bool:
        """
        Check if a location is within the specified radius of a reference location.
        
        Args:
            location: Location string to check
            reference_location: Reference location string
            max_distance_km: Maximum distance in kilometers
            
        Returns:
            True if within radius or if location cannot be determined
        """
        if not location or not reference_location:
            return False
            
        location_lower = location.lower().strip()
        reference_lower = reference_location.lower().strip()
        
        # Get city coordinates
        city_coords = JobFilters._get_city_coordinates()
        
        # Check if reference location is in our coordinates
        reference_coords = None
        for city_name, coords in city_coords.items():
            if city_name in reference_lower:
                reference_coords = coords
                break
        
        if not reference_coords:
            # If reference location not found, allow the job (fallback)
            return True
        
        # Check for exact city name matches in job location
        for city_name, (lat, lon) in city_coords.items():
            if city_name in location_lower:
                distance = JobFilters._haversine_distance(
                    reference_coords[0], reference_coords[1], lat, lon
                )
                print(f"   📍 Location check: {location} -> {city_name} = {distance:.1f}km from {reference_location} (max: {max_distance_km}km)")
                return distance <= max_distance_km
        
        # Special handling for partial matches and common variations
        location_variations = {
            'mülheim': 'mülheim an der ruhr',
            'bergisch': 'bergisch gladbach',
            'gladbach': 'bergisch gladbach',
        }
        
        for variation, full_name in location_variations.items():
            if variation in location_lower and full_name in city_coords:
                coords = city_coords[full_name]
                distance = JobFilters._haversine_distance(
                    reference_coords[0], reference_coords[1], coords[0], coords[1]
                )
                return distance <= max_distance_km
        
        # If we can't determine the location, return True for safety (allow the job)
        return True

    @staticmethod
    def _is_german_location_with_distance(location: str, job_title: str = "", job_description: str = "", 
                                         searched_locations: Optional[List[str]] = None, 
                                         max_distance_km: float = 50.0) -> bool:
        """
        Enhanced German location check that includes distance filtering from Essen.
        
        Args:
            location: Job location string
            job_title: Job title for additional context
            job_description: Job description for additional context  
            searched_locations: List of searched locations for context
            max_distance_km: Maximum distance from Essen in kilometers
            
        Returns:
            True if location is in Germany AND within distance radius of Essen, False otherwise
        """
        if not location:
            return False
        
        location_lower = location.lower()
        
        # First, check for non-German countries and reject them immediately
        non_german_countries = [
            'usa', 'united states', 'america', 'american', 'u.s.', 'u.s.a.',
            'canada', 'canadian',
            'uk', 'united kingdom', 'england', 'scotland', 'wales',
            'australia', 'australian',
            'india', 'indian',
            'china', 'chinese',
            'japan', 'japanese',
            'singapore', 'singaporean',
            'hong kong',
            'belgium', 'belgian',
            'netherlands', 'dutch',
            'france', 'french',
            'austria', 'austrian',
            'switzerland', 'swiss',
            'poland', 'polish',
            'italy', 'italian',
            'spain', 'spanish'
        ]
        
        # Reject if location contains non-German country indicators
        if any(country in location_lower for country in non_german_countries):
            return False
        
        # Major US cities to reject
        us_cities = [
            'new york', 'los angeles', 'chicago', 'houston', 'phoenix', 'philadelphia',
            'san antonio', 'san diego', 'dallas', 'san jose', 'austin', 'jacksonville',
            'fort worth', 'columbus', 'charlotte', 'san francisco', 'indianapolis',
            'seattle', 'denver', 'washington', 'boston', 'el paso', 'nashville',
            'detroit', 'oklahoma city', 'portland', 'las vegas', 'memphis',
            'louisville', 'baltimore', 'milwaukee', 'albuquerque', 'tucson',
            'fresno', 'sacramento', 'atlanta', 'kansas city', 'long beach',
            'colorado springs', 'raleigh', 'miami', 'virginia beach', 'omaha',
            'oakland', 'minneapolis', 'tulsa', 'arlington', 'tampa', 'new orleans',
            'wichita', 'cleveland', 'bakersfield', 'aurora', 'anaheim', 'santa ana',
            'corpus christi', 'riverside', 'lexington', 'stockton', 'henderson',
            'saint paul', 'st. paul', 'st louis', 'cincinnati', 'pittsburgh',
            'anchorage', 'greensboro', 'plano', 'newark', 'durham', 'lincoln',
            'orlando', 'chula vista', 'irvine', 'laredo', 'norfolk', 'lubbock',
            'madison', 'gilbert', 'chandler', 'buffalo', 'north las vegas'
        ]
        
        # Reject if location contains US city names
        if any(city in location_lower for city in us_cities):
            return False
        
        # Check for remote work (always allow remote)
        remote_indicators = ['remote', 'home office', 'homeoffice', 'hybrid', 'flexibel']
        if any(indicator in location_lower for indicator in remote_indicators):
            return True
        
        # Check if it's within distance radius of searched location or Essen as fallback
        if searched_locations and searched_locations[0]:
            # Use the first searched location as reference point
            reference_location = searched_locations[0].lower()
            return JobFilters._is_within_location_radius(location, reference_location, max_distance_km)
        else:
            # Fallback to Essen if no searched location provided
            return JobFilters._is_within_essen_radius(location, max_distance_km)
    
    @staticmethod
    def _is_english_job(job_title: str, job_description: str = "") -> bool:
        """Check if a job is in English language."""
        if not LANGUAGE_DETECTION_AVAILABLE:
            return JobFilters._is_english_simple_detection(job_title, job_description)
        
        try:
            # Combine title and description for better detection
            text_to_check = f"{job_title} {job_description}".strip()
            
            if len(text_to_check) < 10:
                # Too short for reliable detection, use simple method
                return JobFilters._is_english_simple_detection(job_title, job_description)
            
            detected_lang = detect(text_to_check)
            return detected_lang == 'en'
            
        except Exception:
            # Fall back to simple detection if language detection fails
            return JobFilters._is_english_simple_detection(job_title, job_description)
    
    @staticmethod
    def _is_english_simple_detection(job_title: str, job_description: str = "") -> bool:
        """Sophisticated language detection based on main job description content."""
        # Focus on the main job description, not just title
        main_content = job_description if job_description else job_title
        if not main_content:
            return False
        
        # Clean and normalize text
        text_to_check = main_content.lower()
        
        # Strong German language indicators (only count if they appear in meaningful context)
        strong_german_indicators = [
            'wir suchen', 'für unser', 'mitarbeiter', 'unternehmen', 'bereich',
            'erfahrung', 'kenntnisse', 'aufgaben', 'anforderungen', 'qualifikation',
            'bewerbung', 'arbeitsplatz', 'stelle', 'gmbh', 'ag', '(m/w/d)', '(w/m/d)',
            'deutsch', 'deutschland', 'entwickler', 'ingenieur', 'berater'
        ]
        
        # Strong English language indicators
        strong_english_indicators = [
            'we are looking', 'for our', 'team', 'experience', 'skills',
            'responsibilities', 'requirements', 'opportunity', 'position',
            'developer', 'engineer', 'consultant', 'company', 'ltd', 'inc',
            'you will', 'you should', 'you must', 'we offer', 'we provide'
        ]
        
        # Count strong indicators
        german_score = sum(1 for indicator in strong_german_indicators if indicator in text_to_check)
        english_score = sum(1 for indicator in strong_english_indicators if indicator in text_to_check)
        
        # Analyze sentence structure and patterns
        german_patterns = [
            r'\bder\b', r'\bdie\b', r'\bdas\b', r'\bund\b', r'\bmit\b', r'\bfür\b',
            r'\bvon\b', r'\bzu\b', r'\bbei\b', r'\bnach\b', r'\büber\b'
        ]
        english_patterns = [
            r'\bthe\b', r'\band\b', r'\bwith\b', r'\bfor\b', r'\bfrom\b',
            r'\bto\b', r'\bat\b', r'\bafter\b', r'\bover\b'
        ]
        
        # Count pattern matches
        import re
        german_pattern_count = sum(len(re.findall(pattern, text_to_check)) for pattern in german_patterns)
        english_pattern_count = sum(len(re.findall(pattern, text_to_check)) for pattern in english_patterns)
        
        # Weighted scoring system
        total_german_score = german_score * 3 + german_pattern_count * 0.5
        total_english_score = english_score * 3 + english_pattern_count * 0.5
        
        # Determine language based on weighted scores
        if total_german_score > total_english_score and total_german_score >= 2:
            return False  # German
        elif total_english_score > total_german_score and total_english_score >= 2:
            return True   # English
        else:
            # If scores are close or low, check for explicit language indicators
            if any(phrase in text_to_check for phrase in ['english', 'international', 'global']):
                return True
            elif any(phrase in text_to_check for phrase in ['german', 'deutsch', 'deutschland']):
                return False
            else:
                # Default to English for international job postings
                return True


class LocationExtractor:
    """Utilities for extracting and processing location information."""
    
    @staticmethod
    def extract_location_from_content(title: str, description: str, company: str) -> str:
        """Extract location information from job content."""
        # Common location patterns in German job postings
        location_patterns = [
            r'(?:in|bei|Standort)\s+([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*)',
            r'([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*)\s*,\s*Deutschland',
            r'(\d{5})\s+([A-ZÄÖÜ][a-zäöüß]+)',  # Postal code + city
            r'Raum\s+([A-ZÄÖÜ][a-zäöüß]+)',
            r'Nähe\s+([A-ZÄÖÜ][a-zäöüß]+)',
        ]
        
        text_to_check = f"{title} {description} {company}"
        
        for pattern in location_patterns:
            matches = re.findall(pattern, text_to_check)
            if matches:
                # Return the first match
                if isinstance(matches[0], tuple):
                    return ' '.join(matches[0])
                else:
                    return matches[0]
        
        return ""
    
    @staticmethod
    def extract_city_from_location(location: str) -> str:
        """Extract city name from location string."""
        if not location:
            return ""
        
        # Remove common prefixes and suffixes
        location = re.sub(r'^(Raum|Nähe|bei|in)\s+', '', location, flags=re.IGNORECASE)
        location = re.sub(r'\s+(und Umgebung|Umgebung|Region|Bereich)$', '', location, flags=re.IGNORECASE)
        
        # Split by comma and take the first part
        parts = location.split(',')
        city = parts[0].strip()
        
        # Remove postal codes
        city = re.sub(r'^\d{5}\s+', '', city)
        
        return city
    
    @staticmethod
    def normalize_location(location: str) -> str:
        """Normalize location string for consistent processing."""
        if not location:
            return ""
        
        # Remove extra whitespace
        location = re.sub(r'\s+', ' ', location.strip())
        
        # Common replacements
        replacements = {
            'München': 'Munich',
            'Köln': 'Cologne',
            'Nürnberg': 'Nuremberg',
        }
        
        for german, english in replacements.items():
            location = location.replace(german, english)
        
        return location


class KeywordMatcher:
    """Utilities for keyword matching and scoring."""
    
    @staticmethod
    def calculate_strict_match_score(keywords: str, job_title: str, 
                                   job_description: str = "", job_tags: str = "") -> Dict:
        """
        Calculate strict keyword match score with detailed breakdown.
        
        Args:
            keywords: Search keywords
            job_title: Job title
            job_description: Job description
            job_tags: Job tags
            
        Returns:
            Dictionary with match scores and details
        """
        # Parse keywords
        keyword_list = JobFilters._parse_keywords(keywords)
        if not keyword_list:
            return {'overall_score': 1.0, 'matched_keywords': [], 'missing_keywords': []}
        
        # Prepare text for matching
        title_lower = job_title.lower()
        desc_lower = job_description.lower()
        tags_lower = job_tags.lower()
        all_text = f"{title_lower} {desc_lower} {tags_lower}"
        
        # Track matches
        matched_keywords = []
        missing_keywords = []
        title_matches = []
        desc_matches = []
        
        # Check each keyword
        for keyword in keyword_list:
            keyword_variations = KeywordMatcher._get_keyword_variations(keyword)
            
            found = False
            for variation in keyword_variations:
                if variation in all_text:
                    matched_keywords.append(keyword)
                    found = True
                    
                    # Track where it was found
                    if variation in title_lower:
                        title_matches.append(keyword)
                    if variation in desc_lower:
                        desc_matches.append(keyword)
                    break
            
            if not found:
                missing_keywords.append(keyword)
        
        # Calculate scores
        overall_score = len(matched_keywords) / len(keyword_list) if keyword_list else 1.0
        title_score = len(title_matches) / len(keyword_list) if keyword_list else 0.0
        
        return {
            'overall_score': overall_score,
            'title_score': title_score,
            'matched_keywords': matched_keywords,
            'missing_keywords': missing_keywords,
            'title_matches': title_matches,
            'description_matches': desc_matches,
            'total_keywords': len(keyword_list)
        }
    
    @staticmethod
    def _get_keyword_variations(keyword: str) -> List[str]:
        """Get variations of a keyword for matching."""
        variations = [keyword]
        
        # Add common variations
        if 'python' in keyword:
            variations.extend(['py', 'python3'])
        elif 'javascript' in keyword:
            variations.extend(['js', 'node.js', 'nodejs'])
        elif 'react' in keyword:
            variations.extend(['reactjs', 'react.js'])
        elif 'vue' in keyword:
            variations.extend(['vuejs', 'vue.js'])
        elif 'angular' in keyword:
            variations.extend(['angularjs'])
        
        # Add plural/singular variations
        if keyword.endswith('s') and len(keyword) > 3:
            variations.append(keyword[:-1])
        elif not keyword.endswith('s'):
            variations.append(keyword + 's')
        
        return variations
    
    @staticmethod
    def extract_skills_from_text(text: str) -> Set[str]:
        """Extract technical skills from text."""
        skills = set()
        
        # Common technical skills patterns
        skill_patterns = [
            r'\b(?:Python|Java|JavaScript|TypeScript|C\+\+|C#|PHP|Ruby|Go|Rust|Swift|Kotlin)\b',
            r'\b(?:React|Vue|Angular|Django|Flask|Spring|Laravel|Rails)\b',
            r'\b(?:SQL|MySQL|PostgreSQL|MongoDB|Redis|Elasticsearch)\b',
            r'\b(?:AWS|Azure|GCP|Docker|Kubernetes|Jenkins|Git)\b',
            r'\b(?:HTML|CSS|SASS|LESS|Bootstrap|Tailwind)\b',
            r'\b(?:REST|GraphQL|API|Microservices|DevOps|CI/CD)\b'
        ]
        
        text_lower = text.lower()
        
        for pattern in skill_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            skills.update(match.lower() for match in matches)
        
        return skills 