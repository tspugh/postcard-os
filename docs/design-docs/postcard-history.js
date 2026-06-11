// v2 extensions: extra June waitlist entry + archived May 2026 campaign history
(function () {
  const seed = window.POSTCARD_SEED;
  const NOW = Date.now();
  const H = 3600e3, D = 24 * H;
  const ago = (ms) => new Date(NOW - ms).toISOString();

  // A second roofer on the June waitlist (demonstrates ordering / reorder)
  seed.BUSINESSES.push({
    id: 'b-apex', name: 'Apex Exteriors', category: 'roofer',
    website: 'https://apexexteriors-in.com', source: 'agent:web',
    createdAt: ago(4 * D), viewedAt: ago(3 * D), status: 'researched',
    premise: 'Roofing and siding contractor on the north side; insurance-claim specialists for hail and wind damage.',
    hooks: ['Handles the insurance paperwork for you', 'Owens Corning preferred contractor'],
    evidence: ['https://apexexteriors-in.com/insurance'],
    contacts: [
      { id: 'c12', name: 'Stan Kowalski', title: 'Owner', email: 'stan@apexexteriors-in.com', emailSource: 'site contact page', emailConfidence: 'listed', phone: null, isPrimary: true },
    ],
    participation: {
      status: 'waitlisted', askingPriceCents: 29900, committedAmountCents: null,
      paymentStatus: null, paymentMethod: null, paidAt: null,
      slot: null, waitlistOrder: 2,
      fulfillment: { logo_received: false, offer_confirmed: false, artwork_approved: false },
      emails: [
        { v: 1, author: 'agent', status: 'sent', subject: 'Roofer spot on the Lafayette June postcard', body: 'Hi Stan,\n\nInsurance-claim roofing is exactly what storm season puts on people\u2019s minds. We\u2019re mailing a shared postcard to 10,000 Lafayette households in June \u2014 one roofer per card. $299 flat.\n\nInterested?\n\n\u2014 Grant', ts: ago(3 * D) },
      ],
      events: [
        { label: 'Moved to waitlist #2 — roofer slot committed to Tippecanoe Roofing Co.', ts: ago(2 * D) },
        { label: 'Replied interested', ts: ago(2.5 * D) },
      ],
    },
    comments: [],
  });

  // Archived May 2026 campaign — read-only history
  const MAY = {
    id: 'camp-0',
    name: 'Lafayette May 2026',
    market: 'Lafayette, IN',
    month: 'May 2026',
    deadline: '2026-05-15',
    slotPriceCents: 29900,
    totalSlots: 8,
    status: 'archived',
    participants: [
      { businessId: 'b-tippecanoe', name: 'Tippecanoe Roofing Co.', category: 'roofer', status: 'paid', amountCents: 29900, method: 'cash', slot: 1 },
      { businessId: 'b-sycamore', name: 'Sycamore Plumbing', category: 'plumber', status: 'paid', amountCents: 29900, method: 'paypal', slot: 2 },
      { businessId: 'b-redbrick', name: 'Red Brick Bistro', category: 'restaurant', status: 'paid', amountCents: 29900, method: 'check', slot: 3 },
      { businessId: 'b-fivepoints', name: 'Five Points Auto Care', category: 'auto repair', status: 'paid', amountCents: 29900, method: 'cash', slot: 4 },
      { businessId: 'b-riverside', name: 'Riverside Realty Group', category: 'realtor', status: 'paid', amountCents: 25000, method: 'paypal', slot: 5 },
      { businessId: 'b-summit', name: 'Summit Ridge Roofing', category: 'roofer', status: 'waitlisted', amountCents: null, waitlistOrder: 1 },
      { businessId: 'b-gearhead', name: 'Gearhead Garage', category: 'auto repair', status: 'declined', amountCents: null },
    ],
  };

  window.POSTCARD_V2 = { MAY };
})();
