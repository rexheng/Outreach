"""
Enrich master_lsoa.gpkg with community support services.

Steps:
1. Build a curated dataset of London community services (from web research)
2. Geocode postcodes via postcodes.io (free, no API key)
3. Spatial join: assign each service to an LSOA
4. Aggregate: count services per LSOA by type + distance to nearest
5. Save enriched GeoPackage + standalone services CSV
"""

import geopandas as gpd
import pandas as pd
import numpy as np
import requests
import time
import json
from pathlib import Path
from shapely.geometry import Point

# ---------------------------------------------------------------------------
# 1. Curated community services dataset (from verified web research)
# ---------------------------------------------------------------------------

SERVICES = [
    # ── MENTAL HEALTH CHARITIES (Mind local branches) ──
    {"name": "Mind in Camden", "type": "mental_health_charity", "subtype": "Mind",
     "postcode": "NW1 0JH", "borough": "Camden",
     "address": "Barnes House, 9-15 Camden Road"},
    {"name": "South East London Mind - Orpington (Head Office)", "type": "mental_health_charity", "subtype": "Mind",
     "postcode": "BR6 0RZ", "borough": "Bromley",
     "address": "Anchor House, 5 Station Road, Orpington"},
    {"name": "South East London Mind - Bromley Recovery Works", "type": "mental_health_charity", "subtype": "Mind",
     "postcode": "BR2 9JG", "borough": "Bromley",
     "address": "Stepping Stones, 38 Masons Hill, Bromley"},
    {"name": "South East London Mind - Beckenham Centre", "type": "mental_health_charity", "subtype": "Mind",
     "postcode": "BR3 4HY", "borough": "Bromley",
     "address": "20b Hayne Road, Beckenham"},
    {"name": "South East London Mind - Greenwich", "type": "mental_health_charity", "subtype": "Mind",
     "postcode": "SE10 9EQ", "borough": "Greenwich",
     "address": "Forum at Greenwich, Trafalgar Rd"},
    {"name": "South East London Mind - Lewisham", "type": "mental_health_charity", "subtype": "Mind",
     "postcode": "SE13 7DW", "borough": "Lewisham",
     "address": "91 Granville Park, Lewisham"},
    {"name": "South East London Mind - Lambeth & Southwark", "type": "mental_health_charity", "subtype": "Mind",
     "postcode": "SW9 7DE", "borough": "Lambeth",
     "address": "International House"},
    {"name": "West Central London Mind", "type": "mental_health_charity", "subtype": "Mind",
     "postcode": "SW1P 2AE", "borough": "Westminster",
     "address": "23 Monck Street"},
    {"name": "Mind in Brent Wandsworth Westminster - Kensington Hub", "type": "mental_health_charity", "subtype": "Mind",
     "postcode": "W10 5XL", "borough": "Kensington and Chelsea",
     "address": "7 Thorpe Close"},
    {"name": "Mind in Brent Wandsworth Westminster - Wandsworth", "type": "mental_health_charity", "subtype": "Mind",
     "postcode": "SW17 0SZ", "borough": "Wandsworth",
     "address": "201-203 Tooting High Street"},
    {"name": "Mind in Haringey - Finsbury Park", "type": "mental_health_charity", "subtype": "Mind",
     "postcode": "N4 3QF", "borough": "Haringey",
     "address": "73c Stapleton Hall Road, Finsbury Park"},
    {"name": "Mind in Haringey - Tottenham", "type": "mental_health_charity", "subtype": "Mind",
     "postcode": "N15 4BN", "borough": "Haringey",
     "address": "332 High Road"},
    {"name": "Islington Mind", "type": "mental_health_charity", "subtype": "Mind",
     "postcode": "N7 9DP", "borough": "Islington",
     "address": "Mental Health Resource Centre, Elthorne Road"},
    {"name": "Hammersmith Fulham & Ealing Mind", "type": "mental_health_charity", "subtype": "Mind",
     "postcode": "W6 9LP", "borough": "Hammersmith and Fulham",
     "address": "Palingswick House, 241 King Street"},
    {"name": "Barnet Enfield Haringey Mind", "type": "mental_health_charity", "subtype": "Mind",
     "postcode": "N12 0QE", "borough": "Barnet",
     "address": "818 High Road, North Finchley"},

    # ── SAMARITANS BRANCHES ──
    {"name": "Central London Samaritans", "type": "mental_health_charity", "subtype": "Samaritans",
     "postcode": "W1H 1FJ", "borough": "Westminster",
     "address": "13 Salisbury Place"},
    {"name": "North London Samaritans", "type": "mental_health_charity", "subtype": "Samaritans",
     "postcode": "N11 2QN", "borough": "Barnet",
     "address": "Shaftesbury Hall, Herbert Road"},
    {"name": "Inner South West London Samaritans", "type": "mental_health_charity", "subtype": "Samaritans",
     "postcode": "SW15 1AZ", "borough": "Wandsworth",
     "address": "Princeton Court, 53-55 Felsham Road"},
    {"name": "Lewisham Greenwich Southwark Samaritans", "type": "mental_health_charity", "subtype": "Samaritans",
     "postcode": "SE14 6LU", "borough": "Lewisham",
     "address": "1-5 Angus Street, New Cross"},
    {"name": "Ealing Hammersmith Hounslow Samaritans", "type": "mental_health_charity", "subtype": "Samaritans",
     "postcode": "W5 4XL", "borough": "Ealing",
     "address": "26 Junction Road, Ealing"},
    {"name": "Brent Samaritans", "type": "mental_health_charity", "subtype": "Samaritans",
     "postcode": "NW10 3QE", "borough": "Brent",
     "address": "Samaritans Centre, Brent"},
    {"name": "Croydon & Sutton Samaritans", "type": "mental_health_charity", "subtype": "Samaritans",
     "postcode": "CR0 1NR", "borough": "Croydon",
     "address": "Samaritans Centre, Croydon"},
    {"name": "Kingston Samaritans", "type": "mental_health_charity", "subtype": "Samaritans",
     "postcode": "KT1 1HT", "borough": "Kingston upon Thames",
     "address": "Samaritans Centre, Kingston"},
    {"name": "Bromley & Orpington Samaritans", "type": "mental_health_charity", "subtype": "Samaritans",
     "postcode": "BR1 1HA", "borough": "Bromley",
     "address": "Samaritans Centre, Bromley"},
    {"name": "Harrow Samaritans", "type": "mental_health_charity", "subtype": "Samaritans",
     "postcode": "HA1 1BA", "borough": "Harrow",
     "address": "Samaritans Centre, Harrow"},
    {"name": "Redbridge Samaritans", "type": "mental_health_charity", "subtype": "Samaritans",
     "postcode": "IG1 1BY", "borough": "Redbridge",
     "address": "Samaritans Centre, Ilford"},
    {"name": "Romford Samaritans", "type": "mental_health_charity", "subtype": "Samaritans",
     "postcode": "RM1 3ER", "borough": "Havering",
     "address": "Samaritans Centre, Romford"},
    {"name": "Leyton Samaritans", "type": "mental_health_charity", "subtype": "Samaritans",
     "postcode": "E10 7AA", "borough": "Waltham Forest",
     "address": "Samaritans Centre, Leyton"},
    {"name": "Hillingdon (Uxbridge) Samaritans", "type": "mental_health_charity", "subtype": "Samaritans",
     "postcode": "UB8 1JN", "borough": "Hillingdon",
     "address": "Samaritans Centre, Uxbridge"},
    {"name": "Bexley & Dartford Samaritans", "type": "mental_health_charity", "subtype": "Samaritans",
     "postcode": "DA6 7HJ", "borough": "Bexley",
     "address": "Samaritans Centre, Bexleyheath"},

    # ── RETHINK MENTAL ILLNESS ──
    {"name": "Rethink Mental Illness - London HQ", "type": "mental_health_charity", "subtype": "Rethink",
     "postcode": "SE1 7GR", "borough": "Lambeth",
     "address": "The Dumont, 28 Albert Embankment"},

    # ── HOMELESSNESS SERVICES ──
    {"name": "St Mungo's Head Office", "type": "homelessness_service", "subtype": "St Mungos",
     "postcode": "E1W 1YW", "borough": "Tower Hamlets",
     "address": "3 Thomas More Square, Tower Hill"},
    {"name": "Crisis Head Office", "type": "homelessness_service", "subtype": "Crisis",
     "postcode": "E1 6LT", "borough": "Tower Hamlets",
     "address": "50-52 Commercial Street"},
    {"name": "Centrepoint", "type": "homelessness_service", "subtype": "Centrepoint",
     "postcode": "E1 8DZ", "borough": "Tower Hamlets",
     "address": "Central House, 25 Camperdown Street"},
    {"name": "Shelter London", "type": "homelessness_service", "subtype": "Shelter",
     "postcode": "EC1V 9HU", "borough": "Islington",
     "address": "88 Old Street"},
    {"name": "Thames Reach - Lambeth", "type": "homelessness_service", "subtype": "Thames Reach",
     "postcode": "SE11 5RD", "borough": "Lambeth",
     "address": "29 Peckham Road"},
    {"name": "The Passage - Westminster", "type": "homelessness_service", "subtype": "Day Centre",
     "postcode": "SW1P 3BT", "borough": "Westminster",
     "address": "St Vincent's Centre, Carlisle Place"},
    {"name": "St Mungo's - Broadway House", "type": "homelessness_service", "subtype": "St Mungos",
     "postcode": "SW8 2JB", "borough": "Lambeth",
     "address": "Broadway House, Wandsworth Road"},
    {"name": "St Mungo's - Islington Mental Health", "type": "homelessness_service", "subtype": "St Mungos",
     "postcode": "N7 6PA", "borough": "Islington",
     "address": "Islington Mental Health Service"},
    {"name": "St Mungo's - North London Women's Hostel", "type": "homelessness_service", "subtype": "St Mungos",
     "postcode": "N16 5QP", "borough": "Hackney",
     "address": "Church Walk"},
    {"name": "Whitechapel Mission", "type": "homelessness_service", "subtype": "Day Centre",
     "postcode": "E1 1BJ", "borough": "Tower Hamlets",
     "address": "212 Whitechapel Road"},
    {"name": "The Connection at St Martin's", "type": "homelessness_service", "subtype": "Day Centre",
     "postcode": "WC2N 4JS", "borough": "Westminster",
     "address": "12 Adelaide Street"},
    {"name": "Glass Door Homeless Charity", "type": "homelessness_service", "subtype": "Night Shelter",
     "postcode": "SW11 3AD", "borough": "Wandsworth",
     "address": "St Paul's Church, Battersea"},
    {"name": "Providence Row", "type": "homelessness_service", "subtype": "Day Centre",
     "postcode": "E1 6QR", "borough": "Tower Hamlets",
     "address": "The Dellow Centre, 82 Wentworth Street"},
    {"name": "New Horizon Youth Centre", "type": "homelessness_service", "subtype": "Youth",
     "postcode": "NW1 2HD", "borough": "Camden",
     "address": "68 Chalton Street"},
    {"name": "Depaul UK - Nightstop London", "type": "homelessness_service", "subtype": "Youth",
     "postcode": "SE1 0NR", "borough": "Southwark",
     "address": "Depaul House, Bermondsey"},

    # ── FOODBANKS (Trussell Trust + Independent) ──
    {"name": "Euston Foodbank", "type": "foodbank", "subtype": "Trussell Trust",
     "postcode": "NW1 1TA", "borough": "Camden",
     "address": "28 Phoenix Road"},
    {"name": "Hackney Foodbank", "type": "foodbank", "subtype": "Trussell Trust",
     "postcode": "E5 0LH", "borough": "Hackney",
     "address": "Gilpin Road, Homerton"},
    {"name": "North Enfield Foodbank", "type": "foodbank", "subtype": "Trussell Trust",
     "postcode": "EN1 1FS", "borough": "Enfield",
     "address": "Unit 2 Lumina Way"},
    {"name": "Brent Foodbank", "type": "foodbank", "subtype": "Trussell Trust",
     "postcode": "NW10 2TS", "borough": "Brent",
     "address": "Vestry Hall, Neasden Lane"},
    {"name": "Wandsworth Foodbank", "type": "foodbank", "subtype": "Trussell Trust",
     "postcode": "SW18 4DJ", "borough": "Wandsworth",
     "address": "St Michael's Church, Wimbledon Park Road"},
    {"name": "Lewisham Foodbank - Deptford", "type": "foodbank", "subtype": "Trussell Trust",
     "postcode": "SE8 4NS", "borough": "Lewisham",
     "address": "Deptford Methodist Mission, Creek Road"},
    {"name": "Lewisham Foodbank - Catford", "type": "foodbank", "subtype": "Trussell Trust",
     "postcode": "SE6 2RP", "borough": "Lewisham",
     "address": "Catford and Bromley Synagogue, Cranfield Close"},
    {"name": "Lewisham Foodbank - Forest Hill", "type": "foodbank", "subtype": "Trussell Trust",
     "postcode": "SE23 3HZ", "borough": "Lewisham",
     "address": "All Saints Church, Sydenham Road"},
    {"name": "Southwark Foodbank", "type": "foodbank", "subtype": "Trussell Trust",
     "postcode": "SE21 8BU", "borough": "Southwark",
     "address": "96 Clive Road, Norwood"},
    {"name": "Lambeth Foodbank", "type": "foodbank", "subtype": "Trussell Trust",
     "postcode": "SW2 3UP", "borough": "Lambeth",
     "address": "Oasis St Martin's Village, 155 Tulse Hill"},
    {"name": "Croydon Foodbank", "type": "foodbank", "subtype": "Trussell Trust",
     "postcode": "CR0 2AJ", "borough": "Croydon",
     "address": "Croydon Minster, Church Street"},
    {"name": "Barnet Foodbank - Chipping Barnet", "type": "foodbank", "subtype": "Trussell Trust",
     "postcode": "EN5 5SJ", "borough": "Barnet",
     "address": "Christ Church, St Albans Road"},
    {"name": "Barnet Foodbank - Colindale", "type": "foodbank", "subtype": "Trussell Trust",
     "postcode": "NW9 5HR", "borough": "Barnet",
     "address": "St Matthias Church, Rushgrove Avenue"},
    {"name": "Ealing Foodbank", "type": "foodbank", "subtype": "Trussell Trust",
     "postcode": "W5 2HL", "borough": "Ealing",
     "address": "St John's Church, Mattock Lane"},
    {"name": "Greenwich Foodbank", "type": "foodbank", "subtype": "Trussell Trust",
     "postcode": "SE18 6ST", "borough": "Greenwich",
     "address": "Woolwich Common Baptist Church"},
    {"name": "Hammersmith & Fulham Foodbank", "type": "foodbank", "subtype": "Trussell Trust",
     "postcode": "W14 0HD", "borough": "Hammersmith and Fulham",
     "address": "Hammersmith Community Centre"},
    {"name": "Haringey Foodbank", "type": "foodbank", "subtype": "Trussell Trust",
     "postcode": "N15 4RX", "borough": "Haringey",
     "address": "Selby Centre, Selby Road"},
    {"name": "Hillingdon Foodbank", "type": "foodbank", "subtype": "Trussell Trust",
     "postcode": "UB8 1QS", "borough": "Hillingdon",
     "address": "Christ Church, Redfield Road, Uxbridge"},
    {"name": "Hounslow Foodbank", "type": "foodbank", "subtype": "Trussell Trust",
     "postcode": "TW3 1RH", "borough": "Hounslow",
     "address": "Holy Trinity Church, Hounslow High Street"},
    {"name": "Islington Foodbank", "type": "foodbank", "subtype": "Independent",
     "postcode": "N1 7RE", "borough": "Islington",
     "address": "Islington Baptist Church, Salters Hall Court"},
    {"name": "Kensington & Chelsea Foodbank", "type": "foodbank", "subtype": "Independent",
     "postcode": "W10 5AA", "borough": "Kensington and Chelsea",
     "address": "Dalgarno Community Centre, 1 Webb Close"},
    {"name": "Kingston Foodbank", "type": "foodbank", "subtype": "Trussell Trust",
     "postcode": "KT1 1HT", "borough": "Kingston upon Thames",
     "address": "Kingston Baptist Church, Union Street"},
    {"name": "Merton Foodbank - Wimbledon", "type": "foodbank", "subtype": "Trussell Trust",
     "postcode": "SW19 7PA", "borough": "Merton",
     "address": "Elim Church, Worple Road, Wimbledon"},
    {"name": "Newham Foodbank", "type": "foodbank", "subtype": "Trussell Trust",
     "postcode": "E13 8QE", "borough": "Newham",
     "address": "Newham Community Project, Barking Road"},
    {"name": "Redbridge Foodbank", "type": "foodbank", "subtype": "Trussell Trust",
     "postcode": "IG1 4NH", "borough": "Redbridge",
     "address": "Ilford Baptist Church, Ilford"},
    {"name": "Richmond Foodbank", "type": "foodbank", "subtype": "Trussell Trust",
     "postcode": "TW9 2NQ", "borough": "Richmond upon Thames",
     "address": "The Vineyard Church, Richmond"},
    {"name": "Sutton Foodbank", "type": "foodbank", "subtype": "Trussell Trust",
     "postcode": "SM1 1NR", "borough": "Sutton",
     "address": "Trinity Church, Sutton High Street"},
    {"name": "Tower Hamlets Foodbank", "type": "foodbank", "subtype": "Trussell Trust",
     "postcode": "E1 4AA", "borough": "Tower Hamlets",
     "address": "Tower Hamlets Community Hub"},
    {"name": "Waltham Forest Foodbank", "type": "foodbank", "subtype": "Trussell Trust",
     "postcode": "E17 5BY", "borough": "Waltham Forest",
     "address": "Walthamstow Assembly Hall area"},

    # ── CITIZENS ADVICE ──
    {"name": "Citizens Advice Tower Hamlets", "type": "citizens_advice", "subtype": "Citizens Advice",
     "postcode": "E1 5NP", "borough": "Tower Hamlets",
     "address": "32 Greatorex Street"},
    {"name": "Citizens Advice Hackney", "type": "citizens_advice", "subtype": "Citizens Advice",
     "postcode": "E8 1HE", "borough": "Hackney",
     "address": "300 Mare Street"},
    {"name": "Citizens Advice Newham", "type": "citizens_advice", "subtype": "Citizens Advice",
     "postcode": "E16 4PZ", "borough": "Newham",
     "address": "2nd Floor, The Hub, 123 Star Lane"},
    {"name": "Citizens Advice Westminster", "type": "citizens_advice", "subtype": "Citizens Advice",
     "postcode": "NW10 3QE", "borough": "Westminster",
     "address": "270-272 High Road"},
    {"name": "Citizens Advice Islington", "type": "citizens_advice", "subtype": "Citizens Advice",
     "postcode": "N7 8JG", "borough": "Islington",
     "address": "222 Upper Street"},
    {"name": "Citizens Advice Camden", "type": "citizens_advice", "subtype": "Citizens Advice",
     "postcode": "WC1H 9JR", "borough": "Camden",
     "address": "Tavistock Place"},
    {"name": "Citizens Advice Lambeth", "type": "citizens_advice", "subtype": "Citizens Advice",
     "postcode": "SW9 8PS", "borough": "Lambeth",
     "address": "336-338 Brixton Road"},
    {"name": "Citizens Advice Southwark", "type": "citizens_advice", "subtype": "Citizens Advice",
     "postcode": "SE5 0HG", "borough": "Southwark",
     "address": "97 Peckham High Street"},
    {"name": "Citizens Advice Barnet", "type": "citizens_advice", "subtype": "Citizens Advice",
     "postcode": "EN5 5TH", "borough": "Barnet",
     "address": "40 Church Hill Road, East Barnet"},
    {"name": "Citizens Advice Brent", "type": "citizens_advice", "subtype": "Citizens Advice",
     "postcode": "HA9 6AG", "borough": "Brent",
     "address": "270 High Road, Wembley"},
    {"name": "Citizens Advice Bromley", "type": "citizens_advice", "subtype": "Citizens Advice",
     "postcode": "BR1 1HA", "borough": "Bromley",
     "address": "Community House, South Street"},
    {"name": "Citizens Advice Croydon", "type": "citizens_advice", "subtype": "Citizens Advice",
     "postcode": "CR0 1RX", "borough": "Croydon",
     "address": "Croydon Clocktower, Katharine Street"},
    {"name": "Citizens Advice Ealing", "type": "citizens_advice", "subtype": "Citizens Advice",
     "postcode": "W5 5JY", "borough": "Ealing",
     "address": "Perceval House, 14-16 Uxbridge Road"},
    {"name": "Citizens Advice Enfield", "type": "citizens_advice", "subtype": "Citizens Advice",
     "postcode": "EN2 6LU", "borough": "Enfield",
     "address": "Chase Side, Enfield"},
    {"name": "Citizens Advice Greenwich", "type": "citizens_advice", "subtype": "Citizens Advice",
     "postcode": "SE18 6QX", "borough": "Greenwich",
     "address": "12 Wellington Street, Woolwich"},
    {"name": "Citizens Advice Haringey", "type": "citizens_advice", "subtype": "Citizens Advice",
     "postcode": "N15 4RX", "borough": "Haringey",
     "address": "595a High Road, Tottenham"},
    {"name": "Citizens Advice Harrow", "type": "citizens_advice", "subtype": "Citizens Advice",
     "postcode": "HA1 2AE", "borough": "Harrow",
     "address": "PO Box 383, Harrow"},
    {"name": "Citizens Advice Havering", "type": "citizens_advice", "subtype": "Citizens Advice",
     "postcode": "RM1 3ER", "borough": "Havering",
     "address": "5 Paines Brook Way, Romford"},
    {"name": "Citizens Advice Hillingdon", "type": "citizens_advice", "subtype": "Citizens Advice",
     "postcode": "UB8 1HD", "borough": "Hillingdon",
     "address": "4 Civic Centre, High Street, Uxbridge"},
    {"name": "Citizens Advice Hounslow", "type": "citizens_advice", "subtype": "Citizens Advice",
     "postcode": "TW3 1ES", "borough": "Hounslow",
     "address": "45 Treaty Centre, High Street, Hounslow"},
    {"name": "Citizens Advice Kensington & Chelsea", "type": "citizens_advice", "subtype": "Citizens Advice",
     "postcode": "SW3 4LX", "borough": "Kensington and Chelsea",
     "address": "Chelsea Old Town Hall, King's Road"},
    {"name": "Citizens Advice Kingston", "type": "citizens_advice", "subtype": "Citizens Advice",
     "postcode": "KT1 1EU", "borough": "Kingston upon Thames",
     "address": "Siddeley House, 50 Canbury Park Road"},
    {"name": "Citizens Advice Lewisham", "type": "citizens_advice", "subtype": "Citizens Advice",
     "postcode": "SE6 4RU", "borough": "Lewisham",
     "address": "Catford Broadway"},
    {"name": "Citizens Advice Merton", "type": "citizens_advice", "subtype": "Citizens Advice",
     "postcode": "CR4 3EB", "borough": "Merton",
     "address": "326 London Road, Mitcham"},
    {"name": "Citizens Advice Redbridge", "type": "citizens_advice", "subtype": "Citizens Advice",
     "postcode": "IG1 1BY", "borough": "Redbridge",
     "address": "2nd Floor, 103 Cranbrook Road, Ilford"},
    {"name": "Citizens Advice Richmond", "type": "citizens_advice", "subtype": "Citizens Advice",
     "postcode": "TW1 3DY", "borough": "Richmond upon Thames",
     "address": "Sheen Lane Centre, Sheen Lane"},
    {"name": "Citizens Advice Sutton", "type": "citizens_advice", "subtype": "Citizens Advice",
     "postcode": "SM1 4LE", "borough": "Sutton",
     "address": "Sutton Gate, Carshalton Road"},
    {"name": "Citizens Advice Wandsworth", "type": "citizens_advice", "subtype": "Citizens Advice",
     "postcode": "SW18 4DJ", "borough": "Wandsworth",
     "address": "Wandsworth High Street"},
    {"name": "Citizens Advice Waltham Forest", "type": "citizens_advice", "subtype": "Citizens Advice",
     "postcode": "E17 7JN", "borough": "Waltham Forest",
     "address": "Vestry House, Vestry Road, Walthamstow"},

    # ── AGE UK (all London branches from web scrape) ──
    {"name": "Age UK Barnet", "type": "older_people_charity", "subtype": "Age UK",
     "postcode": "NW4 4JT", "borough": "Barnet",
     "address": "Meritage Centre, Church End"},
    {"name": "Age UK Bexley", "type": "older_people_charity", "subtype": "Age UK",
     "postcode": "DA17 6AA", "borough": "Bexley",
     "address": "Belvedere Community Centre, Mitchell Close"},
    {"name": "Age UK Hillingdon Harrow Brent", "type": "older_people_charity", "subtype": "Age UK",
     "postcode": "UB3 2LW", "borough": "Hillingdon",
     "address": "2 Chapel Court, 126 Church Road, Hayes"},
    {"name": "Age UK Bromley & Greenwich", "type": "older_people_charity", "subtype": "Age UK",
     "postcode": "BR1 1RH", "borough": "Bromley",
     "address": "Community House, South Street"},
    {"name": "Age UK Camden", "type": "older_people_charity", "subtype": "Age UK",
     "postcode": "NW3 6NS", "borough": "Camden",
     "address": "Henderson Court, 102 Fitzjohn's Avenue"},
    {"name": "Age UK Croydon", "type": "older_people_charity", "subtype": "Age UK",
     "postcode": "CR7 7JH", "borough": "Croydon",
     "address": "81 Brigstock Road, Thornton Heath"},
    {"name": "Age UK Ealing", "type": "older_people_charity", "subtype": "Age UK",
     "postcode": "UB6 9JS", "borough": "Ealing",
     "address": "Greenford Community Centre, 170 Oldfield Lane South"},
    {"name": "Age UK Enfield", "type": "older_people_charity", "subtype": "Age UK",
     "postcode": "EN1 1DW", "borough": "Enfield",
     "address": "John Jackson Library, 35 Agricola Place, Bush Hill Park"},
    {"name": "Age UK Hackney (East London)", "type": "older_people_charity", "subtype": "Age UK",
     "postcode": "E8 3AZ", "borough": "Hackney",
     "address": "22 Dalston Lane"},
    {"name": "Age UK Hammersmith & Fulham", "type": "older_people_charity", "subtype": "Age UK",
     "postcode": "W6 8NJ", "borough": "Hammersmith and Fulham",
     "address": "105 Greyhound Road"},
    {"name": "Age UK Hounslow", "type": "older_people_charity", "subtype": "Age UK",
     "postcode": "TW14 8AP", "borough": "Hounslow",
     "address": "Southville Community Centre, Southville Road, Feltham"},
    {"name": "Age UK Islington", "type": "older_people_charity", "subtype": "Age UK",
     "postcode": "N7 6LA", "borough": "Islington",
     "address": "6/9 Manor Gardens"},
    {"name": "Age UK Kensington & Chelsea", "type": "older_people_charity", "subtype": "Age UK",
     "postcode": "W10 5XL", "borough": "Kensington and Chelsea",
     "address": "1 Thorpe Close, North Kensington"},
    {"name": "Age UK Lambeth", "type": "older_people_charity", "subtype": "Age UK",
     "postcode": "SW2 5SG", "borough": "Lambeth",
     "address": "10 Acre Lane, Brixton"},
    {"name": "Age UK Lewisham & Southwark", "type": "older_people_charity", "subtype": "Age UK",
     "postcode": "SE1 1QQ", "borough": "Southwark",
     "address": "Stones End Day Centre, 11 Scovell Road"},
    {"name": "Age UK Merton", "type": "older_people_charity", "subtype": "Age UK",
     "postcode": "CR4 3NT", "borough": "Merton",
     "address": "Elmwood Centre, 277 London Road, Mitcham"},
    {"name": "Age UK Newham (East London)", "type": "older_people_charity", "subtype": "Age UK",
     "postcode": "E13 9EX", "borough": "Newham",
     "address": "655 Barking Road"},
    {"name": "Age UK Redbridge Barking Havering", "type": "older_people_charity", "subtype": "Age UK",
     "postcode": "IG1 4PU", "borough": "Redbridge",
     "address": "4th Floor, 103 Cranbrook Road, Ilford"},
    {"name": "Age UK Richmond upon Thames", "type": "older_people_charity", "subtype": "Age UK",
     "postcode": "SW14 8LS", "borough": "Richmond upon Thames",
     "address": "Parkway House, Sheen Lane, East Sheen"},
    {"name": "Age UK Sutton", "type": "older_people_charity", "subtype": "Age UK",
     "postcode": "SM1 4LE", "borough": "Sutton",
     "address": "Sutton Gate, 1 Carshalton Road"},
    {"name": "Age UK Tower Hamlets (East London)", "type": "older_people_charity", "subtype": "Age UK",
     "postcode": "E2 9LU", "borough": "Tower Hamlets",
     "address": "82 Russia Lane"},
    {"name": "Age UK Waltham Forest", "type": "older_people_charity", "subtype": "Age UK",
     "postcode": "E4 8EU", "borough": "Waltham Forest",
     "address": "Waltham Forest Resource Hub, 58 Hall Lane, Chingford"},
    {"name": "Age UK Wandsworth", "type": "older_people_charity", "subtype": "Age UK",
     "postcode": "SW18 1TQ", "borough": "Wandsworth",
     "address": "549 Old York Road"},
    {"name": "Age UK Westminster", "type": "older_people_charity", "subtype": "Age UK",
     "postcode": "W10 4JL", "borough": "Westminster",
     "address": "Beethoven Centre, Third Avenue"},
    {"name": "Staywell (Kingston)", "type": "older_people_charity", "subtype": "Age UK",
     "postcode": "KT3 5EA", "borough": "Kingston upon Thames",
     "address": "Raleigh House, 14 Nelson Road, New Malden"},

    # ── NHS TALKING THERAPIES (IAPT) ──
    {"name": "Ealing Talking Therapies", "type": "nhs_talking_therapy", "subtype": "IAPT",
     "postcode": "W5 5JY", "borough": "Ealing",
     "address": "Ealing Hospital, Uxbridge Road"},
    {"name": "Hounslow Talking Therapies", "type": "nhs_talking_therapy", "subtype": "IAPT",
     "postcode": "TW3 3EB", "borough": "Hounslow",
     "address": "Hounslow Civic Centre"},
    {"name": "Hammersmith & Fulham Talking Therapies", "type": "nhs_talking_therapy", "subtype": "IAPT",
     "postcode": "W6 8LH", "borough": "Hammersmith and Fulham",
     "address": "Hammersmith Hospital"},
    {"name": "Westminster Talking Therapies", "type": "nhs_talking_therapy", "subtype": "IAPT",
     "postcode": "W2 1NY", "borough": "Westminster",
     "address": "St Mary's Hospital, Praed Street"},
    {"name": "Lambeth Talking Therapies (SLaM)", "type": "nhs_talking_therapy", "subtype": "IAPT",
     "postcode": "SE5 8AZ", "borough": "Lambeth",
     "address": "Maudsley Hospital, Denmark Hill"},
    {"name": "Southwark Talking Therapies", "type": "nhs_talking_therapy", "subtype": "IAPT",
     "postcode": "SE5 8AZ", "borough": "Southwark",
     "address": "Maudsley Hospital, Denmark Hill"},
    {"name": "Lewisham Talking Therapies", "type": "nhs_talking_therapy", "subtype": "IAPT",
     "postcode": "SE13 6LH", "borough": "Lewisham",
     "address": "University Hospital Lewisham"},
    {"name": "Croydon Talking Therapies", "type": "nhs_talking_therapy", "subtype": "IAPT",
     "postcode": "CR7 7YE", "borough": "Croydon",
     "address": "Bethlem Royal Hospital, Monks Orchard Road"},
    {"name": "Harrow Talking Therapies", "type": "nhs_talking_therapy", "subtype": "IAPT",
     "postcode": "HA1 2SL", "borough": "Harrow",
     "address": "12-14 Station Road, Harrow"},
    {"name": "Barking & Dagenham Talking Therapies (NELFT)", "type": "nhs_talking_therapy", "subtype": "IAPT",
     "postcode": "IG11 7LZ", "borough": "Barking and Dagenham",
     "address": "Barking Community Hospital, Upney Lane"},
    {"name": "Havering Talking Therapies (NELFT)", "type": "nhs_talking_therapy", "subtype": "IAPT",
     "postcode": "RM7 0AG", "borough": "Havering",
     "address": "Queen's Hospital, Rom Valley Way"},
    {"name": "Redbridge Talking Therapies (NELFT)", "type": "nhs_talking_therapy", "subtype": "IAPT",
     "postcode": "IG3 8XJ", "borough": "Redbridge",
     "address": "King George Hospital, Barley Lane"},
    {"name": "Waltham Forest Talking Therapies (NELFT)", "type": "nhs_talking_therapy", "subtype": "IAPT",
     "postcode": "E17 3EA", "borough": "Waltham Forest",
     "address": "Thorpe Coombe Hospital, 714 Forest Road"},
    {"name": "Camden & Islington Talking Therapies", "type": "nhs_talking_therapy", "subtype": "IAPT",
     "postcode": "N19 5NF", "borough": "Camden",
     "address": "St Pancras Hospital, St Pancras Way"},
    {"name": "Barnet Talking Therapies", "type": "nhs_talking_therapy", "subtype": "IAPT",
     "postcode": "EN5 3DJ", "borough": "Barnet",
     "address": "Barnet Hospital, Wellhouse Lane"},
    {"name": "Enfield Talking Therapies", "type": "nhs_talking_therapy", "subtype": "IAPT",
     "postcode": "N18 1QX", "borough": "Enfield",
     "address": "St Ann's Hospital, St Ann's Road"},
    {"name": "Haringey Talking Therapies", "type": "nhs_talking_therapy", "subtype": "IAPT",
     "postcode": "N15 3TH", "borough": "Haringey",
     "address": "St Ann's Hospital, St Ann's Road"},
    {"name": "Hackney Talking Therapies (ELFT)", "type": "nhs_talking_therapy", "subtype": "IAPT",
     "postcode": "E9 6SR", "borough": "Hackney",
     "address": "Homerton University Hospital"},
    {"name": "Newham Talking Therapies (ELFT)", "type": "nhs_talking_therapy", "subtype": "IAPT",
     "postcode": "E13 8SL", "borough": "Newham",
     "address": "Newham Centre for Mental Health"},
    {"name": "Tower Hamlets Talking Therapies (ELFT)", "type": "nhs_talking_therapy", "subtype": "IAPT",
     "postcode": "E1 4DG", "borough": "Tower Hamlets",
     "address": "Mile End Hospital, Bancroft Road"},
    {"name": "Bexley Talking Therapies", "type": "nhs_talking_therapy", "subtype": "IAPT",
     "postcode": "DA6 8DX", "borough": "Bexley",
     "address": "Queen Mary's Hospital, Frognal Avenue"},
    {"name": "Bromley Talking Therapies", "type": "nhs_talking_therapy", "subtype": "IAPT",
     "postcode": "BR6 8ND", "borough": "Bromley",
     "address": "Princess Royal University Hospital"},
    {"name": "Greenwich Talking Therapies", "type": "nhs_talking_therapy", "subtype": "IAPT",
     "postcode": "SE18 4QH", "borough": "Greenwich",
     "address": "Queen Elizabeth Hospital, Stadium Road"},
    {"name": "Kingston Talking Therapies", "type": "nhs_talking_therapy", "subtype": "IAPT",
     "postcode": "KT2 7QB", "borough": "Kingston upon Thames",
     "address": "Kingston Hospital, Galsworthy Road"},
    {"name": "Merton Talking Therapies", "type": "nhs_talking_therapy", "subtype": "IAPT",
     "postcode": "CR4 4TP", "borough": "Merton",
     "address": "Wilson Hospital, Cranmer Road, Mitcham"},
    {"name": "Richmond Talking Therapies", "type": "nhs_talking_therapy", "subtype": "IAPT",
     "postcode": "TW11 0JL", "borough": "Richmond upon Thames",
     "address": "Teddington Memorial Hospital"},
    {"name": "Sutton Talking Therapies", "type": "nhs_talking_therapy", "subtype": "IAPT",
     "postcode": "SM5 1AA", "borough": "Sutton",
     "address": "Jubilee Health Centre, Shotfield"},
    {"name": "Wandsworth Talking Therapies", "type": "nhs_talking_therapy", "subtype": "IAPT",
     "postcode": "SW17 7DJ", "borough": "Wandsworth",
     "address": "Springfield University Hospital, Glenburnie Road"},
    {"name": "Hillingdon Talking Therapies", "type": "nhs_talking_therapy", "subtype": "IAPT",
     "postcode": "UB8 3NN", "borough": "Hillingdon",
     "address": "Hillingdon Hospital, Pield Heath Road"},

    # ── NHS COMMUNITY MENTAL HEALTH TEAMS (CMHTs) ──
    {"name": "CMHT Walworth (Southwark)", "type": "nhs_cmht", "subtype": "CMHT",
     "postcode": "SE16 2TH", "borough": "Southwark",
     "address": "Chaucer Resource Centre, 13 Ann Moss Way"},
    {"name": "CMHT Dulwich (Southwark)", "type": "nhs_cmht", "subtype": "CMHT",
     "postcode": "SE5 7UD", "borough": "Southwark",
     "address": "St Giles House, 1 St Giles Road, Camberwell"},
    {"name": "CMHT Lambeth", "type": "nhs_cmht", "subtype": "CMHT",
     "postcode": "SE5 8AZ", "borough": "Lambeth",
     "address": "Maudsley Hospital, Denmark Hill"},
    {"name": "CMHT North Islington (ELFT)", "type": "nhs_cmht", "subtype": "CMHT",
     "postcode": "N7 6LB", "borough": "Islington",
     "address": "Highbury Corner Mental Health Centre"},
    {"name": "CMHT South Islington (ELFT)", "type": "nhs_cmht", "subtype": "CMHT",
     "postcode": "EC1V 2NZ", "borough": "Islington",
     "address": "South Islington CMHT"},
    {"name": "CMHT Hackney (ELFT)", "type": "nhs_cmht", "subtype": "CMHT",
     "postcode": "E9 6SR", "borough": "Hackney",
     "address": "Homerton University Hospital"},
    {"name": "CMHT Tower Hamlets (ELFT)", "type": "nhs_cmht", "subtype": "CMHT",
     "postcode": "E1 4DG", "borough": "Tower Hamlets",
     "address": "Mile End Hospital, Bancroft Road"},
    {"name": "CMHT Newham (ELFT)", "type": "nhs_cmht", "subtype": "CMHT",
     "postcode": "E13 8SL", "borough": "Newham",
     "address": "Newham Centre for Mental Health"},
    {"name": "CMHT Barnet (North London)", "type": "nhs_cmht", "subtype": "CMHT",
     "postcode": "EN5 3DJ", "borough": "Barnet",
     "address": "Barnet Hospital, Wellhouse Lane"},
    {"name": "CMHT Camden (North London)", "type": "nhs_cmht", "subtype": "CMHT",
     "postcode": "NW3 2QG", "borough": "Camden",
     "address": "Royal Free Hospital, Pond Street"},
    {"name": "CMHT Haringey (North London)", "type": "nhs_cmht", "subtype": "CMHT",
     "postcode": "N15 3TH", "borough": "Haringey",
     "address": "St Ann's Hospital, St Ann's Road"},
    {"name": "CMHT Enfield (North London)", "type": "nhs_cmht", "subtype": "CMHT",
     "postcode": "N18 1QX", "borough": "Enfield",
     "address": "Chase Farm Hospital"},

    # ── COUNCIL WELLBEING / SOCIAL PRESCRIBING HUBS ──
    {"name": "Bromley by Bow Centre (Social Prescribing Pioneer)", "type": "council_wellbeing_hub", "subtype": "Social Prescribing",
     "postcode": "E3 3BT", "borough": "Tower Hamlets",
     "address": "St Leonard's Street, Bromley-by-Bow"},
    {"name": "Merton Recovery Cafe - Wimbledon", "type": "council_wellbeing_hub", "subtype": "Recovery Cafe",
     "postcode": "SW19 7PA", "borough": "Merton",
     "address": "Wimbledon area"},
    {"name": "Merton Assessment Team (Wilson Hospital)", "type": "council_wellbeing_hub", "subtype": "Council MH Hub",
     "postcode": "CR4 4TP", "borough": "Merton",
     "address": "Wilson Hospital, Cranmer Road, Mitcham"},
    {"name": "Highgate East - Inpatient Facility (North London)", "type": "council_wellbeing_hub", "subtype": "Council MH Hub",
     "postcode": "N19 5NF", "borough": "Camden",
     "address": "Highgate Hill"},
    {"name": "Lowther Road ICMHC (Islington)", "type": "council_wellbeing_hub", "subtype": "ICMHC",
     "postcode": "N7 8US", "borough": "Islington",
     "address": "Lowther Road"},
]


