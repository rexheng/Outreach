# Outreach -- Pitch Script (2-3 minutes)

## Opening (15 seconds)

Last summer I worked at a charity called Blackfriars Settlement in Southwark. I saw firsthand how borough councils allocate mental health funding based on aggregate statistics that completely miss what's happening at the neighbourhood level. A borough can look fine on paper while individual communities inside it are struggling with severe mental health need, high disability, and no services nearby.

## The Problem (20 seconds)

The data to fix this already exists. ONS publishes health and disability statistics. MHCLG publishes deprivation indices. The University of Bristol publishes a mental health index covering every neighbourhood in England. But this data sits across six different agencies, in different formats, at different geographic scales. No frontline commissioner has the time to join it all up. So the funding keeps following the averages, and the most vulnerable communities keep falling through the gaps.

## What Outreach Does (30 seconds)

Outreach solves this by assembling all of that data into one place. It maps mental health need across every single one of London's 4,994 neighbourhoods. Each one gets a Composite Need Index from 0 to 10, combining deprivation, health outcomes, disability rates, unemployment, and long-term sickness. You can filter by borough, toggle between nine different indicator layers, and click any neighbourhood to see a full breakdown of what's driving need there.

## The AI Chatbot (30 seconds)

The part I'm most excited about is the policy chatbot. Instead of reading a dashboard and trying to interpret the numbers yourself, you can ask questions in plain English. For example: "We have funding for three new community mental health teams. Which boroughs should get them?" And the chatbot gives you a commissioning-ready answer, grounded entirely in the data, with clickable links that take you straight to the specific neighbourhoods on the map. It speaks in the language of policy recommendations, telling you where to deploy outreach workers or expand talking therapies, rather than listing statistics.

## Demo Moment (20 seconds)

Let me show you quickly. I'll ask: "What's driving high need in Hackney and what should we do about it?" ... And you can see it pulls the borough data, identifies the top risk factors, and recommends specific interventions for specific neighbourhoods. Every borough name and LSOA is a clickable link that navigates the map.

## How I Built It (20 seconds)

I built this solo in two and a half hours using multiple Claude Code instances running in parallel. One agent assembled the dataset from six public sources. Another built the frontend with Leaflet. A third handled the FastAPI backend and chatbot integration. Everything feeds from a single GeoPackage file containing 120 indicators per neighbourhood. It's deployed live on Railway right now.

## Closing (15 seconds)

The gap between having public data and making it actionable is where most health policy tools fall short. Outreach is designed to close that gap. I believe this is exactly the kind of AI application that helps people flourish, by giving the people who make funding decisions the neighbourhood-level intelligence they need to direct resources where they'll have the greatest impact.
