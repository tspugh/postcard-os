// Seed data — Postcard Campaign Platform, Lafayette IN, June 2026
// All times relative to "now" so the prototype always feels current.
(function () {
  const NOW = Date.now();
  const H = 3600e3, D = 24 * H;
  const ago = (ms) => new Date(NOW - ms).toISOString();

  const SETTINGS = {
    defaultSlotPriceCents: 29900,
    totalSlots: 8,
    categories: ['roofer', 'plumber', 'electrician', 'hvac', 'landscaper', 'auto repair', 'realtor', 'restaurant'],
    seedMarket: 'Lafayette, IN',
  };

  const CAMPAIGN = {
    id: 'camp-1',
    name: 'Lafayette June 2026',
    market: 'Lafayette, IN',
    month: 'June 2026',
    deadline: '2026-06-19',
    slotPriceCents: 29900,
    totalSlots: 8,
    status: 'filling',
  };

  // Helper to build an email version
  const em = (v, author, status, subject, body, ts) => ({ v, author, status, subject, body, ts });

  const BUSINESSES = [
    // ---- COMMITTED ----
    {
      id: 'b-tippecanoe', name: 'Tippecanoe Roofing Co.', category: 'roofer',
      website: 'https://tippecanoeroofing.example', source: 'agent:web',
      createdAt: ago(9 * D), viewedAt: ago(8 * D), status: 'researched',
      premise: 'Residential roofing contractor serving Tippecanoe County; primarily asphalt shingle replacement and storm repair. Family-run crew, in business since 2004.',
      hooks: ['Family-owned 22 years', '4.9★ across 210 Google reviews', 'Free storm-damage inspections'],
      evidence: ['https://tippecanoeroofing.example/about', 'https://google.com/maps/place/tippecanoe-roofing'],
      contacts: [
        { id: 'c1', name: 'Dale Hutchins', title: 'Owner', email: 'dale@tippecanoeroofing.example', emailSource: 'site contact page', emailConfidence: 'listed', phone: '(765) 555-0142', isPrimary: true },
      ],
      participation: {
        status: 'paid', askingPriceCents: 29900, committedAmountCents: 29900,
        paymentStatus: 'paid', paymentMethod: 'cash', paidAt: ago(2 * D),
        slot: 1, waitlistOrder: null,
        fulfillment: { logo_received: true, offer_confirmed: true, artwork_approved: false },
        emails: [
          em(2, 'agent', 'sent', 'One roofer spot on June\u2019s Lafayette postcard', 'Hi Dale,\n\n22 years family-owned and a 4.9\u2605 across 210 reviews \u2014 you\u2019re exactly who neighbors ask about after a storm. We\u2019re mailing a shared postcard to 10,000 Lafayette households in June: 8 local businesses, one per industry, so you\u2019d be the only roofer on the card.\n\nThe spot is $299 flat. One card, one month, your offer in front of every mailbox in town.\n\nWorth a quick call this week?\n\n\u2014 Grant', ago(7 * D)),
          em(1, 'agent', 'superseded', 'Advertise on the Lafayette postcard?', 'Hi Dale,\n\nWould you like to advertise on a postcard we\u2019re mailing in June? Spots are $299.\n\n\u2014 Grant', ago(8 * D)),
        ],
        events: [
          { label: 'Payment recorded — $299 cash', ts: ago(2 * D) },
          { label: 'Committed at $299 · slot 1 assigned', ts: ago(4 * D) },
          { label: 'Marked sent by operator', ts: ago(7 * D) },
          { label: 'v2 approved by operator', ts: ago(7 * D) },
        ],
      },
      comments: [
        { id: 'cm1', author: 'grant', body: 'Lead with the storm-repair angle — June hail season.', ts: ago(8 * D), resolved: true },
      ],
    },
    {
      id: 'b-wabash', name: 'Wabash Heating & Air', category: 'hvac',
      website: 'https://wabashheatingair.example', source: 'operator',
      createdAt: ago(8 * D), viewedAt: ago(7 * D), status: 'researched',
      premise: 'HVAC installation and service for greater Lafayette; strong on residential AC replacement and maintenance plans.',
      hooks: ['Same-day service guarantee', 'Carrier factory-authorized dealer'],
      evidence: ['https://wabashheatingair.example'],
      contacts: [
        { id: 'c2', name: 'Marcy Pollard', title: 'Office Manager', email: 'office@wabashheatingair.example', emailSource: 'https://wabashheatingair.example/contact', emailConfidence: 'listed', phone: '(765) 555-0177', isPrimary: true },
      ],
      participation: {
        status: 'committed', askingPriceCents: 29900, committedAmountCents: 27500,
        paymentStatus: 'pending', paymentMethod: null, paidAt: null,
        slot: 2, waitlistOrder: null,
        fulfillment: { logo_received: true, offer_confirmed: false, artwork_approved: false },
        emails: [
          em(1, 'agent', 'sent', 'The only HVAC spot on Lafayette\u2019s June postcard', 'Hi Marcy,\n\nWe\u2019re putting 8 Lafayette businesses on one postcard to 10,000 local households in June \u2014 one per industry. The HVAC spot is open, and with your same-day guarantee it writes its own headline.\n\n$299 for the month. Want me to hold the spot while you check with the team?\n\n\u2014 Grant', ago(6 * D)),
        ],
        events: [
          { label: 'Committed at $275 (negotiated) · slot 2 assigned', ts: ago(3 * D) },
          { label: 'Marked sent by operator', ts: ago(6 * D) },
        ],
      },
      comments: [],
    },
    {
      id: 'b-redbrick', name: 'Red Brick Bistro', category: 'restaurant',
      website: 'https://redbrickbistro.example', source: 'agent:web',
      createdAt: ago(7 * D), viewedAt: ago(6 * D), status: 'researched',
      premise: 'Downtown Lafayette bistro; lunch and dinner, locally sourced menu, popular patio season May\u2013September.',
      hooks: ['Voted Best Patio 2025 \u2014 Journal & Courier', 'New summer menu launching June'],
      evidence: ['https://redbrickbistro.example/menu', 'https://jconline.com/best-of-2025'],
      contacts: [
        { id: 'c3', name: 'Anthony Reyes', title: 'Owner', email: 'anthony@redbrickbistro.example', emailSource: 'scraped from site footer', emailConfidence: 'scraped', phone: null, isPrimary: true },
      ],
      participation: {
        status: 'committed', askingPriceCents: 29900, committedAmountCents: 29900,
        paymentStatus: 'pending', paymentMethod: null, paidAt: null,
        slot: 3, waitlistOrder: null,
        fulfillment: { logo_received: false, offer_confirmed: false, artwork_approved: false },
        emails: [
          em(1, 'agent', 'sent', 'Put the Best Patio in 10,000 Lafayette mailboxes', 'Hi Anthony,\n\nCongrats on Best Patio 2025. We\u2019re mailing a shared postcard to 10,000 Lafayette households in June \u2014 8 businesses, one per industry, and the restaurant spot is yours if you want it. Perfect timing for the summer menu.\n\n$299 flat for the month. Interested?\n\n\u2014 Grant', ago(5 * D)),
        ],
        events: [
          { label: 'Committed at $299 · slot 3 assigned', ts: ago(1 * D) },
          { label: 'Marked sent by operator', ts: ago(5 * D) },
        ],
      },
      comments: [],
    },

    // ---- WAITLISTED ----
    {
      id: 'b-summit', name: 'Summit Ridge Roofing', category: 'roofer',
      website: 'https://summitridgeroofing.example', source: 'agent:web',
      createdAt: ago(6 * D), viewedAt: ago(5 * D), status: 'researched',
      premise: 'Roofing and exterior contractor covering Lafayette and West Lafayette; metal and asphalt; commercial and residential.',
      hooks: ['Just opened a second location in West Lafayette', 'GAF-certified installer'],
      evidence: ['https://summitridgeroofing.example/news'],
      contacts: [
        { id: 'c4', name: 'Priya Raman', title: 'Co-owner', email: 'priya@summitridgeroofing.example', emailSource: 'https://summitridgeroofing.example/team', emailConfidence: 'listed', phone: '(765) 555-0123', isPrimary: true },
      ],
      participation: {
        status: 'waitlisted', askingPriceCents: 29900, committedAmountCents: null,
        paymentStatus: null, paymentMethod: null, paidAt: null,
        slot: null, waitlistOrder: 1,
        fulfillment: { logo_received: false, offer_confirmed: false, artwork_approved: false },
        emails: [
          em(1, 'agent', 'sent', 'Roofer spot on the Lafayette June postcard', 'Hi Priya,\n\nWith the new West Lafayette location, June is a great month to be in every mailbox in town. We\u2019re running a shared postcard \u2014 8 local businesses, one per industry \u2014 and I\u2019d love to have Summit Ridge on it. $299 for the month.\n\nOpen to it?\n\n\u2014 Grant', ago(5 * D)),
        ],
        events: [
          { label: 'Moved to waitlist — roofer slot committed to Tippecanoe Roofing Co.', ts: ago(3 * D) },
          { label: 'Replied interested', ts: ago(4 * D) },
          { label: 'Marked sent by operator', ts: ago(5 * D) },
        ],
      },
      comments: [
        { id: 'cm2', author: 'agent', body: 'They want in if the roofer slot frees up \u2014 also asked about July. Carrying forward as priority prospect.', ts: ago(3 * D), resolved: false },
      ],
    },
    {
      id: 'b-comfort', name: 'Comfort Zone Mechanical', category: 'hvac',
      website: 'https://comfortzonemech.example', source: 'agent:web',
      createdAt: ago(5 * D), viewedAt: ago(4 * D), status: 'researched',
      premise: 'HVAC and light plumbing service shop on the south side; residential maintenance contracts are the core business.',
      hooks: ['$59 tune-up special running now', '24/7 emergency line'],
      evidence: ['https://comfortzonemech.example/specials'],
      contacts: [
        { id: 'c5', name: 'Greg Schmitt', title: 'Owner', email: null, emailSource: null, emailConfidence: null, phone: '(765) 555-0190', isPrimary: true },
      ],
      participation: {
        status: 'waitlisted', askingPriceCents: 29900, committedAmountCents: null,
        paymentStatus: null, paymentMethod: null, paidAt: null,
        slot: null, waitlistOrder: 1,
        fulfillment: { logo_received: false, offer_confirmed: false, artwork_approved: false },
        emails: [
          em(1, 'agent', 'sent', 'One HVAC spot, 10,000 Lafayette mailboxes', 'Hi Greg,\n\nWe\u2019re mailing a shared postcard to 10,000 Lafayette households in June \u2014 8 businesses, one per industry. Your $59 tune-up special would pop on it.\n\n$299 flat. Interested?\n\n\u2014 Grant', ago(4 * D)),
        ],
        events: [
          { label: 'Moved to waitlist — hvac slot committed to Wabash Heating & Air', ts: ago(2 * D) },
          { label: 'Replied interested', ts: ago(3 * D) },
        ],
      },
      comments: [],
    },

    // ---- INTERESTED ----
    {
      id: 'b-lawn', name: 'Lafayette Lawn & Grade', category: 'landscaper',
      website: 'https://lafayettelawngrade.example', source: 'agent:web',
      createdAt: ago(5 * D), viewedAt: ago(4 * D), status: 'researched',
      premise: 'Landscaping and grading contractor; mowing contracts, mulch, and small excavation for residential lots.',
      hooks: ['Booked out 3 weeks \u2014 hiring a second crew', 'Veteran-owned'],
      evidence: ['https://lafayettelawngrade.example', 'https://facebook.com/lafayettelawngrade'],
      contacts: [
        { id: 'c6', name: 'Tom Brodie', title: 'Owner', email: 'tom@lafayettelawngrade.example', emailSource: 'Facebook page', emailConfidence: 'scraped', phone: '(765) 555-0156', isPrimary: true },
      ],
      participation: {
        status: 'interested', askingPriceCents: 29900, committedAmountCents: null,
        paymentStatus: null, paymentMethod: null, paidAt: null,
        slot: null, waitlistOrder: null,
        fulfillment: { logo_received: false, offer_confirmed: false, artwork_approved: false },
        emails: [
          em(1, 'agent', 'sent', 'The only landscaper on Lafayette\u2019s June postcard', 'Hi Tom,\n\nBooked out three weeks and hiring \u2014 sounds like demand isn\u2019t your problem, but June\u2019s card will be in 10,000 mailboxes when people are planning summer projects. One landscaper per card, $299 flat.\n\nWant the spot?\n\n\u2014 Grant', ago(4 * D)),
        ],
        events: [
          { label: 'Replied interested — asked if price is negotiable', ts: ago(1 * D) },
          { label: 'Marked sent by operator', ts: ago(4 * D) },
        ],
      },
      comments: [
        { id: 'cm3', author: 'grant', body: 'He asked for $250. Holding at $299 \u2014 only landscaper spot in town.', ts: ago(20 * H), resolved: false },
      ],
    },

    // ---- CONTACTED ----
    {
      id: 'b-sycamore', name: 'Sycamore Plumbing', category: 'plumber',
      website: 'https://sycamoreplumbing.example', source: 'agent:web',
      createdAt: ago(4 * D), viewedAt: ago(3 * D), status: 'researched',
      premise: 'Residential plumbing service and repair; water heaters, drain cleaning, fixture installs across Tippecanoe County.',
      hooks: ['3rd-generation family business', 'Up-front flat-rate pricing'],
      evidence: ['https://sycamoreplumbing.example/about'],
      contacts: [
        { id: 'c7', name: 'Janet Voss', title: 'Co-owner', email: 'janet@sycamoreplumbing.example', emailSource: 'site contact page', emailConfidence: 'listed', phone: '(765) 555-0163', isPrimary: true },
      ],
      participation: {
        status: 'contacted', askingPriceCents: 29900, committedAmountCents: null,
        paymentStatus: null, paymentMethod: null, paidAt: null,
        slot: null, waitlistOrder: null,
        fulfillment: { logo_received: false, offer_confirmed: false, artwork_approved: false },
        emails: [
          em(1, 'agent', 'sent', 'One plumber spot on June\u2019s Lafayette postcard', 'Hi Janet,\n\nThree generations of Sycamore Plumbing \u2014 that\u2019s the kind of name neighbors trust from a postcard. We\u2019re mailing 10,000 Lafayette households in June: 8 businesses, one per industry, and the plumber spot is open.\n\n$299 flat for the month. Can I send over the details?\n\n\u2014 Grant', ago(2 * D)),
        ],
        events: [{ label: 'Marked sent by operator', ts: ago(2 * D) }],
      },
      comments: [],
    },
    {
      id: 'b-fivepoints', name: 'Five Points Auto Care', category: 'auto repair',
      website: 'https://fivepointsautocare.example', source: 'agent:web',
      createdAt: ago(4 * D), viewedAt: ago(3 * D), status: 'researched',
      premise: 'Independent auto repair shop near Five Points; brakes, diagnostics, and fleet maintenance for local small businesses.',
      hooks: ['4.8★ on 340 reviews', 'Loaner cars for repairs over 4 hours'],
      evidence: ['https://fivepointsautocare.example', 'https://google.com/maps/place/five-points-auto'],
      contacts: [
        { id: 'c8', name: 'Ray Delgado', title: 'Owner', email: 'ray@fivepointsautocare.example', emailSource: 'site contact page', emailConfidence: 'listed', phone: '(765) 555-0171', isPrimary: true },
      ],
      participation: {
        status: 'contacted', askingPriceCents: 29900, committedAmountCents: null,
        paymentStatus: null, paymentMethod: null, paidAt: null,
        slot: null, waitlistOrder: null,
        fulfillment: { logo_received: false, offer_confirmed: false, artwork_approved: false },
        emails: [
          em(2, 'operator', 'sent', 'Your reviews belong in 10,000 mailboxes', 'Hi Ray,\n\n340 reviews at 4.8\u2605 \u2014 most shops would kill for that. We\u2019re mailing a shared postcard to 10,000 Lafayette households in June; one auto shop per card, and the spot is open.\n\n$299 flat. The loaner-car perk would make a great offer line.\n\nInterested?\n\n\u2014 Grant', ago(1 * D)),
          em(1, 'agent', 'superseded', 'Auto repair spot on the Lafayette postcard', 'Hi Ray,\n\nWe\u2019re mailing a postcard to 10,000 Lafayette households in June with 8 local businesses on it, one per industry. The auto repair spot is open \u2014 $299 for the month.\n\nInterested?\n\n\u2014 Grant', ago(2 * D)),
        ],
        events: [
          { label: 'Marked sent by operator', ts: ago(1 * D) },
          { label: 'v2 saved by operator (edit)', ts: ago(1 * D) },
        ],
      },
      comments: [
        { id: 'cm4', author: 'grant', body: 'Rewrote to lead with the review count \u2014 the v1 opener was generic.', ts: ago(1 * D), resolved: true },
      ],
    },

    // ---- RESEARCHED (prospecting, drafts in review) ----
    {
      id: 'b-hoosier', name: 'Hoosier Electric LLC', category: 'electrician',
      website: 'https://hoosierelectricllc.example', source: 'agent:web',
      createdAt: ago(2 * D), viewedAt: ago(1 * D), status: 'researched',
      premise: 'Licensed residential electrician; panel upgrades, EV charger installs, and service calls in Lafayette and West Lafayette.',
      hooks: ['EV charger installs up 3\u00d7 this year (their blog)', 'Licensed & insured, free estimates'],
      evidence: ['https://hoosierelectricllc.example/blog/ev-chargers', 'https://hoosierelectricllc.example'],
      contacts: [
        { id: 'c9', name: 'Kurt Weaver', title: 'Owner', email: 'kurt@hoosierelectricllc.example', emailSource: 'site contact page', emailConfidence: 'listed', phone: '(765) 555-0118', isPrimary: true },
      ],
      participation: {
        status: 'prospecting', askingPriceCents: 29900, committedAmountCents: null,
        paymentStatus: null, paymentMethod: null, paidAt: null,
        slot: null, waitlistOrder: null,
        fulfillment: { logo_received: false, offer_confirmed: false, artwork_approved: false },
        emails: [
          em(1, 'agent', 'in_review', 'The only electrician on Lafayette\u2019s June postcard', 'Hi Kurt,\n\nEV charger installs tripling this year tells me Lafayette homeowners are looking for exactly what you do. We\u2019re mailing a shared postcard to 10,000 local households in June \u2014 8 businesses, one per industry, so you\u2019d be the only electrician on the card.\n\nThe spot is $299 flat for the month. Want me to send the details?\n\n\u2014 Grant', ago(6 * H)),
        ],
        events: [{ label: 'Attached to campaign · asking price $299 snapshotted', ts: ago(1 * D) }],
      },
      comments: [],
    },
    {
      id: 'b-riverside', name: 'Riverside Realty Group', category: 'realtor',
      website: 'https://riversiderealtygroup.example', source: 'agent:web',
      createdAt: ago(2 * D), viewedAt: null, status: 'researched',
      premise: 'Independent residential brokerage, 6 agents; strong in first-time buyers and near-campus rentals-to-owners conversions.',
      hooks: ['Top-10 Tippecanoe County brokerage by 2025 volume', 'Hosting free first-time-buyer seminar June 20'],
      evidence: ['https://riversiderealtygroup.example/events', 'https://mibor.com/rankings-2025'],
      contacts: [
        { id: 'c10', name: 'Dana Okafor', title: 'Managing Broker', email: 'dana@riversiderealtygroup.example', emailSource: 'https://riversiderealtygroup.example/agents', emailConfidence: 'listed', phone: '(765) 555-0135', isPrimary: true },
      ],
      participation: {
        status: 'prospecting', askingPriceCents: 29900, committedAmountCents: null,
        paymentStatus: null, paymentMethod: null, paidAt: null,
        slot: null, waitlistOrder: null,
        fulfillment: { logo_received: false, offer_confirmed: false, artwork_approved: false },
        emails: [
          em(1, 'agent', 'in_review', 'Fill your June 20 seminar from 10,000 mailboxes', 'Hi Dana,\n\nYour first-time-buyer seminar on June 20 is a perfect match for what we\u2019re mailing: a shared postcard reaching 10,000 Lafayette households in early June \u2014 8 local businesses, one per industry, one realtor.\n\nPut the seminar on the card as your offer and the timing does the work. $299 flat.\n\nWorth a quick call?\n\n\u2014 Grant', ago(3 * H)),
        ],
        events: [{ label: 'Attached to campaign · asking price $299 snapshotted', ts: ago(5 * H) }],
      },
      comments: [],
    },

    // ---- RESEARCHING ----
    {
      id: 'b-stonecreek', name: 'Stone Creek Landscaping', category: 'landscaper',
      website: 'https://stonecreeklandscaping.example', source: 'agent:web',
      createdAt: ago(1 * D), viewedAt: ago(20 * H), status: 'researching',
      claimedAt: ago(35 * 60e3),
      premise: null, hooks: [], evidence: [], contacts: [],
      participation: null, comments: [],
    },

    // ---- STAGED ----
    {
      id: 'b-maxwell', name: "Maxwell's Auto Body", category: 'auto repair',
      website: 'https://maxwellsautobody.example', source: 'agent:web',
      createdAt: ago(4 * H), viewedAt: null, status: 'staged',
      premise: null, hooks: [], evidence: [], contacts: [],
      participation: null, comments: [],
    },
    {
      id: 'b-courthouse', name: 'Courthouse Realty', category: 'realtor',
      website: 'https://courthouserealty.example', source: 'agent:web',
      createdAt: ago(4 * H), viewedAt: null, status: 'staged',
      premise: null, hooks: [], evidence: [], contacts: [],
      participation: null, comments: [],
    },
    {
      id: 'b-drainmasters', name: 'Drainmasters Sewer & Drain', category: 'plumber',
      website: 'https://drainmasters-lafayette.example', source: 'operator',
      createdAt: ago(1 * D), viewedAt: ago(22 * H), status: 'staged',
      premise: null, hooks: [], evidence: [], contacts: [],
      participation: null, comments: [],
    },

    // ---- DISQUALIFIED / DECLINED ----
    {
      id: 'b-roofpros', name: 'Lafayette Roof Pros', category: 'roofer',
      website: 'https://lafayetteroofpros.example', source: 'agent:web',
      createdAt: ago(6 * D), viewedAt: ago(5 * D), status: 'disqualified',
      dq: { code: 'duplicate', note: 'Same crew as Tippecanoe Roofing Co. — rebrand site, same phone number.' },
      premise: null, hooks: [], evidence: [], contacts: [],
      participation: null, comments: [],
    },
    {
      id: 'b-bigbox', name: 'BigBox Realty', category: 'realtor',
      website: 'https://bigboxrealty.example', source: 'agent:web',
      createdAt: ago(5 * D), viewedAt: ago(5 * D), status: 'disqualified',
      dq: { code: 'bad_fit', note: 'National franchise; ad decisions made at corporate, not local to market.' },
      premise: null, hooks: [], evidence: [], contacts: [],
      participation: null, comments: [],
    },
    {
      id: 'b-gearhead', name: 'Gearhead Garage', category: 'auto repair',
      website: 'https://gearheadgaragein.example', source: 'agent:web',
      createdAt: ago(6 * D), viewedAt: ago(5 * D), status: 'researched',
      premise: 'Performance and general auto repair shop on Sagamore Pkwy.',
      hooks: ['Sponsors local dirt-track team'],
      evidence: ['https://gearheadgaragein.example'],
      contacts: [
        { id: 'c11', name: 'Bill Tanner', title: 'Owner', email: 'bill@gearheadgaragein.example', emailSource: 'site contact page', emailConfidence: 'listed', phone: null, isPrimary: true },
      ],
      participation: {
        status: 'declined', askingPriceCents: 29900, committedAmountCents: null,
        paymentStatus: null, paymentMethod: null, paidAt: null,
        slot: null, waitlistOrder: null,
        fulfillment: { logo_received: false, offer_confirmed: false, artwork_approved: false },
        emails: [
          em(1, 'agent', 'sent', 'Auto repair spot on the Lafayette postcard', 'Hi Bill,\n\nWe\u2019re mailing a shared postcard to 10,000 Lafayette households in June \u2014 one auto shop per card. $299 flat.\n\nInterested?\n\n\u2014 Grant', ago(5 * D)),
        ],
        events: [
          { label: 'Declined — committed budget to radio ads this quarter', ts: ago(3 * D) },
          { label: 'Marked sent by operator', ts: ago(5 * D) },
        ],
      },
      comments: [],
    },
  ];

  const ACTIVITY = [
    { id: 'a1', tool: 'postcard_save_email_draft', outcome: 'ok', detail: 'Riverside Realty Group — v1 “Fill your June 20 seminar…” in review', ts: ago(3 * H) },
    { id: 'a2', tool: 'postcard_stage_leads', outcome: 'ok', detail: 'Staged 2 leads: Maxwell\u2019s Auto Body, Courthouse Realty', ts: ago(4 * H) },
    { id: 'a3', tool: 'postcard_save_email_draft', outcome: 'ok', detail: 'Hoosier Electric LLC — v1 “The only electrician…” in review', ts: ago(6 * H) },
    { id: 'a4', tool: 'postcard_stage_leads', outcome: 'rejected', detail: '“Lafayette Roofing Pros” rejected — duplicate of existing record Lafayette Roof Pros', ts: ago(7 * H) },
    { id: 'a5', tool: 'postcard_claim_lead', outcome: 'ok', detail: 'Claimed Stone Creek Landscaping for research', ts: ago(35 * 60e3) },
    { id: 'a6', tool: 'postcard_submit_research', outcome: 'ok', detail: 'Riverside Realty Group — 1 contact, 2 hooks, 2 evidence URLs', ts: ago(5 * H) },
    { id: 'a7', tool: 'postcard_record_commitment', outcome: 'rejected', detail: 'Summit Ridge Roofing — roofer slot already committed; recommended move_to_waitlist', ts: ago(3 * D) },
    { id: 'a8', tool: 'postcard_move_to_waitlist', outcome: 'ok', detail: 'Summit Ridge Roofing → waitlist #1 (roofer)', ts: ago(3 * D) },
    { id: 'a9', tool: 'postcard_get_campaign_status', outcome: 'ok', detail: 'Oriented: 3/8 slots committed, 2 waitlisted, deadline Jun 19', ts: ago(8 * H) },
  ].sort((a, b) => new Date(b.ts) - new Date(a.ts));

  const DQ_CODES = ['no_contact_info', 'defunct', 'bad_fit', 'duplicate', 'do_not_contact', 'other'];

  window.POSTCARD_SEED = { SETTINGS, CAMPAIGN, BUSINESSES, ACTIVITY, DQ_CODES, NOW };
})();
