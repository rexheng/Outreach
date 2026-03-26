# Outreach -- Demo Script (~2.5 minutes)

> Designed to be spoken over a live screen share. Stage directions in brackets. Pause points marked with [beat].

---

**[Screen: browser open to the overview page]**

So this is Outreach. It maps mental health need across all 4,994 neighbourhoods in London.

The reason I built it is pretty simple. Last summer I worked at a charity in Southwark and I saw how funding decisions get made -- boroughs look at aggregate statistics, and those averages hide what's actually happening street by street. The data to fix that already exists across ONS, MHCLG, the University of Bristol -- but nobody has time to join it up. So I did.

**[Gesture at the KPI strip]**

Up top, headline numbers for all of London. Average mental health index, antidepressant prescribing rates, depression prevalence, disability. Below that are five data-driven narratives -- things like the correlation between deprivation and mental health, or the fact that every single borough got worse between 2019 and 2022.

**[Scroll down briefly to show the borough table and scatter plot, then click "Map Explorer"]**

Now this is the main tool. Every area gets a Composite Need Index from 0 to 10. It's built from two pillars -- socioeconomic deprivation and demographic vulnerability -- using weighted indicators like health deprivation, income, employment, long-term sickness.

**[Toggle one or two layer radio cards on the left panel]**

Nine different layers you can switch between. Health deprivation. Income. SAMHI mental health index. Each one recolours the map instantly.

**[Select "Barking and Dagenham" from the borough dropdown]**

Filter to a borough -- say Barking and Dagenham, which ranks highest for need in London. [beat] And now there's a "Download Briefing" button. That generates a one-page PDF with their headline KPIs, top five priority neighbourhoods, what's driving need in each one, and how the borough compares to the London average. Something a cabinet member can take into a budget meeting.

**[Click on a dark-shaded neighbourhood]**

Click any neighbourhood and the sidebar gives you the full picture. Score, rank, indicator bars, a narrative about what's driving need here, nearest community services with distances.

**[Close sidebar, open the chat panel in bottom-right]**

And this is the part I think matters most. Instead of reading charts and trying to work out what they mean for policy, you just ask.

**[Type: "We have funding for three new community mental health teams. Which boroughs should get them?"]**

Plain English question, and it gives you a commissioning-ready answer. Specific boroughs, specific neighbourhoods, specific interventions -- expand talking therapies here, deploy outreach workers there. And every borough and neighbourhood name is a clickable link that takes you straight to it on the map.

**[Click one of the entity links to show it navigates the map]**

[beat]

I built this solo with Claude Code. FastAPI backend, Leaflet frontend, 120 indicators per neighbourhood assembled from six public datasets, all in a single GeoPackage file. It's live on Railway right now.

**[beat]**

There's a lot of public data about mental health in this country. The problem has never been the data -- it's that nobody's made it actionable for the people who control the funding. That's what Outreach does.
