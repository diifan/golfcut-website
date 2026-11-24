"""Conservative, explainable intent routing; unknown is never an irrelevance verdict.

Routing identifies a content requirement, not permission to publish or a SERP claim.
Evidence URLs are hints only. Provenance, source verification and editorial gates follow.
"""
import re
from urllib.parse import urlsplit

VERSION='2026-11-24.1'
def route(keyword,url,sport):
    word=' '.join(keyword.casefold().split());path=urlsplit(url).path.casefold()
    def has(pattern):return bool(re.search(pattern,word))
    def result(kind,reason,state='content_candidate'):
        return dict(page_type=kind,routing_state=state,routing_reason=reason,routing_version=VERSION)
    if has(r'\b(net worth|girlfriend|boyfriend|wife|husband|obituary|salary|wedding|betting|prizepicks|odds|casino)\b'):
        return result('out_of_scope','Explicit personal-life, gambling or non-product intent','out_of_scope')
    others=r'\b(basketball|football|soccer|baseball|pickleball|'+('golf' if sport=='tennis' else 'tennis')+r')\b'
    if has(others):return result('cross_sport_review','Cross-sport query needs human disambiguation','needs_review')
    if has(r'\b(elbow|injury|injuries|pain|brace|rehab|treatment)\b'):
        return result('health','Medical claims need specialist sources','specialist_review')
    if has(r'\b(live|scores|results|schedule|tickets|rankings|ranking|prediction|predictions)\b') or '/matches/' in path:
        return result('event_results','Requires dated event data and an update policy','freshness_required')
    if has(r'\b(dimension|dimensions|width|length|size|diagram|layout|measurement|measurements)\b') and has(r'\b(court|courts|net)\b'):
        return result('court_reference','Court layout or measurement question')
    if has(r'\b(rule|rules|scoring|tiebreak|tiebreaker|tie break|deuce|advantage|love|fault|let serve)\b'):
        return result('rules_explainer','Rules or scoring question; exact format must be sourced')
    if has(r'\b(grip|grips)\b') and not has(r'\b(size|sizing|overgrip|sweaty|buy|tape)\b'):
        return result('technique_guide','Grip technique or grip comparison')
    if has(r'\b(strategy|strategies|tactics|tactical|pusher|pushers|positioning)\b|how to (win|beat)\b'):
        return result('tactics_guide','Tactical decision or opponent strategy')
    if has(r'\b(drills?|practice|practise|training|beginners?|learn|learning)\b|how to (start|play)\b'):
        return result('practice_plan','Learning or practice planning question')
    if has(r'\b(apps?|software|camera|cameras|recording|filming|editing|tracer|tracker|tracking|videos?|highlights?)\b'):
        return result('tool_guide','Tool selection or video creation workflow')
    if has(r'\b(serves?|serving|forehand|backhand|volleys?|rallies|rally|topspin|slice|footwork|overhead|lobs?|lobbing|drop shot|swing|chipping|bunker|pitching|putting)\b'):
        return result('technique_guide','Sport technique question')
    if has(r'\b(racquets?|rackets?|strings?|tension|shoes?|balls?|irons?|drivers?|wedges?|putters?|sensors?|gps|rangefinder|arccos)\b') or '/gear/' in path:
        return result('equipment_guide','Equipment decision; requires item-specific facts')
    if '/courses' in path or has(r'\b(golf course|golf courses|country club|driving range)\b'):
        return result('location_guide','Location-specific information must be checked','freshness_required')
    if '/tournaments/' in path:
        return result('event_results','Tournament destination; no evergreen intent confirmed','freshness_required')
    if '/players-rankings/' in path or '/player' in path or 'player.cgi' in path or 'wplayer.cgi' in path:
        return result('player_reference','Player identity requires editorial relevance review','needs_review')
    return result('unresolved','No confident intent; preserve for review, do not discard','needs_review')
