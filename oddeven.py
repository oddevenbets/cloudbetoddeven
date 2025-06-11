import requests
import uuid
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Constants
API_KEY = "eyJhbGciOiJSUzI1NiIsImtpZCI6IkhKcDkyNnF3ZXBjNnF3LU9rMk4zV05pXzBrRFd6cEdwTzAxNlRJUjdRWDAiLCJ0eXAiOiJKV1QifQ.eyJhY2Nlc3NfdGllciI6InRyYWRpbmciLCJleHAiOjIwNDYyODAxNjgsImlhdCI6MTczMDkyMDE2OCwianRpIjoiY2E1MzQ1ODItNmYzNC00MzcyLWE0ZmYtZDg2MTljOWUyYjNlIiwic3ViIjoiZWFjNTgwZDctMTQ5MS00MDc2LTgwYzgtODRkMGE1ODgzMTdkIiwidGVuYW50IjoiY2xvdWRiZXQiLCJ1dWlkIjoiZWFjNTgwZDctMTQ5MS00MDc2LTgwYzgtODRkMGE1ODgzMTdkIn0.HOVEaLMU0im_co-fVl8kavcd9_ISgePju7pL6mDCb5CLwb7RloA7sgGnfJ7ZQ2vsXzGQJ9uO_1lidi0aliOy63KC_iP0iUs5qsdaXyurKZvTPUSXewycVc5fFhj0pNC1mflRVpq8NpJ-5h_D03kbnzzsaBJWkHe0I4Pd4h9qCpJNwhWKHrHDnyQt6cUK-vNIvsZjSpB5LAVCXDyva3zwn3Lup1iDIpqIkKYEhleObXhPvZC0_iyH2TTJjtRtaYjZRyVI7ddPd5jM8na2j7UqIUzoNTSWb5aL3iZWSXovBkVgfVmWf-7_G7KOf9Q569IDHX2eZjwfeQ0tttKBQtVX-Q"
FEED_API_URL = "https://sports-api.cloudbet.com/pub/v2/odds"
TRADING_API_URL = "https://sports-api.cloudbet.com/pub/v3/bets"

