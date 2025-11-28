"""ADK tools for Bangumi and Anitabi API queries.

These tools are used by both LlmAgents (as FunctionTools) and the root agent.
Extracted to avoid circular imports between agent.py and sub-agents.
"""

from clients.bangumi import BangumiClient
from clients.anitabi import AnitabiClient

# Initialize clients
_bangumi_client = BangumiClient()
_anitabi_client = AnitabiClient()


async def search_bangumi_subjects(keyword: str) -> dict:
    """
    Search Bangumi subjects (anime) by keyword.

    Args:
        keyword: Search keyword for bangumi name.

    Returns:
        {"keyword": keyword, "results": [...bangumi subjects from API...]}
    """
    results = await _bangumi_client.search_subject(
        keyword=keyword,
        subject_type=BangumiClient.TYPE_ANIME,
    )
    return {"keyword": keyword, "results": results}


async def get_bangumi_subject(subject_id: int) -> dict:
    """
    Get detailed Bangumi subject information by ID.

    Args:
        subject_id: Bangumi subject ID.

    Returns:
        {"subject_id": subject_id, "subject": {...}}
    """
    subject = await _bangumi_client.get_subject(subject_id)
    return {"subject_id": subject_id, "subject": subject}


async def get_anitabi_points(bangumi_id: str) -> dict:
    """
    Get Anitabi pilgrimage points for a specific bangumi.

    Args:
        bangumi_id: Bangumi identifier used by Anitabi.

    Returns:
        {"bangumi_id": bangumi_id, "points": [...flattened point dicts...]}
    """
    points = await _anitabi_client.get_bangumi_points(bangumi_id)

    return {
        "bangumi_id": bangumi_id,
        "points": [
            {
                "id": p.id,
                "name": p.name,
                "cn_name": p.cn_name,
                "lat": p.coordinates.latitude,
                "lng": p.coordinates.longitude,
                "episode": p.episode,
                "time_seconds": p.time_seconds,
                "screenshot_url": p.screenshot_url,
                "address": p.address,
            }
            for p in points
        ],
    }


async def search_anitabi_bangumi_near_station(
    station_name: str,
    radius_km: float = 5.0,
) -> dict:
    """
    Search Anitabi for bangumi near a station.

    Args:
        station_name: Station name in Japanese.
        radius_km: Search radius in kilometers.

    Returns:
        {"station": {...}, "bangumi_list": [...], "radius_km": radius_km}
    """
    station = await _anitabi_client.get_station_info(station_name)
    bangumi_list = await _anitabi_client.search_bangumi(
        station=station,
        radius_km=radius_km,
    )

    return {
        "station": {
            "name": station.name,
            "lat": station.coordinates.latitude,
            "lng": station.coordinates.longitude,
            "city": station.city,
            "prefecture": station.prefecture,
        },
        "bangumi_list": [
            {
                "id": b.id,
                "title": b.title,
                "cn_title": b.cn_title,
                "cover_url": b.cover_url,
                "points_count": b.points_count,
                "distance_km": b.distance_km,
            }
            for b in bangumi_list
        ],
        "radius_km": radius_km,
    }