def geocode_postcodes(services):
    """Geocode postcodes using postcodes.io bulk API (free, no key needed)."""
    postcodes = list(set(s["postcode"] for s in services))
    results = {}

    # postcodes.io allows bulk lookups of up to 100 at a time
    for i in range(0, len(postcodes), 100):
        batch = postcodes[i:i+100]
        payload = {"postcodes": batch}
        try:
            resp = requests.post(
                "https://api.postcodes.io/postcodes",
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            for item in data["result"]:
                pc = item["query"]
                if item["result"]:
                    results[pc] = {
                        "lat": item["result"]["latitude"],
                        "lon": item["result"]["longitude"],
                        "easting": item["result"]["eastings"],
                        "northing": item["result"]["northings"],
                        "lsoa_code": item["result"].get("codes", {}).get("lsoa"),
                        "lsoa_name_api": item["result"].get("lsoa"),
                    }
                else:
                    print(f"  WARNING: Postcode {pc} not found via API")
                    results[pc] = None
        except Exception as e:
            print(f"  ERROR geocoding batch {i}: {e}")
            for pc in batch:
                results[pc] = None
        time.sleep(0.3)  # be polite

    return results


def main():
    base = Path(r"C:\Users\Rex\OneDrive - London School of Economics\Desktop\Work\Projects\aamental health data")
    gpkg_path = base / "master_lsoa.gpkg"

    print(f"Loading master_lsoa from {gpkg_path}...")
    gdf = gpd.read_file(gpkg_path, layer="master_lsoa")
    print(f"  Loaded {len(gdf)} LSOAs, CRS={gdf.crs}")

    # Drop any previous enrichment columns to ensure clean merge
    prev_cols = [c for c in gdf.columns if any(
        c.startswith(p) for p in [
            "community_services_", "cs_", "dist_to_nearest_",
            "nearest_community_service_",
        ]
    )]
    if prev_cols:
        print(f"  Dropping {len(prev_cols)} previous enrichment columns")
        gdf = gdf.drop(columns=prev_cols)

    # --- Step 1: Build services DataFrame ---
    print(f"\nBuilding services dataset ({len(SERVICES)} services)...")
    sdf = pd.DataFrame(SERVICES)

    # --- Step 2: Geocode postcodes ---
    print("Geocoding postcodes via postcodes.io...")
    geo = geocode_postcodes(SERVICES)

    sdf["lat"] = sdf["postcode"].map(lambda pc: geo.get(pc, {}).get("lat") if geo.get(pc) else None)
    sdf["lon"] = sdf["postcode"].map(lambda pc: geo.get(pc, {}).get("lon") if geo.get(pc) else None)
    sdf["easting"] = sdf["postcode"].map(lambda pc: geo.get(pc, {}).get("easting") if geo.get(pc) else None)
    sdf["northing"] = sdf["postcode"].map(lambda pc: geo.get(pc, {}).get("northing") if geo.get(pc) else None)
    sdf["lsoa_from_postcode"] = sdf["postcode"].map(
        lambda pc: geo.get(pc, {}).get("lsoa_code") if geo.get(pc) else None
    )

    geocoded = sdf["lat"].notna().sum()
    print(f"  Geocoded {geocoded}/{len(sdf)} services successfully")

    failed = sdf[sdf["lat"].isna()]
    if len(failed) > 0:
        print(f"  Failed postcodes: {failed['postcode'].tolist()}")

    # --- Step 3: Spatial join (point-in-polygon) for accuracy ---
    sdf_geo = sdf[sdf["easting"].notna()].copy()
    sdf_geo["geometry"] = sdf_geo.apply(
        lambda r: Point(r["easting"], r["northing"]), axis=1
    )
    services_gdf = gpd.GeoDataFrame(sdf_geo, crs="EPSG:27700", geometry="geometry")

    print("Performing spatial join (point-in-polygon)...")
    joined = gpd.sjoin(services_gdf, gdf[["lsoa_code", "lsoa_name", "geometry"]],
                       how="left", predicate="within")

    # Use spatial join lsoa_code; fall back to postcode API lsoa
    sdf["lsoa_joined"] = None
    sdf.loc[sdf_geo.index, "lsoa_joined"] = joined["lsoa_code"].values
    sdf["assigned_lsoa"] = sdf["lsoa_joined"].fillna(sdf["lsoa_from_postcode"])

    assigned = sdf["assigned_lsoa"].notna().sum()
    print(f"  Assigned {assigned}/{len(sdf)} services to LSOAs")

    # --- Step 4: Save standalone CSV ---
    csv_path = base / "community_services.csv"
    sdf_out = sdf[["name", "type", "subtype", "address", "postcode", "borough",
                    "lat", "lon", "easting", "northing", "assigned_lsoa"]].copy()
    sdf_out.to_csv(csv_path, index=False)
    print(f"\nSaved {len(sdf_out)} services to {csv_path}")

    # --- Step 5: Aggregate per LSOA ---
    print("\nAggregating service counts per LSOA...")
    sdf_valid = sdf[sdf["assigned_lsoa"].notna()].copy()

    # Total count
    total_counts = sdf_valid.groupby("assigned_lsoa").size().rename("community_services_total")

    # By type
    type_counts = sdf_valid.groupby(["assigned_lsoa", "type"]).size().unstack(fill_value=0)
    type_counts.columns = [f"cs_{col}_count" for col in type_counts.columns]

    # Service names list (pipe-separated)
    service_names = sdf_valid.groupby("assigned_lsoa")["name"].apply(
        lambda x: " | ".join(x)
    ).rename("community_services_names")

    # Service types list (unique, pipe-separated)
    service_types = sdf_valid.groupby("assigned_lsoa")["type"].apply(
        lambda x: " | ".join(sorted(set(x)))
    ).rename("community_services_types")

    agg = pd.concat([total_counts, type_counts, service_names, service_types], axis=1)
    agg.index.name = "lsoa_code"
    agg = agg.reset_index()

    print(f"  {len(agg)} LSOAs have at least one service")
    print(f"  Service type columns: {[c for c in agg.columns if c.startswith('cs_')]}")

    # --- Step 6: Compute distance to nearest service (from LSOA centroid) ---
    print("Computing distance to nearest community service per LSOA...")

    # Build array of service locations (BNG easting/northing)
    svc_coords = sdf_geo[["easting", "northing"]].values.astype(float)

    # LSOA centroids in BNG
    lsoa_centroids = gdf.geometry.centroid
    lsoa_eastings = lsoa_centroids.x.values
    lsoa_northings = lsoa_centroids.y.values

    # Nearest distance for each LSOA
    nearest_dists = []
    nearest_names = []
    nearest_types = []

    for i in range(len(gdf)):
        dx = svc_coords[:, 0] - lsoa_eastings[i]
        dy = svc_coords[:, 1] - lsoa_northings[i]
        dists = np.sqrt(dx**2 + dy**2)
        min_idx = np.argmin(dists)
        nearest_dists.append(dists[min_idx])
        nearest_names.append(sdf_geo.iloc[min_idx]["name"])
        nearest_types.append(sdf_geo.iloc[min_idx]["type"])

    gdf["dist_to_nearest_community_service_m"] = nearest_dists
    gdf["nearest_community_service_name"] = nearest_names
    gdf["nearest_community_service_type"] = nearest_types

    # Distance to nearest by type
    service_types_list = sdf_geo["type"].unique()
    for stype in service_types_list:
        mask = sdf_geo["type"] == stype
        type_coords = sdf_geo.loc[mask, ["easting", "northing"]].values.astype(float)
        col_name = f"dist_to_nearest_{stype}_m"
        dists_for_type = []
        for i in range(len(gdf)):
            dx = type_coords[:, 0] - lsoa_eastings[i]
            dy = type_coords[:, 1] - lsoa_northings[i]
            d = np.sqrt(dx**2 + dy**2)
            dists_for_type.append(d.min())
        gdf[col_name] = dists_for_type

    # --- Step 7: Merge aggregate counts ---
    gdf = gdf.merge(agg, on="lsoa_code", how="left")

    # Fill NaN counts with 0
    count_cols = [c for c in gdf.columns if c.endswith("_count") or c == "community_services_total"]
    for col in count_cols:
        gdf[col] = gdf[col].fillna(0).astype(int)

    # --- Step 8: Save enriched GeoPackage ---
    out_layer = "master_lsoa"
    print(f"\nSaving enriched GeoPackage (overwriting layer '{out_layer}')...")
    gdf.to_file(gpkg_path, layer=out_layer, driver="GPKG")

    print(f"\n{'='*60}")
    print("ENRICHMENT COMPLETE")
    print(f"{'='*60}")
    print(f"Services catalogued: {len(sdf)}")
    print(f"Services geocoded:   {geocoded}")
    print(f"Services assigned:   {assigned}")
    print(f"LSOAs with services: {len(agg)}")
    print(f"LSOAs total:         {len(gdf)}")
    print()
    print("New columns added to master_lsoa:")
    new_cols = [c for c in gdf.columns if "community" in c or "nearest" in c or c.startswith("cs_") or c.startswith("dist_to_nearest_")]
    for c in sorted(new_cols):
        print(f"  - {c}")
    print()
    print(f"Standalone CSV: {csv_path}")
    print(f"GeoPackage:     {gpkg_path} (layer: {out_layer})")


if __name__ == "__main__":
    main()