headers = {
    "X-API-Key": API_KEY,
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# Global variables
active_bets = {}
executor = ThreadPoolExecutor(max_workers=10)

def get_all_live_basketball_events():
    """Get all live basketball events with Odd/Even markets"""
    print("\nSearching for all live basketball events...")
    params = {
        "sport": "basketball",
        "live": "true",
        "markets": "basketball.odd_even"
    }

    try:
        response = requests.get(
            f"{FEED_API_URL}/events",
            headers=headers,
            params=params,
            timeout=10
        )
        response.raise_for_status()
        
        events = []
        data = response.json()
        
        if not data.get("competitions"):
            print("No live basketball games available.")
            return events

        for competition in data["competitions"]:
            for event in competition["events"]:
                if event.get('status', '').lower() == 'trading_live':
                    selections = get_odd_even_market(event['id'])
                    if selections:
                        # Filter selections to only include those with odds > 2.04
                        filtered_selections = [s for s in selections if float(s['price']) > 1.84]
                        if filtered_selections:
                            events.append({
                                'event_id': event['id'],
                                'event_name': f"{event['home']['name']} vs {event['away']['name']}",
                                'competition': competition['name'],
                                'selections': filtered_selections
                            })
        
        print(f"Found {len(events)} live events with Odd/Even markets and odds > 1.84")
        return events

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching events: {e}")
        return []

def get_odd_even_market(event_id):
    """Get Odd/Even market selections for an event"""
    params = {"markets": "basketball.odd_even"}
    try:
        response = requests.get(
            f"{FEED_API_URL}/events/{event_id}",
            headers=headers,
            params=params,
            timeout=5
        )
        response.raise_for_status()
        data = response.json()
       
        if "markets" in data and "basketball.odd_even" in data["markets"]:
            market = data["markets"]["basketball.odd_even"]
            if "submarkets" in market:
                for submarket in market["submarkets"].values():
                    return submarket["selections"]
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching market: {e}")
        return None

def place_bet(event_info, stake_per_side=1.0):
    """Place bet on a single selection with odds > 1.84"""
    bets_placed = []
    currency = "PLAY_EUR"  # Manually set to PLAY_EUR
    
    for selection in event_info['selections']:
        side = selection['outcome']
        price = selection['price']
        
        bet_payload = {
            "eventId": str(event_info['event_id']),
            "marketUrl": f"basketball.odd_even/{side}",
            "price": str(price),
            "stake": str(stake_per_side),
            "currency": currency,
            "referenceId": str(uuid.uuid4()),
            "acceptPriceChange": "BETTER"
        }

        try:
            response = requests.post(
                f"{TRADING_API_URL}/place",
                headers=headers,
                json=bet_payload,
                timeout=10
            )
            response.raise_for_status()
            bet_response = response.json()
            bets_placed.append(bet_response)

            # Write event ID to events.txt
            with open("events.txt", "a") as f:
                f.write(f"{event_info['event_id']}\n")

            
            print(f"\n🎯 Placed {side} bet:")
            print(f"  Event: {event_info['event_name']}")
            print(f"  Stake: {stake_per_side} {currency}")
            print(f"  Price: {price}")
            print(f"  Ref ID: {bet_response['referenceId']}")
            print(f"  Status: {bet_response['status']}")
            
            # Start monitoring this bet
            if bet_response['status'] == 'PENDING_ACCEPTANCE':
                active_bets[bet_response['referenceId']] = {
                    'event': event_info['event_name'],
                    'side': side,
                    'stake': stake_per_side,
                    'currency': currency
                }
                executor.submit(monitor_bet, bet_response['referenceId'])
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to place {side} bet on {event_info['event_name']}: {e}")
    
    return bets_placed

def check_bet_status(reference_id):
    """Check current status of a bet"""
    try:
        response = requests.get(
            f"{TRADING_API_URL}/{reference_id}/status",
            headers=headers,
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error checking status for {reference_id}: {e}")
        return None

def monitor_bet(reference_id, max_checks=30, interval=10):
    """Continuously monitor bet status until resolution"""
    terminal_states = ['ACCEPTED', 'REJECTED', 'WIN', 'LOSS', 'PUSH', 
                      'MARKET_SUSPENDED', 'INSUFFICIENT_FUNDS', 'CANCELLED']
    
    for i in range(max_checks):
        status = check_bet_status(reference_id)
        if not status:
            time.sleep(interval)
            continue
        
        if status['status'] in terminal_states:
            print(f"\n✅ Bet {reference_id} resolved:")
            print(f"  Event: {active_bets.get(reference_id, {}).get('event', 'Unknown')}")
            print(f"  Side: {active_bets.get(reference_id, {}).get('side', 'Unknown')}")
            print(f"  Final Status: {status['status']}")
            if reference_id in active_bets:
                del active_bets[reference_id]
            return
        
        time.sleep(interval)
    
    print(f"\n⚠️ Bet {reference_id} monitoring ended without resolution")
    if reference_id in active_bets:
        del active_bets[reference_id]

def load_existing_event_ids():
    """Load event IDs from events.txt to avoid duplicate bets."""
    try:
        with open("events.txt", "r") as f:
            return set(line.strip() for line in f)
    except FileNotFoundError:
        return set()

def main():
    print(f"\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load previously bet event IDs
    existing_event_ids = load_existing_event_ids()
    
    # Find all live events
    events = get_all_live_basketball_events()
    if not events:
        return

    # Filter out events that were already bet on
    events = [event for event in events if str(event['event_id']) not in existing_event_ids]

    if not events:
        print("✅ No new events to place bets on")
        return
    
    # Set fixed stake amount (1.0 PLAY_EUR)
    stake_per_side = 1.0
    
    print(f"\n💵 Betting Parameters:")
    print(f"  Currency: PLAY_EUR")
    print(f"  Stake per side: {stake_per_side:.2f}")
    print(f"  Total new events: {len(events)}")
    print(f"  Estimated total stake: {stake_per_side*len(events):.2f} PLAY_EUR")
    
    # Place bets on new events only
    print("\n🚀 Placing bets on new events...")
    for event in events:
        place_bet(event, stake_per_side)

    # Keep monitoring until all bets are resolved
    print("\n🔍 Monitoring active bets... (Ctrl+C to exit)")
    try:
        while active_bets:
            print(f"\nActive bets remaining: {len(active_bets)}")
            for ref_id, bet in list(active_bets.items()):
                print(f"  - {ref_id}: {bet['event']} ({bet['side']}) {bet['stake']} {bet['currency']}")
            time.sleep(30)
    except KeyboardInterrupt:
        print("\n👋 Exiting monitor - your bets will continue processing")
    
    executor.shutdown(wait=False)

if __name__ == "__main__":
    main()